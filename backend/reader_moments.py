import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import WIKTIONARY_DB_PATH
from backend.cognitive_reader.engine import CognitiveEngine
from backend.cognitive_reader.compiler import build_cognitive_database
from backend.reader_text import (
    _search,
    _first_matching_sentence,
    _last_matching_sentence,
)

_ENGINE_INSTANCE: Optional[CognitiveEngine] = None


def get_thedral_cognitive_engine() -> CognitiveEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        db_path = Path(__file__).resolve().parent / "data" / "cognitive_lexicon.db"
        wikt_path = str(WIKTIONARY_DB_PATH) if WIKTIONARY_DB_PATH.exists() else None
        
        if not db_path.exists():
            build_cognitive_database(output_db_path=db_path, wiktionary_sqlite_path=wikt_path)
            
        _ENGINE_INSTANCE = CognitiveEngine(db_path=db_path, wiktionary_db_path=wikt_path)
    return _ENGINE_INSTANCE


def clip_excerpt(text: str, max_chars: int = 140) -> str:
    clean = " ".join((text or "").split())
    return clean if len(clean) <= max_chars else clean[: max_chars - 3].rstrip() + "..."


def _loss_and_care(paragraphs: List[str], cues: dict[str, re.Pattern]) -> List[Dict[str, Any]]:
    moments = []
    care_bonds = []
    for idx, p in enumerate(paragraphs, 1):
        if _search(cues["care"], p):
            sent = _first_matching_sentence(p, cues["care"])
            cared_nouns = (
                set(re.findall(r"\b[A-Z][a-z]+\b", p))
                | set(re.findall(r"\b(?:dog|hound|horse|brother|sister|father|mother|friend|child)\b", p.lower()))
            )
            if cared_nouns:
                care_bonds.append((idx, sent, cared_nouns))

    if not care_bonds:
        return moments

    for idx, p in enumerate(paragraphs, 1):
        if "sunset" in p.lower() or "dusk" in p.lower():
            continue
        if _search(cues["loss"], p):
            loss_sent = _last_matching_sentence(p, cues["loss"])
            loss_nouns = (
                set(re.findall(r"\b[A-Z][a-z]+\b", p))
                | set(re.findall(r"\b(?:dog|hound|horse|brother|sister|father|mother|friend|child)\b", p.lower()))
            )
            for care_idx, care_sent, care_nouns in care_bonds:
                shared_nouns = care_nouns & loss_nouns
                if care_idx < idx and shared_nouns:
                    shared_label = ", ".join(shared_nouns)
                    moments.append({
                        "kind": "loss",
                        "headline": f"A bond broken by loss ({shared_label})",
                        "reaction": (
                            f"Because the prose established genuine care for {shared_label} first, "
                            "this loss will land as grief rather than mere event plot."
                        ),
                        "confidence": "Bond followed by loss cue",
                        "paragraph": idx,
                        "evidence": loss_sent[:700],
                        "payoff_evidence": loss_sent[:700],
                        "setup_evidence": care_sent[:400],
                        "setup_title": f"Paragraph {care_idx}",
                    })
                    return moments
    return moments


def _empathy_moments(paragraphs: List[str], cues: dict[str, re.Pattern]) -> List[Dict[str, Any]]:
    moments = []
    for idx, p in enumerate(paragraphs, 1):
        if re.search(r"\b(?:talk|speak|meet|leave|let|be)\s+(?:\w+\s+)?alone\b", p, re.IGNORECASE):
            continue

        if _search(cues["vulnerability"], p):
            sentence = _first_matching_sentence(p, cues["vulnerability"])
            if sentence:
                moments.append({
                    "kind": "empathy",
                    "headline": "An unshielded moment of vulnerability",
                    "reaction": (
                        "The character drops their defenses and lets the reader see their raw fear or doubt. "
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
