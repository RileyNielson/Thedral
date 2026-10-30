"""
Thedral Studio — Cognitive Reader Moments & Dynamic Emotion Detectors
Provides deterministic implementations for Loss/Grief, Empathy, and Trust shifts,
fully formatted for the Inspector Reader Tab.
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
from backend.reader_text import (
    _search,
    _first_matching_sentence,
    _last_matching_sentence,
    _windows,
    _anchors,
    _KIN,
)

_ENGINE_INSTANCE: Optional[CognitiveEngine] = None


def get_thedral_cognitive_engine() -> CognitiveEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        db_path = Path(__file__).resolve().parent / "data" / "cognitive_lexicon.db"
        wikt_env = os.environ.get("THEDRAL_WIKTIONARY_SQLITE_PATH", "").strip()
        if not db_path.exists() and wikt_env and os.path.exists(wikt_env):
            build_cognitive_database(output_db_path=db_path, wiktionary_sqlite_path=wikt_env)
        _ENGINE_INSTANCE = CognitiveEngine(db_path=db_path)
    return _ENGINE_INSTANCE


def clip_excerpt(text: str, max_chars: int = 140) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= max_chars else clean[: max_chars - 3].rstrip() + "..."


def _loss_and_care(paragraphs: List[str], cues: dict[str, re.Pattern]) -> List[Dict[str, Any]]:
    """Detects where loss occurs after an established bond of care."""
    moments = []
    text = " ".join(paragraphs)
    has_loss = bool(_search(cues["loss"], text))
    has_care = bool(_search(cues["care"], text))

    if not (has_loss and has_care):
        return moments

    care_para_idx = next((i + 1 for i, p in enumerate(paragraphs) if _search(cues["care"], p)), 1)
    loss_para_idx = next((i + 1 for i, p in enumerate(paragraphs) if _search(cues["loss"], p)), len(paragraphs))

    care_sentence = _first_matching_sentence(text, cues["care"])
    loss_sentence = _last_matching_sentence(text, cues["loss"])

    if care_sentence and loss_sentence:
        moments.append({
            "kind": "loss",
            "headline": "A bond broken by loss",
            "reaction": (
                "Because the prose established genuine care and attachment first, "
                "this separation will land as grief rather than mere event plot."
            ),
            "confidence": "Bond followed by loss cue",
            "paragraph": loss_para_idx,
            "evidence": loss_sentence[:700],
            "payoff_evidence": loss_sentence[:700],
            "setup_evidence": care_sentence[:400],
            "setup_title": f"Paragraph {care_para_idx}",
        })
    return moments


def _empathy_moments(paragraphs: List[str], cues: dict[str, re.Pattern]) -> List[Dict[str, Any]]:
    """Detects raw vulnerability or unshielded admission that invites reader empathy."""
    moments = []
    for idx, p in enumerate(paragraphs, 1):
        if _search(cues["vulnerability"], p):
            sentence = _first_matching_sentence(p, cues["vulnerability"])
            if sentence:
                moments.append({
                    "kind": "empathy",
                    "headline": "An unshielded moment of vulnerability",
                    "reaction": (
                        "The character drops their defenses and lets the reader see their raw fear or shame. "
                        "Readers step closer when the facade cracks."
                    ),
                    "confidence": "Vulnerability marker",
                    "paragraph": idx,
                    "evidence": sentence[:700],
                    "payoff_evidence": sentence[:700],
                    "setup_evidence": "",
                    "setup_title": "",
                })
                break
    return moments


def _trust_shifts(paragraphs: List[str], cues: dict[str, re.Pattern]) -> List[Dict[str, Any]]:
    """Detects broken promises, false reassurances, or sudden trust fractures."""
    moments = []
    for idx, p in enumerate(paragraphs, 1):
        reassurance = bool(_search(cues["reassurance"], p))
        negative = bool(_search(cues["negative"], p))

        if reassurance and negative:
            moments.append({
                "kind": "trust_shift",
                "headline": "False comfort turns into an alert",
                "reaction": (
                    "The reassurance collapses against an immediate negative reality. "
                    "Readers will withdraw trust and brace for failure."
                ),
                "confidence": "Reassurance broken by negative cue",
                "paragraph": idx,
                "evidence": p[:700],
                "payoff_evidence": p[:700],
                "setup_evidence": "",
                "setup_title": "",
            })
            break
    return moments
