import re
from functools import lru_cache
from pathlib import Path

from backend.config import WIKTIONARY_DB_PATH
from backend.reader_feel import analyze_reader_feel
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import expand_lexical_terms, get_lexicon_status
from backend.reader_cues import _cached_reader_cues, _key_terms, _named_terms, _paragraphs, _reader_cues, _sentences  # noqa: F401
from backend.reader_moments import _empathy_moments, _irony_moments, _loss_and_care, _subtext_moments, _trust_shifts  # noqa: F401
from backend.reader_text import _anchors, _clean, _first_matching_sentence, _in_dialogue, _last_matching_sentence, _scene_text, _search, _state, _windows  # noqa: F401
from backend.reader_threads import _find_reader_threads, _promise_candidates, _turns  # noqa: F401

def analyze_reader_story(
    scenes: list[dict],
    selected_scene_id: str,
    current_content: str,
    lexicon_path: str | Path | None = None,
) -> dict:
    selected_index = next(
        (index for index, scene in enumerate(scenes) if scene["scene_id"] == selected_scene_id),
        None,
    )
    if selected_index is None:
        return {
            "scene_id": selected_scene_id,
            "turns": [],
            "threads": [],
            "emotional_payoffs": [],
            "trust_shifts": [],
            "summary": "This scene is not in the manuscript’s active reading order.",
        }

    text = html_to_text(current_content or "")
    paragraphs = _paragraphs(text)
    cues = _reader_cues(lexicon_path)
    lexicon = get_lexicon_status(lexicon_path)
    threads = _find_reader_threads(scenes, selected_index, text, cues)
    turns = _turns(paragraphs, cues)
    emotional_payoffs = _loss_and_care(scenes, selected_index, text, cues)
    empathy_moments = _empathy_moments(scenes, selected_index, text, cues)
    subtext_moments = _subtext_moments(text)
    irony_moments = _irony_moments(text, cues)
    trust_shifts = _trust_shifts(scenes, selected_index, text, cues)
    experience_moments = analyze_reader_feel(current_content)
    for moment in experience_moments:
        moment["setup_scene_id"] = selected_scene_id
        moment["payoff_scene_id"] = selected_scene_id
    insights = (
        len(experience_moments) + len(threads) + len(turns) + len(emotional_payoffs)
        + len(empathy_moments) + len(subtext_moments)
        + len(irony_moments) + len(trust_shifts)
    )
    summary = (
        "There’s a story turn here worth noticing."
        if insights
        else "No clear promise, payoff, or story turn surfaced here yet."
    )
    return {
        "scene_id": selected_scene_id,
        "scene_index": selected_index,
        "summary": summary,
        "experience_moments": experience_moments,
        "threads": threads,
        "turns": turns,
        "emotional_payoffs": emotional_payoffs,
        "empathy_moments": empathy_moments,
        "subtext_moments": subtext_moments,
        "irony_moments": irony_moments,
        "trust_shifts": trust_shifts,
        "disclaimer": (
            "These are confident predictions of a typical reader’s experience, "
            "grounded in the manuscript—not a guarantee that every reader will react the same way."
        ),
        "method": (
            "Transparent text-pattern rules expanded with local English Wiktionary word forms and synonyms; no generative AI is used."
            if lexicon["available"]
            else "Transparent text-pattern rules; no generative AI is used. A local Wiktionary index can expand word forms and synonyms."
        ),
        "lexicon": {
            "available": lexicon["available"],
            "source": lexicon.get("source"),
            "license": lexicon.get("license"),
            "attribution": lexicon.get("attribution"),
        },
    }

