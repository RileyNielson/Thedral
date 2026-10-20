import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

from backend.config import WIKTIONARY_DB_PATH
from backend.reader_feel import analyze_reader_feel
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import expand_lexical_terms, get_lexicon_status
from backend.reader_cues import _cached_reader_cues, _reader_cues

# Fallback for clip_excerpt in case reader_text.py doesn't export it
try:
    from backend.reader_text import clip_excerpt
except ImportError:
    try:
        from backend.reader_text import excerpt as clip_excerpt
    except ImportError:
        def clip_excerpt(text: str, max_chars: int = 140) -> str:
            clean = " ".join((text or "").split())
            return clean if len(clean) <= max_chars else clean[:max_chars - 3].rstrip() + "..."

from backend.reader_text import _paragraphs
from backend.reader_moments import get_thedral_cognitive_engine


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
    lexicon = get_lexicon_status(lexicon_path)

    # 1. Run the new Cognitive Engine once
    engine = get_thedral_cognitive_engine()
    report = engine.analyze_document(text)

    # 2. Map Cognitive Output to Thedral's UI Arrays
    subtext_moments = []
    for sub in report.subtext_hits:
        p_idx = next((i for i, p in enumerate(paragraphs) if sub.utterance in p), 0)
        label_map = {
            "GRICEAN_EVASION": f"{sub.speaker or 'Character'} dodges the question",
            "QUANTITY_ASYMMETRY": f"{sub.speaker or 'Character'} stonewalls",
            "TEMPORAL_HYPERBOLE_SARCASM": f"Dry snark from {sub.speaker or 'Speaker'}",
            "POLARITY_INVERSION_SARCASM": f"Sarcasm / insincerity ({sub.speaker or 'Speaker'})",
            "SOMATIC_MASKING": f"Polite mask hiding tension ({sub.speaker or 'Speaker'})",
        }
        subtext_moments.append({
            "type": "subtext",
            "label": label_map.get(sub.subtext_category, "Unspoken subtext"),
            "paragraph_index": p_idx,
            "excerpt": f'"{sub.utterance}"',
            "body": sub.comprehension_note,
        })

    irony_moments = []
    for ep in report.epistemic_alerts:
        p_idx = ep.paragraph_index
        irony_moments.append({
            "type": "irony",
            "label": f"Dramatic irony for {ep.character}",
            "paragraph_index": p_idx,
            "excerpt": clip_excerpt(paragraphs[p_idx]) if 0 <= p_idx < len(paragraphs) else "",
            "body": ep.explanation,
        })

    # Keep original reader feels (pacing, rhythm) and inject cognitive metaphors/continuity
    experience_moments = analyze_reader_feel(current_content)
    for moment in experience_moments:
        moment["setup_scene_id"] = selected_scene_id
        moment["payoff_scene_id"] = selected_scene_id

    for met in report.metaphors:
        p_idx = next((i for i, p in enumerate(paragraphs) if met.span in p), 0)
        experience_moments.append({
            "type": "payoff",
            "label": f"Vivid image: '{clip_excerpt(met.span, 45)}'",
            "paragraph_index": p_idx,
            "excerpt": met.span,
            "body": met.comprehension_note,
            "setup_scene_id": selected_scene_id,
            "payoff_scene_id": selected_scene_id,
        })

    for alert in report.continuity_alerts:
        experience_moments.append({
            "type": "continuity",
            "label": f"Continuity check ({alert.entity})",
            "paragraph_index": alert.paragraph_index,
            "excerpt": alert.trigger_span,
            "body": alert.explanation,
            "setup_scene_id": selected_scene_id,
            "payoff_scene_id": selected_scene_id,
        })

    # 3. Build Story Threads from the Cognitive Character Cast & Chekhov Promises
    threads = []
    last_tick = report.ticks[-1] if report.ticks else None
    if last_tick:
        for entity in last_tick.present_cast:
            threads.append({
                "id": f"thread_char_{entity.lower().replace(' ', '_')}",
                "name": entity,
                "type": "character",
                "active": True,
            })
    for prom in report.promises:
        threads.append({
            "id": prom.promise_id,
            "name": prom.cue_phrase[:32],
            "type": "promise",
            "active": not prom.resolved,
            "distance": prom.current_word_distance,
        })

    insights = len(experience_moments) + len(threads) + len(subtext_moments) + len(irony_moments)
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
        "turns": [],
        "emotional_payoffs": [],
        "empathy_moments": [],
        "subtext_moments": subtext_moments,
        "irony_moments": irony_moments,
        "trust_shifts": [],
        "disclaimer": (
            "These are confident predictions of a typical reader’s experience, "
            "grounded in the deterministic cognitive model."
        ),
        "method": "Transparent structural and psycholinguistic modeling via CognitiveEngine. Zero generative AI.",
        "lexicon": {
            "available": lexicon["available"],
            "source": "Cognitive Lexicon (Wiktionary + WordNet + Lancaster Norms)",
            "license": lexicon.get("license"),
            "attribution": lexicon.get("attribution"),
        },
    }


def analyze_promises(text: str) -> list[dict]:
    promises = []
    engine = get_thedral_cognitive_engine()
    cog_report = engine.analyze_document(text or "")

    for prom in cog_report.promises:
        promises.append({
            "type": "chekhov_causal_span",
            "severity": "medium" if prom.tension_tautness >= 0.4 else "low",
            "title": f"Unresolved Setup (P{prom.setup_paragraph + 1})",
            "setup_paragraph": prom.setup_paragraph,
            "excerpt": prom.cue_phrase,
            "suggestion": (
                f"Planted {prom.current_word_distance:,} words ago (`{prom.cue_phrase}`). "
                f"Make sure this thread is reminded or cashed in before it decays."
            ),
        })
    return promises
