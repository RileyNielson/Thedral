import re

from backend.text_utils import html_to_text
from backend.reader_cues import _key_terms, _sentences

_IDIOMS = re.compile(
    r"\b(?:dead (?:center|centre|sprint|silent|still|end|air|weight|quiet|ahead|"
    r"asleep|tired|serious|calm|on)|stopped dead|stopped short|"
    r"(?:held|hold|holding) (?:together|on|tight|steady|up|back|still|out)|"
    r"(?:dead|stopped) in (?:his|her|their|my) tracks|wrong (?:way|turn|side|door)|"
    r"dead (?:rodents?|leaves|wood|weeds?))\b",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return _IDIOMS.sub(" ", text)


def _search(pattern: re.Pattern, text: str):
    return pattern.search(_clean(text))


def _in_dialogue(sentence: str) -> bool:
    return any(mark in sentence for mark in '"“”')


_KIN = {
    "father", "mother", "brother", "sister", "son", "daughter", "wife", "husband",
    "mentor", "friend", "dad", "mom", "grandmother", "grandfather", "uncle", "aunt",
}


_GENERIC = {
    "his", "her", "him", "she", "its", "our", "who", "how", "why", "all", "one",
    "was", "had", "for", "and", "but", "not", "the", "you", "own", "way", "day",
    "night", "time", "life", "eyes", "hand", "hands", "heart", "back", "like",
}


def _anchors(text: str) -> set[str]:
    terms = {re.sub(r"['’]s$", "", term) for term in _key_terms(text)}
    return {term for term in terms if len(term) > 2 and term not in _GENERIC}


def _windows(text: str):
    """Yield (sentence, sentence plus its predecessor), newest first, so a pronoun
    subject can lean on the sentence that names who it is."""
    sentences = _sentences(text)
    for index in range(len(sentences) - 1, -1, -1):
        previous = sentences[index - 1] if index else ""
        yield sentences[index], f"{previous} {sentences[index]}"


def _first_matching_sentence(text: str, pattern: re.Pattern) -> str:
    return next(
        (sentence for sentence in _sentences(text) if _search(pattern, sentence)),
        "",
    )


def _last_matching_sentence(text: str, pattern: re.Pattern) -> str:
    return next(
        (sentence for sentence in reversed(_sentences(text)) if _search(pattern, sentence)),
        "",
    )


def _scene_text(scene: dict) -> str:
    return html_to_text(scene.get("content") or "").strip()


def _state(text: str, cues: dict[str, re.Pattern]) -> str | None:
    positive = bool(_search(cues["positive"], text))
    negative = bool(_search(cues["negative"], text))
    if positive == negative:
        return None
    return "yes" if positive else "no"


