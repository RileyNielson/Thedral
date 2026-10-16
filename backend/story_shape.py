"""Story shape: how strongly each plot strand shows up in a scene, chapter, or book.

Scores come from transparent word lists counted in the manuscript text; no AI is used.
Strand scores are relative to the book itself, so they show emphasis, not a grade.
"""
import hashlib
import re
from collections import OrderedDict

from backend.text_utils import html_to_text

# (key, label, core, confidence, terms). A trailing * lets a stem take any ending.
_STRAND_DEFS = [
    ("action", "Action", True, "high", [
        "punch*", "kick*", "strike*", "struck", "slash*", "stab*", "shot", "shoot*", "fire*", "fired", "swing*", "swung",
        "dodg*", "lunge*", "lunged", "charge*", "tackl*", "grapple*", "smash*", "crash*", "slam*", "blade*", "sword*",
        "gun*", "rifle*", "explo*", "chase*", "chasing", "sprint*", "leap*", "leapt", "vault*", "parr*", "block*",
        "wrestl*", "fight*", "fought", "battle*", "blow*", "bullet*", "dagger*", "arrow*", "duck*", "roll*", "scrambl*",
        "hurl*", "kicked", "throw*", "threw", "wound*", "bleed*", "blood*"]),
    ("conflict", "Conflict", True, "high", [
        "argu*", "shout*", "yell*", "scream*", "snap*", "accus*", "blame*", "threat*", "demand*", "refus*", "defy*",
        "defian*", "confront*", "insult*", "curse*", "cursed", "furious", "fury", "rage*", "enrag*", "angry", "anger*",
        "hate*", "hatred", "liar*", "lied", "lie", "betray*", "quarrel*", "dispute*", "oppos*", "enem*", "rival*", "clash*",
        "storm* out", "slammed the door", "how dare", "get out", "shut up"]),
    ("romance", "Romance", True, "high", [
        "kiss*", "embrac*", "hug*", "caress*", "lover*", "love", "loved", "loving", "beloved", "darling", "sweetheart",
        "desire*", "desir*", "longing", "yearn*", "blush*", "flirt*", "intimate", "intimacy", "passion*", "tender*",
        "heartbeat", "heart raced", "pulse quicken*", "fingers brush*", "hand in", "held hands", "holding hands",
        "gaze*", "lips", "adore*", "affection*", "courtship", "wedding", "marry", "married", "bride", "groom"]),
    ("mystery", "Mystery", True, "high", [
        "clue*", "secret*", "mysteri*", "puzzl*", "riddle*", "strange*", "unknown", "unexplained", "wonder*",
        "investigat*", "evidence", "suspect*", "disappear*", "vanish*", "missing", "hidden", "conceal*", "cipher*",
        "code", "mystery", "odd", "curious", "peculiar", "inexplicabl*", "impossible", "reveal*", "discover*", "uncover*",
        "figure out", "make sense", "what if", "why would", "how could", "no one knew", "nobody knew"]),
    ("suspense", "Suspense", True, "medium", [
        "wait*", "silence", "silent", "hush*", "listen*", "footstep*", "creak*", "shadow*", "tense", "tension", "hold* breath",
        "held breath", "held her breath", "held his breath", "any moment", "too late", "running out", "ticking", "countdown",
        "deadline", "trap*", "ambush*", "stalk*", "lurk*", "watching", "watched", "followed", "behind him", "behind her",
        "closer", "approach*", "freeze*", "froze", "frozen", "stillness", "dread", "unseen", "just out of", "heart pounded",
        "heart hammer*", "pulse pound*", "nervous*", "uneasy", "on edge"]),
    ("adventure", "Adventure", True, "medium", [
        "journey*", "travel*", "voyage*", "expedition*", "quest*", "explor*", "wander*", "trek*", "hike*", "climb*", "ascend*",
        "descend*", "cross*", "sail*", "ship*", "road", "trail*", "path*", "map*", "mountain*", "forest*", "river*", "desert*",
        "cave*", "cavern*", "ruin*", "treasure*", "horizon", "frontier", "camp*", "supplies", "compass", "horse*", "ride",
        "rode", "riding", "fly*", "flew", "beyond the", "uncharted", "wilderness", "island*", "coast*", "canyon*", "valley*"]),
    ("growth", "Character growth", True, "low", [
        "realiz*", "realis*", "understood", "understand*", "learn*", "decid*", "chose", "choose*", "choice*", "forgiv*",
        "forgave", "apolog*", "sorry", "regret*", "ashamed", "shame*", "guilt*", "atone*", "redeem*", "redemption", "change*",
        "changed", "become", "became", "growing", "grew", "accept*", "face the", "faced the", "courage*", "brave*", "mistake*",
        "wrong", "should have", "never again", "no longer", "for the first time", "promise*", "vow*", "let go", "moved on",
        "truth about", "admit*", "owned up", "responsib*"]),
    ("emotion", "Emotion", True, "medium", [
        "cry", "cried", "crying", "tear*", "sob*", "weep*", "wept", "tremble*", "trembl*", "shak*", "ache*", "aching", "grief",
        "joy*", "happy", "happier", "sad", "sadness", "fear*", "afraid", "terrif*", "panic*", "relief", "relieved", "despair*",
        "lonely", "loneliness", "heartbreak*", "heartbroken", "overwhelm*", "choke*", "swallow*", "throat tight", "chest tight",
        "laugh*", "smil*", "sigh*", "gasp*", "numb", "hollow", "ache", "heavy", "rush of"]),
    ("danger", "Danger", False, "high", [
        "danger*", "threat*", "peril*", "risk*", "deadly", "lethal", "kill*", "murder*", "death", "dying", "die", "died",
        "weapon*", "armed", "hostage*", "poison*", "knife*", "gunfire", "siren*", "alarm*", "emergency", "trapped", "survive*",
        "survival", "escape*", "fled", "flee*", "run!", "hunted", "hunt*", "predator*", "monster*", "beast*", "attack*", "assault*"]),
    ("humor", "Humor", False, "medium", [
        "laugh*", "giggl*", "chuckl*", "grin*", "smirk*", "joke*", "jok*", "witty", "wry", "sarcas*", "tease*", "teasing",
        "banter*", "quip*", "funny", "amus*", "ridiculous", "absurd*", "silly", "snort*", "snicker*", "cheeky", "deadpan",
        "rolled her eyes", "rolled his eyes", "eye roll*", "punchline", "pun"]),
    ("dread", "Dread", False, "medium", [
        "dread*", "horror", "horrif*", "ominous", "sinister", "eerie", "uncanny", "nightmare*", "haunt*", "ghost*", "corpse*",
        "grave*", "tomb*", "rot", "rotting", "decay*", "cold sweat", "chill*", "shiver*", "crawled", "skin crawl*",
        "dark*", "darkness", "gloom*", "foreboding", "doom*", "scream*", "bone*", "writhe*", "shriek*", "unnatural"]),
    ("loss", "Loss", False, "medium", [
        "loss", "lost", "grief", "griev*", "mourn*", "funeral*", "buried", "burial", "gone", "goodbye", "farewell", "widow*",
        "orphan*", "memorial", "empty chair", "never see", "never again", "passed away", "bereave*", "miss her", "miss him",
        "missed her", "missed him", "ashes", "condolence*", "left behind", "abandon*", "alone", "lonely"]),
    ("betrayal", "Betrayal", False, "medium", [
        "betray*", "traitor*", "treachery", "deceiv*", "deceit*", "decepti*", "lied to", "lies", "double-cross*", "backstab*",
        "sold us out", "sold me out", "turned on", "behind my back", "behind his back", "behind her back", "confess*",
        "revealed that", "the truth was", "all along", "never told", "kept from", "spy", "spies", "informant*", "mole",
        "secretly", "fake", "pretend*", "false"]),
    ("hope", "Hope", False, "low", [
        "hope*", "hopeful", "dawn", "sunrise", "bright*", "triumph*", "victor*", "saved", "rescue*",
        "freedom", "healed", "heal*", "renew*", "rebuil*", "reunite*", "reunion", "peace*", "promise*",
        "at last", "finally", "succeed*", "celebrat*", "cheer*", "recover*", "relief", "thrive*"]),
    ("intrigue", "Intrigue", False, "low", [
        "king*", "queen*", "throne*", "crown*", "court*", "council*", "senate*", "senator*", "lord*", "lady", "duke*", "duchess*",
        "emperor*", "empress*", "regent*", "heir*", "succession", "treaty", "treaties", "alliance*", "allies", "faction*",
        "conspir*", "plot*", "scheme*", "schem*", "manipulat*", "bribe*", "blackmail*", "rule*", "ruler*",
        "politic*", "minister*", "decree*", "noble*", "envoy*", "ambassador*", "coup", "rebel*", "loyal*", "oath"]),
]

STRANDS = [
    {"key": k, "label": label, "core": core, "confidence": conf}
    for k, label, core, conf, _ in _STRAND_DEFS
]
STRAND_KEYS = [s["key"] for s in STRANDS]
PACING_KEYS = ["dialogue_share", "avg_sentence_words", "short_sentence_share"]

# A strand never needs more than this many hits per 1,000 words to read as "fully present".
_MIN_SCALE = 2.0
_CACHE_LIMIT = 4000
_cache: "OrderedDict[str, dict]" = OrderedDict()


def _compile(terms: list[str]) -> re.Pattern:
    parts = []
    for term in terms:
        stem = term[:-1] if term.endswith("*") else term
        piece = re.escape(stem).replace(r"\ ", r"\s+")
        parts.append(piece + (r"\w*" if term.endswith("*") else ""))
    parts.sort(key=len, reverse=True)
    return re.compile(r"(?<![\w'])(?:" + "|".join(parts) + r")(?![\w'])", re.IGNORECASE)


_PATTERNS = {k: _compile(terms) for k, _l, _c, _f, terms in _STRAND_DEFS}

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])[\"”’')\]]*\s+|\n+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s and s.strip()]


def _dialogue_words(text: str) -> int:
    total = 0
    for quoted in re.findall(r"[\"“]([^\"”\n]{1,600})[\"”]", text):
        total += len(_WORD.findall(quoted))
    return total


def analyze_text(raw: str, lore_terms: list[str] | None = None, evidence_per_strand: int = 6) -> dict:
    """Raw strand hits, word count, pacing numbers, and evidence sentences for one block of text."""
    text = html_to_text(raw or "")
    lore_terms = sorted({t.strip() for t in (lore_terms or []) if t and len(t.strip()) > 2})
    key = hashlib.md5((text + "\x00" + "\x01".join(lore_terms)).encode("utf-8", "ignore")).hexdigest()
    cached = _cache.get(key)
    if cached is not None:
        _cache.move_to_end(key)
        return cached

    lore_pattern = _compile(lore_terms) if lore_terms else None
    sentences = _sentences(text)
    words = len(_WORD.findall(text))
    hits = {k: 0.0 for k in STRAND_KEYS}
    evidence = {k: [] for k in STRAND_KEYS}
    short = 0
    questions = 0

    for index, sentence in enumerate(sentences):
        sentence_words = len(_WORD.findall(sentence))
        if 0 < sentence_words <= 6:
            short += 1
        if sentence.rstrip("”\"'’) ").endswith("?"):
            questions += 1
        for strand, pattern in _PATTERNS.items():
            found = [m.group(0).lower() for m in pattern.finditer(sentence)]
            if found:
                hits[strand] += len(found)
                evidence[strand].append({"sentence": sentence[:320], "matches": sorted(set(found))[:5], "order": index})
        if lore_pattern is not None:
            found = [m.group(0).lower() for m in lore_pattern.finditer(sentence)]
            if found:
                hits.setdefault("lore", 0.0)
                hits["lore"] += len(found)
                evidence.setdefault("lore", []).append({"sentence": sentence[:320], "matches": sorted(set(found))[:5], "order": index})

    # Structure adds to suspense: clipped sentences and open questions make a reader lean in.
    if sentences:
        short_share = short / len(sentences)
        if len(sentences) >= 6 and short_share > 0.35:
            hits["suspense"] += (short_share - 0.35) * len(sentences) * 0.8
        hits["suspense"] += questions * 0.4

    for strand in evidence:
        ranked = sorted(evidence[strand], key=lambda e: (-len(e["matches"]), e["order"]))[:evidence_per_strand]
        evidence[strand] = sorted(ranked, key=lambda e: e["order"])

    result = {
        "words": words,
        "hits": hits,
        "evidence": evidence,
        "pacing": {
            "dialogue_share": round(_dialogue_words(text) / words, 3) if words else 0.0,
            "avg_sentence_words": round(words / len(sentences), 1) if sentences else 0.0,
            "short_sentence_share": round(short / len(sentences), 3) if sentences else 0.0,
        },
    }
    _cache[key] = result
    if len(_cache) > _CACHE_LIMIT:
        _cache.popitem(last=False)
    return result


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _density(hits: float, words: int) -> float:
    return hits * 1000.0 / words if words else 0.0


def _trend(values: list[float]) -> dict:
    n = len(values)
    if n < 3:
        return {"direction": "flat", "change": 0.0, "peak_index": max(range(n), key=lambda i: values[i]) if n else 0}
    third = max(1, n // 3)
    early = sum(values[:third]) / third
    late = sum(values[-third:]) / third
    change = late - early
    direction = "rising" if change > 12 else "fading" if change < -12 else "flat"
    return {"direction": direction, "change": round(change, 1), "peak_index": max(range(n), key=lambda i: values[i])}


def build_story_shape(units: list[dict], lore_terms: list[str] | None = None) -> dict:
    """units: [{scene_id, title, chapter_id, chapter_title, content}] in reading order."""
    analyses = [analyze_text(u["content"], lore_terms) for u in units]
    strands = list(STRANDS)
    keys = list(STRAND_KEYS)
    if lore_terms:
        strands = strands + [{"key": "lore", "label": "Lore density", "core": False, "confidence": "high"}]
        keys.append("lore")

    scales = {}
    for key in keys:
        densities = [_density(a["hits"].get(key, 0.0), a["words"]) for a in analyses if a["words"] >= 40]
        scales[key] = max(_percentile(densities, 0.9), _MIN_SCALE)

    def score(hits: float, words: int, key: str) -> float:
        return round(min(100.0, _density(hits, words) / scales[key] * 100.0), 1)

    scenes = []
    for unit, a in zip(units, analyses):
        scenes.append({
            "scene_id": unit["scene_id"],
            "title": unit["title"],
            "chapter_id": unit["chapter_id"],
            "chapter_title": unit["chapter_title"],
            "words": a["words"],
            "scores": {k: score(a["hits"].get(k, 0.0), a["words"], k) for k in keys},
            "pacing": a["pacing"],
        })

    chapters = []
    by_chapter: "OrderedDict[str, list[int]]" = OrderedDict()
    for i, unit in enumerate(units):
        by_chapter.setdefault(unit["chapter_id"], []).append(i)
    for chapter_id, idxs in by_chapter.items():
        words = sum(analyses[i]["words"] for i in idxs)
        hits = {k: sum(analyses[i]["hits"].get(k, 0.0) for i in idxs) for k in keys}
        dialogue = sum(analyses[i]["pacing"]["dialogue_share"] * analyses[i]["words"] for i in idxs)
        chapters.append({
            "chapter_id": chapter_id,
            "title": units[idxs[0]]["chapter_title"],
            "scene_ids": [units[i]["scene_id"] for i in idxs],
            "words": words,
            "scores": {k: score(hits[k], words, k) for k in keys},
            "pacing": {"dialogue_share": round(dialogue / words, 3) if words else 0.0},
        })

    total_words = sum(a["words"] for a in analyses)
    total_hits = {k: sum(a["hits"].get(k, 0.0) for a in analyses) for k in keys}
    book_scores = {k: score(total_hits[k], total_words, k) for k in keys}

    chapter_trends = {k: _trend([c["scores"][k] for c in chapters]) for k in keys}
    scene_trends = {k: _trend([s["scores"][k] for s in scenes]) for k in keys}
    trends = {k: (chapter_trends[k] if len(chapters) >= 3 else scene_trends[k]) for k in keys}

    return {
        "strands": strands,
        "scenes": scenes,
        "chapters": chapters,
        "book": {"words": total_words, "scores": book_scores},
        "trends": trends,
        "method": (
            "Counts of words and phrases for each strand, per 1,000 words, scaled against this book's own busiest scenes. "
            "No AI is used. Scores show emphasis, not quality; open the evidence to see what raised them."
        ),
    }
