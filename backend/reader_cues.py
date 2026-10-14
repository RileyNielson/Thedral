import re
from functools import lru_cache
from pathlib import Path

from backend.config import WIKTIONARY_DB_PATH
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import expand_lexical_terms

_STOP_WORDS = {
    "about", "after", "again", "against", "among", "because", "before", "being",
    "between", "could", "does", "doing", "down", "each", "from", "have", "having",
    "into", "just", "more", "most", "other", "over", "same", "should", "some",
    "such", "than", "that", "their", "them", "then", "there", "these", "they",
    "this", "those", "through", "under", "until", "very", "were", "what", "when",
    "where", "which", "while", "whom", "with", "would", "your", "also", "been",
    "will", "shall", "must", "need", "needs", "want", "wants", "make", "made",
    "someone", "somebody", "anyone", "anybody", "thing", "things", "someone's",
}
_PROMISE_CUES = re.compile(
    r"\b(?:promise[sd]?|swore|sworn|vowed|owe[sd]?|have to|has to|"
    r"must|won['’]t stop|won['’]t rest|one day|"
    r"was going to|set out to|need to|needs to)\b",
    re.IGNORECASE,
)
_POSITIVE_CUES = re.compile(
    r"\b(?:found|saved|won|escaped|survived|succeeded|success|worked|"
    r"agreed|accepted|opened|arrived|managed|rescued|reached|kept|"
    r"answered|returned|remembered|learned|discovered|revealed|admitted)\b",
    re.IGNORECASE,
)
_NEGATIVE_CUES = re.compile(
    r"\b(?:failed|lost|refused|denied|rejected|broke|missed|couldn['’]t|"
    r"wouldn['’]t|cannot|can['’]t|dead|died|death|killed|stopped|"
    r"betrayed|lied|wounded|injured|wrong)\b",
    re.IGNORECASE,
)
_RESOLUTION_CUES = re.compile(
    r"\b(?:finally|at last|found|saved|opened|answered|returned|"
    r"remembered|learned|discovered|revealed|admitted|chose|decided|"
    r"understood|kept the promise|fulfilled)\b",
    re.IGNORECASE,
)
_LOSS_CUES = re.compile(
    r"\b(?:died|dies|funeral|grief|mourn(?:ed|ing)?|goodbye|killed|murdered|"
    r"butchered|passed away|death of|never came back|(?:was|is) gone forever)\b",
    re.IGNORECASE,
)
_CARE_CUES = re.compile(
    r"\b(?:loved(?! to\b)|trusted|protected|comforted|waited for|slept beside|"
    r"loyal|best friend|cared for|raised me|taught me|tucked me|"
    r"held (?:(?:the )?\w+['’]s|his|her|their|my|our) (?:hand|paw|face|head|body)s?)\b",
    re.IGNORECASE,
)
_VULNERABILITY_CUES = re.compile(
    r"\b(?:afraid|alone|ashamed|terrified|cried|wept|sobbed|"
    r"begged|confessed|admitted|couldn['’]t stop crying)\b",
    re.IGNORECASE,
)
_REVERSAL_CUES = re.compile(
    r"\b(?:instead|turned out|all along|suddenly|actually|after all|"
    r"until|not .{1,50} but|yet)\b",
    re.IGNORECASE,
)
_REASSURANCE_CUES = re.compile(
    r"\b(?:perfectly safe|nothing could go wrong|exactly as planned|"
    r"completely harmless|trust me|all under control|couldn['’]t fail)\b",
    re.IGNORECASE,
)
_CONTRAST_CUES = re.compile(r"\b(?:but|yet|however|although|though|instead)\b", re.IGNORECASE)
_AND_CUES = re.compile(r"\b(?:and then|and|then)\b", re.IGNORECASE)
_LEXICAL_SEEDS = {
    "promise": {"promise", "vow", "pledge"},
    "positive": {"success", "win", "rescue", "discovery", "answer"},
    "negative": {"failure", "loss", "death", "rejection", "betrayal", "injury"},
    "resolution": {"resolve", "answer", "discovery", "revelation", "decision"},
    "loss": {"death", "grief", "mourning", "bereavement"},
    "care": {"care", "love", "trust", "protection", "comfort", "loyalty"},
    "vulnerability": {"fear", "loneliness", "shame", "terror", "crying", "confession"},
}


@lru_cache(maxsize=16)
def _cached_reader_cues(
    lexicon_path: str, modification_time: int, file_size: int
) -> dict[str, re.Pattern]:
    del modification_time, file_size
    fallbacks = {
        "promise": _PROMISE_CUES,
        "positive": _POSITIVE_CUES,
        "negative": _NEGATIVE_CUES,
        "resolution": _RESOLUTION_CUES,
        "loss": _LOSS_CUES,
        "care": _CARE_CUES,
        "vulnerability": _VULNERABILITY_CUES,
    }
    cues = {}
    for category, seeds in _LEXICAL_SEEDS.items():
        terms = expand_lexical_terms(seeds, lexicon_path)
        lexical_pattern = (
            r"\b(?:" + "|".join(re.escape(term) for term in sorted(terms)) + r")\b"
            if terms else r"(?!)"
        )
        cues[category] = re.compile(
            f"(?:{fallbacks[category].pattern})|(?:{lexical_pattern})",
            re.IGNORECASE,
        )
    cues["reversal"] = _REVERSAL_CUES
    cues["reassurance"] = _REASSURANCE_CUES
    return cues


def _reader_cues(lexicon_path: str | Path | None = None) -> dict[str, re.Pattern]:
    target = Path(lexicon_path) if lexicon_path else WIKTIONARY_DB_PATH
    if target.is_file():
        stat = target.stat()
        return _cached_reader_cues(str(target), stat.st_mtime_ns, stat.st_size)
    return _cached_reader_cues(str(target), 0, 0)


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", html_to_text(text)) if part.strip()]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def _key_terms(text: str) -> set[str]:
    return {
        token.lower().strip("'’")
        for token in re.findall(r"[A-Za-z][A-Za-z'’_-]{2,}", text)
        if token.lower().strip("'’") not in _STOP_WORDS
    }


def _named_terms(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\b[A-Z][a-z]{2,}\b", text)
        if token.lower() not in {"the", "then", "this", "that", "when", "what"}
    }


