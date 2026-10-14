import asyncio
import hashlib
import json
import sqlite3
import time
import uuid
import re
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import STUDIO_MODEL, LLM_OPTIONS, ENABLE_AI
from backend.database import get_db
from backend.ai_helper import deterministic_brief
from backend.text_utils import html_to_text

router = APIRouter(tags=["Reader Simulation"])


from backend.reader_simulation_store import (  # noqa: F401
    READER_SIMULATION_PROMPT_VERSION,
    READER_CONTEXT_CHAR_LIMIT,
    READER_SIMULATION_SYSTEM_PROMPT,
    READER_EXPERIENCE_DIMENSIONS,
    _quoted_excerpt,
    _serialize_simulation,
    _preceding_scene_context,
    _scene_revision_ref,
    _store_reader_simulation,
    _reader_loop_signal,
)

class ScanDisclosureRequest(BaseModel):
    scene_id: str
    text: str
    reading_mode: Literal["scene", "sequential"] = "scene"

class AddDisclosureRequest(BaseModel):
    scene_id: str
    disclosure_type: str
    narrative_claim: str
    clue_evidence: str = ""


class AuthorHorizonNote(BaseModel):
    scene_id: str
    disclosure_type: str
    narrative_claim: str = Field(min_length=1, max_length=1000)
    source_excerpt: str = Field(default="", max_length=1000)
    clue_evidence: str = Field(default="", max_length=1000)


@router.get("/api/disclosures/scene/{scene_id}")
def get_scene_disclosures(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, disclosure_type, narrative_claim, clue_evidence, source_excerpt, confidence, source, target_reveal_ch, status
        FROM reader_disclosures 
        WHERE scene_id = ? 
        ORDER BY id ASC
    """, (scene_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@router.post("/api/disclosures/scan")
async def scan_scene_disclosures(payload: ScanDisclosureRequest):
    if not payload.text or len(payload.text.strip()) < 30:
        return {"status": "empty", "disclosures": []}

    conn = get_db()
    scene = conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (payload.scene_id,),
    ).fetchone()
    conn.close()
    if not scene:
        raise HTTPException(404, "Scene not found")

    source_text = html_to_text(payload.text)
    intended_takeaway = ""
    analyzed_text = source_text[:3500]
    takeaway_hash = hashlib.sha256(intended_takeaway.encode("utf-8")).hexdigest()
    conn = get_db()
    reading_context = (
        _preceding_scene_context(conn, payload.scene_id)
        if payload.reading_mode == "sequential"
        else ""
    )
    analyzed_hash = hashlib.sha256(
        json.dumps(
            [payload.reading_mode, reading_context, analyzed_text],
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    input_hash = hashlib.sha256(
        json.dumps(
            [payload.reading_mode, reading_context, source_text],
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    cached = conn.execute("""
        SELECT id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
               intended_takeaway_hash, prompt_version, source_text, analyzed_text,
               reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
               model_name, reused_from_id, created_at
        FROM reader_simulations
        WHERE scene_id = ? AND source_content_hash = ? AND intended_takeaway_hash = ?
          AND prompt_version = ?
    """, (
        payload.scene_id, input_hash, takeaway_hash, READER_SIMULATION_PROMPT_VERSION
    )).fetchone()
    if cached:
        conn.close()
        return {
            "status": "success",
            "simulation": _serialize_simulation(cached),
            "reused": True,
            "warnings": [],
        }
    reusable = conn.execute("""
        SELECT id, system_prompt, result_json, model_name
        FROM reader_simulations
        WHERE scene_id = ? AND analyzed_content_hash = ? AND intended_takeaway_hash = ?
          AND prompt_version = ? AND model_name = ?
        ORDER BY created_at DESC, rowid DESC LIMIT 1
    """, (
        payload.scene_id, analyzed_hash, takeaway_hash,
        READER_SIMULATION_PROMPT_VERSION, STUDIO_MODEL,
    )).fetchone()
    conn.close()

    if reusable:
        system_prompt = reusable["system_prompt"]
        result_json = reusable["result_json"]
        model_name = reusable["model_name"]
        reused_from_id = reusable["id"]
        warnings = []
    elif not ENABLE_AI:
        return {"status": "error", "message": "Reader simulation unavailable (local AI is disabled)."}
    else:
        grounding = ""
        try:
            grounding = deterministic_brief(analyzed_text)
        except Exception:
            grounding = ""
        if reading_context:
            prompt_content = (
                "Recent preceding manuscript text (a limited context window; no author notes):\n"
                + reading_context
                + "\n\nCurrent scene excerpt:\n"
                + analyzed_text
            )
        elif payload.reading_mode == "sequential":
            prompt_content = (
                "No earlier scenes with saved text precede this scene in manuscript order.\n\n"
                "Current scene excerpt:\n" + analyzed_text
            )
        else:
            prompt_content = "Current scene excerpt (the only manuscript text supplied):\n" + analyzed_text
        if grounding:
            prompt_content += "\n\n" + grounding
        def find_evidence(quote: str) -> tuple[str, str]:
            excerpt = _quoted_excerpt(analyzed_text, quote)
            if excerpt:
                return excerpt, "current_scene"
            excerpt = _quoted_excerpt(reading_context, quote)
            return (excerpt, "prior_context") if excerpt else ("", "")

        try:
            import ollama
            resp = await asyncio.to_thread(
                ollama.chat,
                model=STUDIO_MODEL,
                messages=[
                    {"role": "system", "content": READER_SIMULATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                format="json",
                options=LLM_OPTIONS
            )
            data = json.loads(resp["message"]["content"])
        except Exception as e:
            return {"status": "error", "message": f"Reader simulation failed: {e}"}

        if not isinstance(data, dict):
            return {"status": "error", "message": "Reader simulation returned an invalid response object."}
        disclosure_types = ("direct", "inferred", "delayed", "friction", "revision_focus")
        for disclosure_type in disclosure_types:
            if disclosure_type not in data:
                data[disclosure_type] = []
            elif not isinstance(data[disclosure_type], list):
                return {
                    "status": "error",
                    "message": f"Reader simulation returned an invalid {disclosure_type} list.",
                }

        warnings = []
        items = []
        for disclosure_type in disclosure_types:
            for item in data[disclosure_type]:
                if not isinstance(item, dict):
                    warnings.append(f"Skipped an ungrounded {disclosure_type} item.")
                    continue
                claim = str(item.get("claim", "")).strip()
                evidence, evidence_source = find_evidence(str(item.get("evidence", "")))
                if not claim or not evidence:
                    warnings.append(f"Skipped a {disclosure_type} item without a matching text excerpt.")
                    continue
                items.append({
                    "disclosure_type": disclosure_type.upper(),
                    "narrative_claim": claim,
                    "source_excerpt": evidence,
                    "evidence_source": evidence_source,
                })
        experience = data.get("reader_experience", {})
        if not isinstance(experience, dict):
            warnings.append("The AI reader-experience estimate had an invalid structure.")
            experience = {}
        for dimension, (disclosure_type, estimate_key) in READER_EXPERIENCE_DIMENSIONS.items():
            observations = experience.get(dimension, [])
            if not isinstance(observations, list):
                warnings.append(f"Skipped reader-experience estimates with an invalid {dimension} list.")
                continue
            for observation in observations[:3]:
                if not isinstance(observation, dict):
                    warnings.append(f"Skipped an invalid {dimension} estimate.")
                    continue
                evidence, evidence_source = find_evidence(str(observation.get("evidence", "")))
                estimate = str(observation.get(estimate_key, "")).strip()
                cause = str(observation.get("cause", "")).strip()
                level = observation.get("level")
                if (
                    not evidence
                    or not estimate
                    or not cause
                    or isinstance(level, bool)
                    or not isinstance(level, int)
                    or not 1 <= level <= 5
                ):
                    warnings.append(f"Skipped an ungrounded {dimension} estimate.")
                    continue
                items.append({
                    "disclosure_type": disclosure_type,
                    "narrative_claim": estimate,
                    "source_excerpt": evidence,
                    "evidence_source": evidence_source,
                    "moment": str(observation.get("moment", "")).strip(),
                    "cause": cause,
                    "level": level,
                })
        system_prompt = READER_SIMULATION_SYSTEM_PROMPT
        result_json = json.dumps(items)
        model_name = STUDIO_MODEL
        reused_from_id = None

    conn = get_db()
    revision_ref = _scene_revision_ref(conn, payload.scene_id, payload.text, source_text)
    simulation_id = f"sim_{uuid.uuid4().hex}"
    saved = _store_reader_simulation(
        conn,
        simulation_id=simulation_id,
        scene_id=payload.scene_id,
        revision_ref=revision_ref,
        source_content_hash=input_hash,
        analyzed_content_hash=analyzed_hash,
        intended_takeaway_hash=takeaway_hash,
        source_text=source_text,
        analyzed_text=analyzed_text,
        reading_mode=payload.reading_mode,
        reading_context=reading_context,
        intended_takeaway=intended_takeaway,
        system_prompt=system_prompt,
        result_json=result_json,
        model_name=model_name,
        reused_from_id=reused_from_id,
    )
    conn.close()

    return {
        "status": "success",
        "simulation": _serialize_simulation(saved),
        "reused": reused_from_id is not None or saved["id"] != simulation_id,
        "warnings": warnings,
    }


@router.get("/api/reader-simulations/scene/{scene_id}")
def get_scene_reader_simulations(scene_id: str):
    conn = get_db()
    if not conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (scene_id,),
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Scene not found")
    rows = conn.execute("""
        SELECT id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
               intended_takeaway_hash, prompt_version, source_text, analyzed_text,
               reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
               model_name, reused_from_id, created_at
        FROM reader_simulations
        WHERE scene_id = ?
        ORDER BY created_at DESC, rowid DESC
    """, (scene_id,)).fetchall()
    conn.close()
    simulations = [_serialize_simulation(row) for row in rows]
    return {
        "simulations": simulations,
        "loop_signal": _reader_loop_signal(simulations),
    }


@router.post("/api/disclosures/author-note")
def add_author_horizon_note(payload: AuthorHorizonNote):
    allowed_types = {"INTENDED", "DIRECT", "INFERRED", "DELAYED"}
    if payload.disclosure_type not in allowed_types:
        raise HTTPException(400, "Unsupported Reader Horizon note type")
    conn = get_db()
    scene = conn.execute(
        "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (payload.scene_id,),
    ).fetchone()
    if not scene:
        conn.close()
        raise HTTPException(404, "Scene not found")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO reader_disclosures
            (scene_id, disclosure_type, narrative_claim, clue_evidence, source_excerpt, confidence, source, status, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, 'AUTHOR', 'ACTIVE', ?)
        """, (
            payload.scene_id, payload.disclosure_type, payload.narrative_claim.strip(),
            payload.clue_evidence.strip(), payload.source_excerpt.strip(), now,
        ))
    conn.close()
    return {"status": "created"}

@router.delete("/api/disclosures/{item_id}")
def delete_disclosure(item_id: int):
    conn = get_db()
    try:
        with conn:
            cur = conn.execute("DELETE FROM reader_disclosures WHERE id = ?", (item_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Note not found")
        return {"status": "deleted"}
    finally:
        conn.close()



