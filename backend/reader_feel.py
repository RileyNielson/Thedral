"""Text-only estimates of what a reader experiences, with no author input.

Every detector reads structure the prose itself exposes: paragraph rhythm, who is
afraid of whom, where the vocabulary changes, what is stated and then undercut,
and how a scene opens and closes. Each insight carries the passages it rests on.
"""
import re
from collections import Counter

from backend.text_utils import html_to_text


_FIRST_PERSON = re.compile(r"\b(?:I|my|me|myself|I['’](?:d|m|ll|ve))\b")
_FEAR = re.compile(
    r"\b(?:terrified|trembl\w*|panick\w*|jittery|ghastly|stammer\w*|shak(?:ing|en)|"
    r"afraid|scared|frightened|quaver\w*|jumped out of (?:his|her|their) boots|"
    r"hissed|whisper\w*|tremor)\b",
    re.IGNORECASE,
)
_DREAD = re.compile(
    r"\b(?:blood\w*|crimson|curdl\w*|rust\w*|speckle\w*|suffocat\w*|ominous|dread\w*|"
    r"unnatural|hush\w*|shudder\w*|tremor|eclipse|cold sweat|shatter\w*|"
    r"sickening|raw|torment|wail\w*|scream\w*)\b",
    re.IGNORECASE,
)
_DANGER = re.compile(
    r"\b(?:guards?|alarm|chase[ds]?|bolt(?:ed)?|scrambl\w*|sprint\w*|crash\w*|"
    r"shriek\w*|blade|caught|cornered|hid|hiding|pressing flat|shadow\w*|"
    r"halberds?|torch\w*|footsteps|boots)\b",
    re.IGNORECASE,
)
_RELEASE = re.compile(
    r"\b(?:let out a (?:\w+ )?breath|exhaled|breathed out|sagged|slumped|"
    r"heart (?:slowed|settled)|finally (?:alone|safe))\b",
    re.IGNORECASE,
)
_BLAME = re.compile(
    r"\b(?:told (?:them|him|her|everyone)|claim(?:ed|ing)|insist(?:ed|ing)|"
    r"accus(?:ed|ing)|blam(?:ed|ing)|swore|swears)\b",
    re.IGNORECASE,
)
_NARRATOR_KNOWS = re.compile(
    r"\b(?:of course|heaven forbid|outwitted|instead|no,|rather than|truth|really)\b",
    re.IGNORECASE,
)
_RULE = re.compile(r"\b(?:rules?|don['’]t get|must not)\b", re.IGNORECASE)
_BREAK = re.compile(r"\b(?:until now|broken|broke|breaking)\b", re.IGNORECASE)
_CERTAINTY = re.compile(
    r"\b(?:knew|known|certain|sure|planned|bet|counted on|supposed to|should)\b",
    re.IGNORECASE,
)
_FUTURE_INTENT = re.compile(
    r"\b(?:going to|will|soon|someday|one day|have to|had to)\b", re.IGNORECASE
)
_SIMILE = re.compile(r"\blike (?:a|an|the) [a-z'’ -]{3,40}", re.IGNORECASE)
VOICE_THRESHOLD = 5
_SKIP_TERMS = {
    "the", "then", "this", "that", "when", "what", "but", "and", "his", "her", "they",
    "she", "its", "right", "huh", "just", "now", "left", "behind", "every", "all",
}


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _is_prose(paragraph: str) -> bool:
    stripped = paragraph.strip()
    if stripped.startswith("[") or re.match(r"(?i)^(?:chapter|scene|part|book)\b", stripped):
        return False
    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters):
        return False
    return len(stripped.split()) > 8 or stripped[-1] in '.!?"”’—…'


def _words(text: str) -> int:
    return len(text.split())


def _has_quote(text: str) -> bool:
    return any(mark in text for mark in '"“”')


def _first(text: str, pattern: re.Pattern) -> str:
    return next((s for s in _sentences(text) if pattern.search(s)), "")


def _capitalized_terms(text: str) -> Counter:
    counts: Counter = Counter()
    for sentence in _sentences(text):
        for token in re.findall(r"\b[A-Z][a-z]{2,}\b", sentence)[1:] if sentence[:1].isupper() \
                else re.findall(r"\b[A-Z][a-z]{2,}\b", sentence):
            if token.lower() not in _SKIP_TERMS:
                counts[token] += 1
    return counts


def _item(kind, headline, reaction, confidence, paragraph, evidence, setup=""):
    return {
        "kind": kind,
        "headline": headline,
        "reaction": reaction,
        "confidence": confidence,
        "paragraph": paragraph,
        "evidence": evidence[:700],
        "payoff_evidence": evidence[:700],
        "setup_evidence": setup[:400],
        "setup_title": "Earlier in this scene",
    }


def _paragraph_index(paragraphs: list[str], sentence: str) -> int | None:
    return next((i for i, p in enumerate(paragraphs, 1) if sentence and sentence in p), None)


def _opening(paragraphs: list[str]) -> list[dict]:
    opening = " ".join(paragraphs[:3])
    opening = " ".join(opening.split()[:140])
    rule, broken = _first(opening, _RULE), _first(opening, _BREAK)
    if rule and broken:
        return [_item(
            "hook", "Opens on a rule and its breaking",
            "The first lines set a rule and break it in the same breath. Readers "
            "will start with a promise of trouble and a narrator who already has a record.",
            "Rule and violation in the opening lines", 1, broken, rule,
        )]
    if len(_DANGER.findall(opening)) >= 2:
        sentence = _first(opening, _DANGER)
        return [_item(
            "hook", "Opens in the middle of trouble",
            "The scene begins already in motion, so readers are working out the "
            "situation while the pressure is on.",
            "Danger language in the first lines", 1, sentence,
        )]
    return []


def _tempo(paragraphs: list[str]) -> list[dict]:
    counts = [_words(p) for p in paragraphs]
    best = None
    for start in range(1, len(paragraphs) - 4):
        window = range(start, start + 5)
        short = [i for i in window if counts[i] <= 12 and not _has_quote(paragraphs[i])]
        mean = sum(counts[i] for i in window) / 5
        if len(short) >= 2 and mean <= 20 and min(counts[i] for i in window) <= 5 \
                and counts[start - 1] >= 30:
            if best is None or (len(short), -mean) > (len(best[2]), -best[0]):
                best = (mean, start, short)
    if not best:
        return []
    mean, start, short = best
    return [_item(
        "tempo", "The pace snaps tight",
        f"Five paragraphs average {mean:.0f} words, and {len(short)} are twelve words or "
        f"fewer, right after a {counts[start - 1]}-word paragraph. Readers will speed "
        "up and read it as a sprint.",
        "Paragraph rhythm", start + 1,
        " / ".join(paragraphs[i] for i in short[:3]), paragraphs[start - 1][:300],
    )]


def _release(paragraphs: list[str]) -> list[dict]:
    items = []
    for index, paragraph in enumerate(paragraphs):
        if index < 3 or not _RELEASE.search(paragraph):
            continue
        before = paragraphs[index - 3:index]
        if sum(len(_DANGER.findall(p)) for p in before) >= 3:
            items.append(_item(
                "release", "A moment to breathe",
                "After a run of pressure, the scene finally lets go. Readers will "
                "exhale with the narrator, and that relief makes the next push land harder.",
                "Release after sustained danger", index + 1,
                _first(paragraph, _RELEASE) or paragraph, _first(before[-1], _DANGER),
            ))
            break
    return items


def _atmosphere(paragraphs: list[str]) -> list[dict]:
    scores = [len(_DREAD.findall(p)) for p in paragraphs]
    for index in range(4, len(paragraphs)):
        if scores[index] >= 2 and sum(scores[index - 4:index]) / 4 <= 0.5:
            words = Counter(m.group(0).lower() for m in _DREAD.finditer(paragraphs[index]))
            names = ", ".join(f"“{word}”" for word, _ in words.most_common(3))
            return [_item(
                "atmosphere", "The air changes",
                f"The language turns to {names} after a stretch in a different register. "
                "Readers will feel something has gone wrong before anyone says it.",
                "Vocabulary shift", index + 1, paragraphs[index][:500],
                _sentences(paragraphs[index - 1])[-1] if paragraphs[index - 1] else "",
            )]
    return []


def _fear_target(paragraphs: list[str], text: str) -> tuple[str, int] | None:
    others = [
        i for i, p in enumerate(paragraphs)
        if _has_quote(p) and _FEAR.search(p) and not _FIRST_PERSON.search(re.sub(r'["“”].*?["“”]', "", p))
    ]
    if len(others) < 2:
        return None
    window = " ".join(paragraphs[max(0, others[0] - 6): others[-1] + 7])
    in_fear = re.sub(r'["“”].*?["“”]', " ", " ".join(paragraphs[i] for i in others))
    scene_counts = _capitalized_terms(text)
    best = None
    for term in _capitalized_terms(window):
        if term in in_fear or scene_counts[term] < 3:
            continue
        article = len(re.findall(rf"\bthe {term}\b(?! [A-Z])", text))
        fear_sentences = sum(
            1 for s in _sentences(text) if term in s and _FEAR.search(s)
        )
        score = article * 2 + fear_sentences
        if article >= 2 and (best is None or score > best[1]):
            best = (term, score)
    return (best[0], others[0]) if best else None


def _fear_of_unseen(paragraphs: list[str], text: str) -> list[dict]:
    found = _fear_target(paragraphs, text)
    if not found:
        return []
    term, fear_index = found
    mentions = len(re.findall(rf"\b{term}\b", text))
    fear_paragraph = paragraphs[fear_index]
    mention = next(
        (s for p in paragraphs for s in _sentences(p) if term in s and _has_quote(s)),
        _first(text, re.compile(rf"\b{term}\b")),
    )
    return [_item(
        "fear_of_unseen", f"Readers will learn to fear the {term}",
        f"The people around the narrator shake and whisper when the {term} comes up "
        f"({mentions} mentions in this scene). Readers take their fear as proof: "
        f"the {term} becomes a real threat without needing to appear.",
        "Fear shown by others, aimed at one name", fear_index + 1,
        _first(fear_paragraph, _FEAR) or fear_paragraph, mention,
    )]


def _false_story(paragraphs: list[str], text: str, target: str | None) -> list[dict]:
    if not target or len(_FIRST_PERSON.findall(text)) < 15:
        return []
    for index, paragraph in enumerate(paragraphs):
        for sentence in _sentences(paragraph):
            if target in sentence and _BLAME.search(sentence):
                reply = " ".join(paragraphs[index + 1:index + 3])
                if _FIRST_PERSON.search(reply) and _NARRATOR_KNOWS.search(reply):
                    return [_item(
                        "false_story", "Readers know the truth the characters don't",
                        f"A character credits the {target} with what happened, and "
                        "the narrator's reply shows they know better. Readers are "
                        "in on the secret and will watch the gap widen.",
                        "Claim answered by the narrator", index + 1,
                        next(
                            (p for p in paragraphs[index + 1:index + 3] if _NARRATOR_KNOWS.search(p)),
                            reply,
                        ),
                        sentence,
                    )]
    return []


def _voice(paragraphs: list[str], text: str) -> list[dict]:
    words = _words(text)
    if words < 300 or len(_FIRST_PERSON.findall(text)) / words * 1000 < 20:
        return []
    similes = [s for s in _sentences(text) if _SIMILE.search(s)]
    quips = [
        paragraph for paragraph in paragraphs
        if _words(paragraph) <= 4 and not _has_quote(paragraph)
    ]
    questions = [
        s for p in paragraphs if not _has_quote(p)
        for s in _sentences(p) if s.endswith("?")
    ]
    asides = len(re.findall(r"—[^—]{3,60}—", text))
    markers = len(similes) + len(quips) + len(questions) + asides
    rate = markers / words * 1000
    if rate < VOICE_THRESHOLD:
        return []
    return [_item(
        "voice", "The narrator’s personality is carrying the scene",
        f"{len(similes)} comparisons, {len(quips)} one-beat asides, "
        f"{len(questions)} questions asked out loud and {asides} dashed asides in "
        f"{words} words. Readers will hear a personality before they follow a plot, "
        "and the scene works as a voice-first read.",
        "Voice markers per thousand words", _paragraph_index(paragraphs, similes[0]) or 1,
        similes[0] if similes else quips[0],
        quips[0] if quips and similes else "",
    )]


def _undercut_plan(paragraphs: list[str]) -> list[dict]:
    for index in range(1, len(paragraphs)):
        paragraph = paragraphs[index]
        if _words(paragraph) <= 3 and not _has_quote(paragraph):
            before = next(
                (
                    paragraphs[i] for i in (index - 1, index - 2)
                    if i >= 0 and _words(paragraphs[i]) >= 40 and _CERTAINTY.search(paragraphs[i])
                ),
                "",
            )
            if before:
                return [_item(
                    "undercut", "A confident plan gets cut off",
                    "The scene states a plan with certainty and then undercuts it in a "
                    "few words. Readers will stop trusting the plan and brace for it to fail.",
                    "Certainty followed by a fragment", index + 1, paragraph,
                    _first(before, _CERTAINTY),
                )]
    return []


def _closing(paragraphs: list[str], text: str) -> list[dict]:
    last = paragraphs[-1]
    narrated = re.sub(r'["“”].*?["“”]', " ", last)
    if _words(last) > 40 or not (
        (_FUTURE_INTENT.search(narrated) and _FIRST_PERSON.search(narrated))
        or (narrated.rstrip().endswith("?") and _FIRST_PERSON.search(narrated))
    ):
        return []
    scene_counts = _capitalized_terms(text)
    terms = [t for t in re.findall(r"\b[A-Z][a-z]{2,}\b", last) if scene_counts[t] >= 3]
    if not terms:
        return []
    term = terms[0]
    setup = next(
        (s for p in paragraphs[:-1] for s in _sentences(p) if re.search(rf"\b{term}\b", s)), ""
    )
    return [_item(
        "closing", "The scene ends on a target",
        f"The last line points the narrator at the {term}, which the scene has "
        f"mentioned {scene_counts[term]} times. Readers will leave with that "
        "confrontation as the thing they're waiting for.",
        "Closing intent aimed at a recurring name", len(paragraphs), last, setup,
    )]


def analyze_reader_feel(content: str) -> list[dict]:
    text = html_to_text(content or "").strip()
    paragraphs = [p for p in _paragraphs(text) if _is_prose(p)]
    text = "\n\n".join(paragraphs)
    if len(paragraphs) < 5 or _words(text) < 150:
        return []
    target = _fear_target(paragraphs, text)
    items = (
        _opening(paragraphs)
        + _voice(paragraphs, text)
        + _undercut_plan(paragraphs)
        + _atmosphere(paragraphs)
        + _tempo(paragraphs)
        + _fear_of_unseen(paragraphs, text)
        + _false_story(paragraphs, text, target[0] if target else None)
        + _release(paragraphs)
        + _closing(paragraphs, text)
    )
    return sorted(items, key=lambda item: item["paragraph"] or 0)
