"""
Thedral Studio - Cognitive Reader Moments & Plain-English Comprehension Adapter
Wires `cognitive_reader.CognitiveEngine` directly into Thedral's Reader Simulation payload.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import sys

# Ensure the project root ('Thedral-main 2') and 'cognitive_reader_pkg' (if sibling) are on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _candidate_path in (
    _PROJECT_ROOT,
    _PROJECT_ROOT / "cognitive_reader_pkg",
    _PROJECT_ROOT.parent / "cognitive_reader_pkg",
):
    if (_candidate_path / "cognitive_reader" / "__init__.py").exists():
        if str(_candidate_path) not in sys.path:
            sys.path.insert(0, str(_candidate_path))
        break

from cognitive_reader import CognitiveEngine, build_cognitive_database
from backend.reader_text import clip_excerpt

_ENGINE_INSTANCE: Optional[CognitiveEngine] = None


def get_thedral_cognitive_engine() -> CognitiveEngine:
    """Lazy-loads CognitiveEngine and links THEDRAL_WIKTIONARY_SQLITE_PATH if configured."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        db_path = Path(__file__).resolve().parent / "data" / "cognitive_lexicon.db"
        wikt_env = os.environ.get("THEDRAL_WIKTIONARY_SQLITE_PATH", "").strip()
        if not db_path.exists() and wikt_env and os.path.exists(wikt_env):
            build_cognitive_database(output_db_path=db_path, wiktionary_sqlite_path=wikt_env)
        _ENGINE_INSTANCE = CognitiveEngine(db_path=db_path)
    return _ENGINE_INSTANCE


# -----------------------------------------------------------------------------
# Compatibility Shims required by `backend/reader_story.py` (Line 10)
# -----------------------------------------------------------------------------
def _subtext_moments(paragraphs: List[str], paragraph_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    engine = get_thedral_cognitive_engine()
    report = engine.analyze_document("\n\n".join(paragraphs))
    results: List[Dict[str, Any]] = []
    for sub in report.subtext_hits:
        p_idx = next((i for i, p in enumerate(paragraphs) if sub.utterance in p), 0)
        results.append({
            "type": "subtext",
            "label": f"Subtext ({sub.subtext_category})",
            "paragraph_index": p_idx,
            "excerpt": f'"{sub.utterance}"',
            "body": sub.comprehension_note,
        })
    return results


def _irony_moments(paragraphs: List[str], paragraph_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    engine = get_thedral_cognitive_engine()
    report = engine.analyze_document("\n\n".join(paragraphs))
    return [
        {
            "type": "irony",
            "label": f"Dramatic irony for {ep.character}",
            "paragraph_index": ep.paragraph_index,
            "excerpt": clip_excerpt(paragraphs[ep.paragraph_index]) if 0 <= ep.paragraph_index < len(paragraphs) else "",
            "body": ep.explanation,
        }
        for ep in report.epistemic_alerts
    ]


def _empathy_moments(paragraphs: List[str], paragraph_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return []


def _loss_and_care(paragraphs: List[str], paragraph_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return []


def _trust_shifts(paragraphs: List[str], paragraph_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return []


# -----------------------------------------------------------------------------
# Main Comprehension & Beta-Reader Moments Builder
# -----------------------------------------------------------------------------
def build_comprehension_payload(
    paragraphs: List[str],
    paragraph_metrics: List[Dict[str, Any]],
    thread_report: Dict[str, Any],
    feel_report: Dict[str, Any],
) -> Dict[str, Any]:
    if not paragraphs:
        return {
            "moments": [],
            "comprehension": {
                "headline": "The reader doesn't have enough story on the page yet.",
                "summary": "Add a few paragraphs of scene text to run the cognitive reader simulation.",
                "knows_now": [],
                "worries_now": [],
                "questions_now": [],
                "subtext_signals": [],
                "payoff_moments": [],
                "irony_moments": [],
                "humor_moments": [],
                "missed_connections": [],
            },
        }

    engine = get_thedral_cognitive_engine()
    full_text = "\n\n".join(paragraphs)
    report = engine.analyze_document(full_text)

    for idx, tick in enumerate(report.ticks):
        if idx < len(paragraph_metrics):
            pm = paragraph_metrics[idx]
            pm["tension"] = round(max(float(pm.get("tension", 0.0)), tick.felt_arousal), 2)
            pm["subtext"] = round(
                max(
                    float(pm.get("subtext", 0.0)),
                    min(1.0, sum(h.divergence_score for h in tick.subtext_hits) * 0.45),
                ),
                2,
            )
            pm["sensory"] = round(
                max(float(pm.get("sensory", 0.0)), sum(tick.sensory_profile.values())),
                2,
            )

    moments: List[Dict[str, Any]] = []
    subtext_signals: List[Dict[str, Any]] = []
    irony_moments: List[Dict[str, Any]] = []
    payoff_moments: List[Dict[str, Any]] = []
    missed_connections: List[Dict[str, Any]] = []

    for alert in report.continuity_alerts:
        p_idx = alert.paragraph_index
        excerpt = clip_excerpt(paragraphs[p_idx]) if 0 <= p_idx < len(paragraphs) else alert.trigger_span
        label_map = {
            "LIGHTING_CONTRADICTION": "Wait—isn't it dark in here?",
            "MEMORY_DECAY_FAILURE": f"Who is {alert.entity} again?",
            "ENTITY_NAME_COLLISION": f"Possible name typo: {alert.entity}",
            "NGRAM_TYPO_ANOMALY": f"Possible word typo: '{alert.trigger_span}'",
        }
        label = label_map.get(alert.alert_type, f"Continuity check ({alert.entity})")
        item = {
            "type": "continuity",
            "label": label,
            "paragraph_index": p_idx,
            "excerpt": excerpt,
            "body": alert.explanation,
        }
        moments.append(item)
        missed_connections.append({
            "name": alert.entity,
            "paragraph_index": p_idx,
            "gap": 1,
            "excerpt": excerpt,
            "body": alert.explanation,
        })

    for sub in report.subtext_hits:
        p_idx = next((i for i, p in enumerate(paragraphs) if sub.utterance in p), 0)
        label_map = {
            "GRICEAN_EVASION": f"{sub.speaker or 'Character'} dodges the question",
            "QUANTITY_ASYMMETRY": f"{sub.speaker or 'Character'} stonewalls",
            "TEMPORAL_HYPERBOLE_SARCASM": f"Dry snark from {sub.speaker or 'Speaker'}",
            "POLARITY_INVERSION_SARCASM": f"Sarcasm / insincerity ({sub.speaker or 'Speaker'})",
            "SOMATIC_MASKING": f"Polite mask hiding tension ({sub.speaker or 'Speaker'})",
        }
        item = {
            "type": "subtext",
            "label": label_map.get(sub.subtext_category, "Unspoken subtext"),
            "paragraph_index": p_idx,
            "excerpt": f'"{sub.utterance}"',
            "body": sub.comprehension_note,
        }
        moments.append(item)
        subtext_signals.append(item)

    for ep in report.epistemic_alerts:
        p_idx = ep.paragraph_index
        excerpt = clip_excerpt(paragraphs[p_idx]) if 0 <= p_idx < len(paragraphs) else ""
        body = (
            f"Suspense spike: because `{ep.character}` wasn't in the room earlier, "
            f"*we* know about `{ep.fact_id}`, but `{ep.character}` has no idea what they're walking into."
        )
        item = {
            "type": "irony",
            "label": f"Dramatic irony for {ep.character}",
            "paragraph_index": p_idx,
            "excerpt": excerpt,
            "body": body,
        }
        moments.append(item)
        irony_moments.append(item)

    for met in report.metaphors:
        p_idx = next((i for i, p in enumerate(paragraphs) if met.span in p), 0)
        item = {
            "type": "payoff",
            "label": f"Vivid image: '{clip_excerpt(met.span, 45)}'",
            "paragraph_index": p_idx,
            "excerpt": met.span,
            "body": met.comprehension_note,
        }
        moments.append(item)
        payoff_moments.append(item)

    for h_idx in report.habituation_warnings[:2]:
        if 0 <= h_idx < len(paragraphs):
            excerpt = clip_excerpt(paragraphs[h_idx])
            body = (
                "I'm starting to go a little numb here. We've had several intense paragraphs in a row "
                "without a breather, so the high-stakes words are starting to blur together."
            )
            moments.append({
                "type": "concern",
                "label": "Intensity is starting to blur together",
                "paragraph_index": h_idx,
                "excerpt": excerpt,
                "body": body,
            })

    moments.sort(key=lambda m: m.get("paragraph_index", 0))

    last_tick = report.ticks[-1] if report.ticks else None
    active_cast = last_tick.present_cast if last_tick else []
    wm_slots = last_tick.working_memory_slots if last_tick else []

    knows_now: List[str] = []
    if active_cast:
        knows_now.append(f"On stage right now: {', '.join(active_cast[:6])}.")
    if wm_slots:
        knows_now.append(f"Front of the reader's mind: {', '.join(wm_slots[:5])}.")
    if report.resolved_aliases:
        alias_pairs = [f"'{k}' = {v}" for k, v in list(report.resolved_aliases.items())[:3]]
        knows_now.append(f"Connected character titles: {', '.join(alias_pairs)}.")
    if last_tick and last_tick.lighting_state == "DARK":
        knows_now.append("The scene lighting is currently pitch dark.")

    worries_now: List[str] = [a.explanation for a in report.continuity_alerts[:3]]
    if not worries_now and report.epistemic_alerts:
        worries_now.append(irony_moments[0]["body"])
    if not worries_now and subtext_signals:
        worries_now.append(subtext_signals[0]["body"])

    questions_now: List[str] = [
        f"Waiting to see how `{p.cue_phrase}` pays off (open for {p.current_word_distance:,} words)."
        for p in report.promises if not p.resolved
    ][:4]
    if not questions_now:
        questions_now = (feel_report.get("open_loops") or [])[:3]

    headline = (
        f"Tracking {len(active_cast)} character(s) across {report.total_paragraphs} paragraphs "
        f"({len(subtext_signals)} subtext catch(es), {len(report.metaphors)} vivid image(s))."
    )
    summary = (
        knows_now[0] + (" " + worries_now[0] if worries_now else " Scene continuity looks solid.")
        if knows_now
        else "The reader is settling into the opening atmosphere."
    )

    return {
        "moments": moments[:18],
        "comprehension": {
            "headline": headline,
            "summary": summary,
            "knows_now": knows_now,
            "worries_now": worries_now,
            "questions_now": questions_now,
            "subtext_signals": subtext_signals[:5],
            "payoff_moments": payoff_moments[:5],
            "irony_moments": irony_moments[:5],
            "humor_moments": [s for s in subtext_signals if "snark" in s["label"].lower() or "sarcasm" in s["label"].lower()][:4],
            "missed_connections": missed_connections[:5],
        },
    }