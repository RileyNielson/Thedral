import time
import uuid
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_db

router = APIRouter(tags=["Reader Feedback"])


class ReaderFeedbackCreate(BaseModel):
    scene_id: str
    revision_ref: str = "CURRENT"
    reader_label: str = Field(default="", max_length=80)
    confusion_rating: int | None = Field(default=None, ge=1, le=5)
    engagement_rating: int | None = Field(default=None, ge=1, le=5)
    tension_rating: int | None = Field(default=None, ge=1, le=5)
    empathy_rating: int | None = Field(default=None, ge=1, le=5)
    response: str = Field(default="", max_length=4000)


@router.get("/api/reader-feedback/book/{book_id}")
def get_book_reader_feedback(book_id: str):
    conn = get_db()
    if not conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'BOOK'",
        (book_id,),
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Manuscript not found")
    rows = conn.execute("""
        SELECT f.id, f.scene_id, f.revision_ref, f.reader_label, f.confusion_rating,
               f.engagement_rating, f.tension_rating, f.empathy_rating, f.response, f.created_at,
               s.title AS scene_title, ch.title AS chapter_title
        FROM reader_feedback f
        JOIN binder_nodes s ON s.id = f.scene_id AND s.node_type = 'SCENE'
        JOIN binder_nodes ch ON ch.id = s.parent_id AND ch.node_type = 'CHAPTER'
        WHERE f.book_id = ?
        ORDER BY ch.sort_order, s.sort_order, f.created_at, f.id
    """, (book_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/api/reader-feedback/scene/{scene_id}")
def get_scene_reader_feedback(scene_id: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT id, revision_ref, reader_label, confusion_rating, engagement_rating,
               tension_rating, empathy_rating, response, created_at
        FROM reader_feedback WHERE scene_id = ?
        ORDER BY created_at DESC, id DESC
    """, (scene_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.post("/api/reader-feedback")
def create_reader_feedback(payload: ReaderFeedbackCreate):
    revision_ref = payload.revision_ref.strip().upper()
    if revision_ref != "CURRENT" and not re.fullmatch(r"V[1-9]\d*", revision_ref):
        raise HTTPException(400, "Revision must be CURRENT or a saved version such as v3")
    if not any((
        payload.confusion_rating is not None,
        payload.engagement_rating is not None,
        payload.tension_rating is not None,
        payload.empathy_rating is not None,
        payload.response.strip(),
    )):
        raise HTTPException(400, "Add at least one rating or written response")
    conn = get_db()
    scene = conn.execute("""
        SELECT s.id, ch.parent_id AS book_id
        FROM binder_nodes s JOIN binder_nodes ch ON ch.id = s.parent_id
        WHERE s.id = ? AND s.node_type = 'SCENE' AND ch.node_type = 'CHAPTER'
    """, (payload.scene_id,)).fetchone()
    if not scene:
        conn.close()
        raise HTTPException(404, "Scene not found")
    if revision_ref != "CURRENT":
        version_num = int(revision_ref[1:])
        if not conn.execute(
            "SELECT 1 FROM node_revisions WHERE node_id = ? AND version_num = ?",
            (payload.scene_id, version_num),
        ).fetchone():
            conn.close()
            raise HTTPException(400, "That saved scene revision does not exist")
    feedback_id = f"reader_{uuid.uuid4().hex}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO reader_feedback
            (id, book_id, scene_id, revision_ref, reader_label, confusion_rating, engagement_rating,
             tension_rating, empathy_rating, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_id, scene["book_id"], payload.scene_id, revision_ref, payload.reader_label.strip(),
            payload.confusion_rating, payload.engagement_rating, payload.tension_rating,
            payload.empathy_rating, payload.response.strip(), now,
        ))
    conn.close()
    return {"id": feedback_id, "status": "saved"}


@router.delete("/api/reader-feedback/{feedback_id}")
def delete_reader_feedback(feedback_id: str):
    conn = get_db()
    with conn:
        result = conn.execute("DELETE FROM reader_feedback WHERE id = ?", (feedback_id,))
    conn.close()
    if not result.rowcount:
        raise HTTPException(404, "Reader feedback entry not found")
    return {"status": "deleted"}

