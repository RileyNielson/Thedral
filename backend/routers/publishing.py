import os
import hashlib
import json
import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from backend.database import get_db
from backend.text_utils import html_to_text
from backend.publishing import generate_query_synopsis
from backend.compiler import compile_book_to_docx
from backend.config import ENABLE_AI, EXPORTS_DIR

router = APIRouter(tags=["Publishing"])

class SynopsisRequest(BaseModel):
    book_id: str | None = None


class ExportRequest(BaseModel):
    book_id: str
    author_name: str = ""
    subtitle: str = ""
    dedication: str = ""
    chapter_ids: list[str] | None = None


class PublishingProfileRequest(BaseModel):
    author_name: str = ""
    subtitle: str = ""
    dedication: str = ""
    genre: str = ""
    logline: str = ""
    author_bio: str = ""
    query_text: str = ""
    sample_scene_ids: list[str] = Field(default_factory=list)
    included_chapter_ids: list[str] | None = None


def _book_or_404(conn, book_id: str):
    book = conn.execute(
        "SELECT id, title FROM binder_nodes WHERE id = ? AND node_type = 'BOOK'",
        (book_id,),
    ).fetchone()
    if not book:
        conn.close()
        raise HTTPException(404, "Manuscript not found")
    return book


@router.get("/api/publishing/review/{book_id}")
def get_manuscript_review(book_id: str):
    conn = get_db()
    _book_or_404(conn, book_id)
    rows = conn.execute("""
        SELECT s.id, s.title, s.synopsis, s.word_count, s.status, ch.title AS chapter_title,
               SUM(CASE WHEN ec.status = 'OPEN' THEN 1 ELSE 0 END) AS open_critiques
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        LEFT JOIN editorial_critiques ec ON ec.scene_id = s.id
        WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
        GROUP BY s.id
        ORDER BY ch.sort_order, s.sort_order
    """, (book_id,)).fetchall()
    scenes = [dict(row) for row in rows]
    anomalies = []
    if scenes:
        from backend.astrolabe import build_astrolabe_manifest
        anomalies = build_astrolabe_manifest(conn, book_id=book_id).get("anomalies", [])
    conn.close()
    return {
        "scenes": scenes,
        "total_scenes": len(scenes),
        "total_words": sum(int(scene["word_count"] or 0) for scene in scenes),
        "empty_scenes": sum(not int(scene["word_count"] or 0) for scene in scenes),
        "missing_synopses": sum(not (scene["synopsis"] or "").strip() for scene in scenes),
        "open_critiques": sum(int(scene["open_critiques"] or 0) for scene in scenes),
        "anomalies": anomalies,
    }


@router.get("/api/publishing/profile/{book_id}")
def get_publishing_profile(book_id: str):
    conn = get_db()
    _book_or_404(conn, book_id)
    row = conn.execute("SELECT * FROM publishing_profiles WHERE book_id = ?", (book_id,)).fetchone()
    conn.close()
    if not row:
        return {"author_name": "", "subtitle": "", "dedication": "", "genre": "", "logline": "", "author_bio": "", "query_text": "", "sample_scene_ids": [], "included_chapter_ids": None}
    profile = dict(row)
    profile["sample_scene_ids"] = json.loads(profile.pop("sample_scene_ids") or "[]")
    saved_chapter_ids = profile.pop("included_chapter_ids")
    profile["included_chapter_ids"] = json.loads(saved_chapter_ids) if saved_chapter_ids is not None else None
    profile.pop("book_id", None)
    profile.pop("updated_at", None)
    return profile


@router.put("/api/publishing/profile/{book_id}")
def save_publishing_profile(book_id: str, payload: PublishingProfileRequest):
    conn = get_db()
    _book_or_404(conn, book_id)
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    data = payload.model_dump()
    with conn:
        conn.execute("""
            INSERT INTO publishing_profiles
            (book_id, author_name, subtitle, dedication, genre, logline, author_bio, query_text, sample_scene_ids, included_chapter_ids, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
                author_name=excluded.author_name, subtitle=excluded.subtitle, dedication=excluded.dedication,
                genre=excluded.genre, logline=excluded.logline, author_bio=excluded.author_bio,
                query_text=excluded.query_text, sample_scene_ids=excluded.sample_scene_ids,
                included_chapter_ids=excluded.included_chapter_ids, updated_at=excluded.updated_at
        """, (
            book_id, data["author_name"], data["subtitle"], data["dedication"], data["genre"],
            data["logline"], data["author_bio"], data["query_text"],
            json.dumps(data["sample_scene_ids"]),
            json.dumps(data["included_chapter_ids"]) if data["included_chapter_ids"] is not None else None,
            now,
        ))
    conn.close()
    return {"status": "saved"}


@router.get("/api/publishing/exports/{book_id}")
def get_export_history(book_id: str):
    conn = get_db()
    _book_or_404(conn, book_id)
    rows = conn.execute("""
        SELECT id, book_title, filename, included_chapter_ids, word_count, content_hash, created_at
        FROM export_history WHERE book_id = ? ORDER BY created_at DESC LIMIT 20
    """, (book_id,)).fetchall()
    conn.close()
    return [
        {**dict(row), "included_chapter_ids": json.loads(row["included_chapter_ids"])}
        for row in rows
    ]


@router.get("/api/publishing/exports/{export_id}/download")
def download_export(export_id: str):
    conn = get_db()
    row = conn.execute("SELECT filename, file_path FROM export_history WHERE id = ?", (export_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Export file is no longer available")
    export_root = os.path.realpath(EXPORTS_DIR)
    file_path = os.path.realpath(row["file_path"])
    if os.path.commonpath((export_root, file_path)) != export_root or not os.path.isfile(file_path):
        raise HTTPException(404, "Export file is no longer available")
    return FileResponse(file_path, filename=row["filename"])


@router.post("/api/publishing/export")
def create_export(payload: ExportRequest):
    conn = get_db()
    book = _book_or_404(conn, payload.book_id)
    chapters = conn.execute(
        "SELECT id FROM binder_nodes WHERE parent_id = ? AND node_type = 'CHAPTER' ORDER BY sort_order",
        (payload.book_id,),
    ).fetchall()
    available_ids = [row["id"] for row in chapters]
    included_ids = list(dict.fromkeys(payload.chapter_ids)) if payload.chapter_ids is not None else available_ids
    if not included_ids or any(chapter_id not in available_ids for chapter_id in included_ids):
        conn.close()
        raise HTTPException(400, "Choose one or more chapters from this manuscript.")
    scene_rows = conn.execute("""
        SELECT s.content FROM binder_nodes s JOIN binder_nodes ch ON s.parent_id = ch.id
        WHERE ch.parent_id = ? AND ch.id IN ({}) AND s.node_type = 'SCENE'
    """.format(",".join("?" for _ in included_ids)), (payload.book_id, *included_ids)).fetchall()
    word_count = sum(len(html_to_text(row["content"] or "").split()) for row in scene_rows)
    conn.close()

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    safe_title = "".join(ch for ch in book["title"] if ch.isalnum() or ch in "-_ ").strip().replace(" ", "_") or "Manuscript"
    filename = f"{safe_title}_{time.strftime('%Y%m%d_%H%M%S')}.docx"
    try:
        file_path = compile_book_to_docx(
            payload.book_id, output_filename=f"export_{uuid.uuid4().hex}.docx",
            author_name=payload.author_name, subtitle=payload.subtitle,
            dedication=payload.dedication, chapter_ids=included_ids,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    with open(file_path, "rb") as exported:
        content_hash = hashlib.sha256(exported.read()).hexdigest()
    export_id = f"export_{uuid.uuid4().hex}"
    conn = get_db()
    with conn:
        conn.execute("""
            INSERT INTO export_history
            (id, book_id, book_title, filename, file_path, included_chapter_ids, word_count, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (export_id, payload.book_id, book["title"], filename, file_path, json.dumps(included_ids), word_count, content_hash, now))
    conn.close()
    return FileResponse(file_path, filename=filename, headers={"X-Thedral-Export-Id": export_id, "X-Thedral-Content-SHA256": content_hash})


@router.post("/api/publishing/synopsis")
def get_synopsis(payload: SynopsisRequest):
    if not ENABLE_AI:
        return {"synopsis": "Query Synopsis requires local AI (Lite mode: AI is off).", "ai_generated": False, "engine": "deterministic"}
    text = generate_query_synopsis(payload.book_id)
    ok = not text.startswith(("Could not generate", "Not enough scenes"))
    return {"synopsis": text, "ai_generated": ok, "engine": "local-ai" if ok else "deterministic"}

