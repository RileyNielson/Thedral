from fastapi import APIRouter
import time
import uuid
from pydantic import BaseModel

from backend.config import ENABLE_AI
from backend.database import get_db
from backend.socratic import elevate_prose_diagnosis, get_socratic_lesson, SOCRATIC_OFFLINE_NOTICE
from backend.ai_helper import ai_meta, deterministic_brief
from backend.telemetry import classify_paragraph_energetics
from backend.text_utils import html_to_text

# Re-exported so existing imports from backend.routers.craft keep working.
from backend.routers.reader_simulation import (  # noqa: F401
    AddDisclosureRequest,
    AuthorHorizonNote,
    ScanDisclosureRequest,
    _preceding_scene_context,
    _quoted_excerpt,
    _reader_loop_signal,
    _scene_revision_ref,
    _serialize_simulation,
    _store_reader_simulation,
    get_scene_disclosures,
    get_scene_reader_simulations,
    scan_scene_disclosures,
)
from backend.routers.reader_feedback import (  # noqa: F401
    ReaderFeedbackCreate,
    create_reader_feedback,
    delete_reader_feedback,
    get_book_reader_feedback,
    get_scene_reader_feedback,
)

router = APIRouter(tags=["Craft"])


class ElevateRequest(BaseModel):
    passage: str
    surrounding: str = ""
    scene_id: str | None = None

class XRayRequest(BaseModel):
    text: str
    staccato_threshold: int = 9
    expansive_threshold: int = 22
    clutter_sensitivity: int = 2

@router.post("/api/craft/elevate")
def elevate_prose(payload: ElevateRequest):
    observations = ""
    if payload.scene_id and ENABLE_AI:
        conn = get_db()
        try:
            row = conn.execute("SELECT content FROM binder_nodes WHERE id = ?", (payload.scene_id,)).fetchone()
            if row and row["content"]:
                observations = deterministic_brief(html_to_text(row["content"]), conn)
        finally:
            conn.close()
    critique = elevate_prose_diagnosis(
        passage=html_to_text(payload.passage),
        surrounding=html_to_text(payload.surrounding),
        scene_id=payload.scene_id,
        observations=observations
    )
    used_ai = ENABLE_AI and critique != SOCRATIC_OFFLINE_NOTICE and bool(payload.passage.strip())

    critique_id = f"crit_{uuid.uuid4().hex[:8]}"
    if payload.scene_id and used_ai:
        conn = get_db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute("""
                INSERT INTO editorial_critiques 
                (id, scene_id, passage_text, critique_text, status, created_at)
                VALUES (?, ?, ?, ?, 'OPEN', ?)
            """, (critique_id, payload.scene_id, payload.passage[:300], critique, now))
        conn.close()

    return {"critique": critique, "critique_id": critique_id, **ai_meta(used_ai)}

@router.post("/api/craft/xray")
def get_craft_xray(payload: XRayRequest):
    """Returns multi-lens paragraph data with zero document scrambling."""
    thresholds = {
        "staccato_threshold": payload.staccato_threshold,
        "expansive_threshold": payload.expansive_threshold,
        "clutter_sensitivity": payload.clutter_sensitivity,
    }
    paragraphs = classify_paragraph_energetics(html_to_text(payload.text), thresholds)
    flat_sentences = [s for p in paragraphs for s in p]
    return {
        "paragraphs": paragraphs,
        "sentences": flat_sentences,
        "thresholds": thresholds
    }

class CritiqueStatusUpdate(BaseModel):
    status: str

@router.get("/api/critiques/scene/{scene_id}")
def get_scene_critiques(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, scene_id, passage_text, critique_text, status, created_at, resolved_at 
        FROM editorial_critiques 
        WHERE scene_id = ? 
        ORDER BY created_at DESC
    """, (scene_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@router.put("/api/critiques/{critique_id}/status")
def update_critique_status(critique_id: str, payload: CritiqueStatusUpdate):
    conn = get_db()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    resolved_time = now if payload.status == "ADDRESSED" else None
    with conn:
        conn.execute("""
            UPDATE editorial_critiques 
            SET status = ?, resolved_at = ? 
            WHERE id = ?
        """, (payload.status, resolved_time, critique_id))
    conn.close()
    return {"status": "updated"}

class TutorRequest(BaseModel):
    question: str
    context: str = ""

@router.post("/api/craft/teach")
def ask_socratic_tutor(payload: TutorRequest):
    lesson = get_socratic_lesson(payload.question, payload.context)
    return {"lesson": lesson}

