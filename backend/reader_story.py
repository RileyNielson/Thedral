"""
Thedral Sovereign Studio — Deterministic Reader Story & Experience Engine
Integrates CognitiveEngine, psycholinguistic lexical modeling, and narrative
trajectory tracking into plain-English beta reader commentary without LLM dependencies.
"""

import re
from pathlib import Path
from typing import Any, Dict, List

from backend.config import WIKTIONARY_DB_PATH
from backend.reader_feel import analyze_reader_feel
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import get_lexicon_status
from backend.reader_cues import _reader_cues, _paragraphs, _sentences
from backend.reader_threads import _turns, _find_reader_threads
from backend.reader_text import (
    _clean,
    _search,
    _in_dialogue,
    _scene_text,
    _first_matching_sentence,
    _last_matching_sentence,
    _windows,
    _anchors,
    _state,
    _KIN,
    _GENERIC,
)
from backend.reader_moments import (
    get_thedral_cognitive_engine,
    _empathy_moments,
    _loss_and_care,
    _trust_shifts,
    clip_excerpt,
)


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
            "empathy_moments": [],
            "subtext_moments": [],
            "irony_moments": [],
            "trust_shifts": [],
            "experience_moments": [],
            "summary": "This scene is not in the manuscript’s active reading order.",
        }

    text = html_to_text(current_content or "").strip()
    paragraphs = _paragraphs(text)
    cues = _reader_cues(lexicon_path)
    lexicon = get_lexicon_status(lexicon_path)

    # 1. Structural Turns (Yes, but / No, and)
    turns = _turns(paragraphs, cues)

    # 2. Causal Story Threads (Setup -> Callback -> Payoff)
    threads = _find_reader_threads(scenes, selected_index, text, cues)

    # 3. Emotional Dynamics (Loss, Empathy, Trust Shifts)
    emotional_payoffs = _loss_and_care(paragraphs, cues)
    empathy_moments = _empathy_moments(paragraphs, cues)
    trust_shifts = _trust_shifts(paragraphs, cues)

    # 4. Cognitive Reading Simulation (Subtext, Dramatic Irony, Sensory Fatigue, Continuity)
    subtext_moments = []
    irony_moments = []
    cognitive_payoffs = []
    continuity_alerts = []

    try:
        engine = get_thedral_cognitive_engine()
        report = engine.analyze_document(text)

        # Map Subtext & Gricean Evasions to Beta-Reader voice
        for sub in report.subtext_hits:
            p_idx = next((i + 1 for i, p in enumerate(paragraphs) if sub.utterance in p), 1)
            headline_map = {
                "GRICEAN_EVASION": f"{sub.speaker or 'The character'} dodges the question",
                "QUANTITY_ASYMMETRY": f"{sub.speaker or 'The character'} stonewalls the exchange",
                "TEMPORAL_HYPERBOLE_SARCASM": f"Dry sarcasm from {sub.speaker or 'the speaker'}",
                "POLARITY_INVERSION_SARCASM": f"Insincere tone from {sub.speaker or 'the speaker'}",
                "SOMATIC_MASKING": f"Polite mask hiding inner tension",
            }
            subtext_moments.append({
                "kind": "subtext",
                "headline": headline_map.get(sub.subtext_category, "Unspoken subtext tension"),
                "reaction": sub.comprehension_note,
                "confidence": "Subtext marker detected",
                "paragraph": p_idx,
                "evidence": f'"{sub.utterance}"',
                "payoff_evidence": f'"{sub.utterance}"',
                "setup_evidence": "",
                "setup_title": "",
            })

        # Map Dramatic Irony
        for ep in report.epistemic_alerts:
            p_idx = ep.paragraph_index + 1
            excerpt = clip_excerpt(paragraphs[ep.paragraph_index]) if 0 <= ep.paragraph_index < len(paragraphs) else ""
            reaction = (
                f"Suspense spike: We know about {ep.fact_id}, but {ep.character} has no idea what they're walking into."
            )
            irony_moments.append({
                "kind": "irony",
                "headline": f"Dramatic irony for {ep.character}",
                "reaction": reaction,
                "confidence": "Asymmetric information",
                "paragraph": p_idx,
                "evidence": excerpt,
                "payoff_evidence": excerpt,
                "setup_evidence": f"Established knowledge: {ep.fact_id}",
                "setup_title": "Prior established fact",
            })

        # Map Metaphors / Imagery
        for met in report.metaphors:
            p_idx = next((i + 1 for i, p in enumerate(paragraphs) if met.span in p), 1)
            cognitive_payoffs.append({
                "kind": "imagery",
                "headline": f"Vivid image: “{clip_excerpt(met.span, 45)}”",
                "reaction": met.comprehension_note,
                "confidence": "Sensory mapping",
                "paragraph": p_idx,
                "evidence": met.span,
                "payoff_evidence": met.span,
                "setup_evidence": "",
                "setup_title": "",
            })

        # Map Continuity / Physical Glitches
        for alert in report.continuity_alerts:
            p_idx = alert.paragraph_index + 1
            continuity_alerts.append({
                "kind": "continuity",
                "headline": f"Continuity check ({alert.entity})",
                "reaction": alert.explanation,
                "confidence": "Sensory contradiction",
                "paragraph": p_idx,
                "evidence": alert.trigger_span,
                "payoff_evidence": alert.trigger_span,
                "setup_evidence": "",
                "setup_title": "",
            })

    except Exception:
        pass

    # 5. Pacing and Atmosphere Moments
    experience_moments = analyze_reader_feel(current_content)
    for moment in experience_moments:
        moment["setup_scene_id"] = selected_scene_id
        moment["payoff_scene_id"] = selected_scene_id

    experience_moments.extend(cognitive_payoffs)
    experience_moments.extend(continuity_alerts)

    total_insights = (
        len(turns)
        + len(threads)
        + len(emotional_payoffs)
        + len(empathy_moments)
        + len(subtext_moments)
        + len(irony_moments)
        + len(trust_shifts)
        + len(experience_moments)
    )

    summary = (
        "There are clear story currents and reader beats active here."
        if total_insights > 0
        else "No distinct narrative turns, callbacks, or subtext surfaced in this draft yet."
    )

    return {
        "scene_id": selected_scene_id,
        "scene_index": selected_index,
        "summary": summary,
        "turns": turns,
        "threads": threads,
        "emotional_payoffs": emotional_payoffs,
        "empathy_moments": empathy_moments,
        "subtext_moments": subtext_moments,
        "irony_moments": irony_moments,
        "trust_shifts": trust_shifts,
        "experience_moments": experience_moments,
        "disclaimer": "Confident predictions of reader perception based on deterministic linguistic modeling.",
        "method": "Transparent structural and psycholinguistic modeling via CognitiveEngine. Zero generative AI.",
        "lexicon": {
            "available": lexicon["available"],
            "source": "Cognitive Lexicon (Wiktionary + Lancaster Norms)",
            "license": lexicon.get("license"),
            "attribution": lexicon.get("attribution"),
        },
    }
