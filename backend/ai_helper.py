"""Shared plumbing that lets the local AI act as a helper on top of the deterministic engines.

Deterministic code finds names, misspellings and reader-experience moments first. The AI
is then handed those findings as evidence to explain or refine, and every response says
whether the AI took part.
"""
import difflib
import re

from backend.config import ENABLE_AI
from backend.entity_names import entity_name_forms
from backend.reader_feel import analyze_reader_feel

AI_ENGINE = "local-ai"
TEXT_ENGINE = "deterministic"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_CAPITALIZED = re.compile(r"[A-Z][A-Za-z'’-]{3,}")


def ai_meta(used: bool, error: str = "") -> dict:
    """Fields every AI-capable response carries so the UI can label its source."""
    meta = {"ai_generated": bool(used), "engine": AI_ENGINE if used else TEXT_ENGINE}
    if error:
        meta["ai_error"] = error
    return meta


def known_cast_lines(conn) -> list[str]:
    rows = conn.execute("SELECT name, aliases FROM canonical_entities").fetchall()
    lines = []
    for row in rows:
        forms = entity_name_forms(row["name"], row["aliases"])
        lines.append(forms[0] if len(forms) == 1 else f"{forms[0]} (also: {', '.join(forms[1:])})")
    return lines


def text_observations(text: str, limit: int = 6) -> list[str]:
    """Moments the prose itself exposes, found without any model."""
    try:
        moments = analyze_reader_feel(text)
    except Exception:
        return []
    lines = []
    for item in moments[:limit]:
        evidence = f' — "{item["evidence"][:140]}"' if item.get("evidence") else ""
        lines.append(f"{item['headline']}{evidence}")
    return lines


def deterministic_brief(text: str, conn=None) -> str:
    """A compact evidence block to place in front of the model."""
    parts = []
    if conn is not None:
        cast = known_cast_lines(conn)
        if cast:
            parts.append("KNOWN CAST (use these exact names; aliases are the same person):\n- " + "\n- ".join(cast[:25]))
    observations = text_observations(text)
    if observations:
        parts.append(
            "TEXT-DERIVED OBSERVATIONS (already computed from the prose; explain or refine them, do not rediscover them):\n- "
            + "\n- ".join(observations)
        )
    return "\n\n".join(parts)


def find_name_candidates(text: str, known: set[str], dictionary_check=None) -> list[str]:
    """Capitalised mid-sentence words that are not already known; made-up names rank first."""
    seen: dict[str, int] = {}
    for sentence in _SENTENCE_SPLIT.split(text):
        words = list(_CAPITALIZED.finditer(sentence))
        for match in words:
            if match.start() < 3:
                continue
            word = match.group(0).strip("'’-")
            if word.casefold() in known:
                continue
            seen[word] = seen.get(word, 0) + 1
    names = list(seen)
    if dictionary_check is not None:
        try:
            real_words = dictionary_check([n.casefold() for n in names])
        except Exception:
            real_words = set()
        names = [n for n in names if n.casefold() not in real_words]
    return sorted(names, key=lambda n: (-seen[n], n))[:20]


def spelling_findings(rules: list[dict], text: str) -> list[dict]:
    """Near-miss spellings of established lore terms, found by string similarity."""
    terms = {r["term"].strip(): r for r in rules if r["term"].strip() and " " not in r["term"].strip()}
    exact = {t.casefold() for t in terms}
    findings = []
    seen = set()
    for word in re.findall(r"[A-Za-z][A-Za-z'’-]{3,}", text):
        key = word.casefold()
        if key in exact or key in seen:
            continue
        for term, rule in terms.items():
            if abs(len(term) - len(word)) > 2:
                continue
            ratio = difflib.SequenceMatcher(None, key, term.casefold()).ratio()
            if ratio >= 0.84:
                seen.add(key)
                findings.append({
                    "rule_broken": term,
                    "violation": word,
                    "explanation": f'"{word}" looks like a misspelling of the established term "{term}".',
                    "source": TEXT_ENGINE,
                })
                break
    return findings


def relevant_rules(rules: list[dict], text: str, cap: int = 15) -> list[dict]:
    """Rules whose term appears in the scene; falls back to a capped sample so unnamed rule breaks can still be checked."""
    lowered = text.casefold()
    hits = [r for r in rules if r["term"].strip() and r["term"].casefold() in lowered]
    return hits[:cap] if hits else rules[:cap]


def ai_enabled() -> bool:
    return bool(ENABLE_AI)
