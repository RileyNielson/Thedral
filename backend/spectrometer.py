import re

from backend.config import TENSION_KEYWORDS, FILTER_VERBS

SIGNAL_LEXICONS = {
    "action_cues": TENSION_KEYWORDS,
    "relational_cues": [
        "gaze", "eyes", "breath", "pulse", "fingers", "touch", "hand", "skin",
        "whisper", "throat", "heart", "lips", "blush", "shiver", "closer",
        "together", "kiss", "embrace", "hesitated", "looked away",
    ],
    "mystery_cues": [
        "secret", "truth", "lie", "hidden", "discovered", "clue", "cipher",
        "puzzle", "curious", "suspicious", "knew", "suspected", "strange",
        "unseen", "behind",
    ],
    "sensory_cues": [
        "scent", "smell", "sound", "light", "shadow", "stone", "sky", "wind",
        "rain", "fog", "mist", "cold", "frozen", "silence", "echo", "vast",
        "distant", "memory", "night", "stars", "water", "sea",
    ],
}


def _term_count(text: str, terms: list[str]) -> int:
    return sum(
        len(re.findall(r"\b" + re.escape(term) + r"\b", text, flags=re.IGNORECASE))
        for term in terms
    )


def analyze_text_signals(text: str) -> dict:
    """Measure selected prose patterns without inferring a reader's biological state."""
    if not text or not text.strip():
        return {
            "word_count": 0,
            "signals": {
                f"{name}_per_1000_words": {"count": 0, "rate": 0.0}
                for name in SIGNAL_LEXICONS
            },
            "patterns": {
                "dialogue_paragraph_pct": 0.0,
                "short_sentence_pct": 0.0,
                "long_sentence_pct": 0.0,
                "question_marks_per_1000_words": 0.0,
            },
            "limitations": "Text-pattern counts do not measure reader emotions, comprehension, or biological responses.",
        }

    words = len(text.split())
    lowered = text.lower()
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    sentence_lengths = [len(sentence.split()) for sentence in sentences if sentence.split()]
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    dialogue_paragraphs = sum(
        '"' in paragraph or "“" in paragraph or "‘" in paragraph
        for paragraph in paragraphs
    )
    sentence_count = max(1, len(sentence_lengths))
    paragraph_count = max(1, len(paragraphs))

    return {
        "word_count": words,
        "signals": {
            f"{name}_per_1000_words": {
                "count": count,
                "rate": round((count / words) * 1000, 1),
            }
            for name, terms in SIGNAL_LEXICONS.items()
            for count in [_term_count(lowered, terms)]
        },
        "patterns": {
            "dialogue_paragraph_pct": round((dialogue_paragraphs / paragraph_count) * 100, 1),
            "short_sentence_pct": round((sum(length <= 8 for length in sentence_lengths) / sentence_count) * 100, 1),
            "long_sentence_pct": round((sum(length >= 22 for length in sentence_lengths) / sentence_count) * 100, 1),
            "question_marks_per_1000_words": round((text.count("?") / words) * 1000, 1),
        },
        "limitations": "Text-pattern counts do not measure reader emotions, comprehension, or biological responses.",
    }
