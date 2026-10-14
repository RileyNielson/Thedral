import logging
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.telemetry import calculate_text_telemetry
from backend.reader_story import analyze_reader_story
from backend.wiktionary_lexicon import download_wiktionary_database, get_lexicon_status

router = APIRouter(tags=["Binder"])

_lexicon_job = {"state": "idle", "error": ""}


def _run_lexicon_download():
    try:
        download_wiktionary_database()
        _lexicon_job.update(state="done", error="")
    except Exception as exc:
        _lexicon_job.update(state="failed", error=str(exc))


@router.get("/api/lexicon/status")
def lexicon_status():
    return {**get_lexicon_status(), "download": dict(_lexicon_job)}


@router.post("/api/lexicon/download")
def lexicon_download():
    """Start the one-time Wiktionary download in the background; poll /api/lexicon/status."""
    if get_lexicon_status()["available"]:
        return {"state": "done", "error": ""}
    if _lexicon_job["state"] != "running":
        _lexicon_job.update(state="running", error="")
        threading.Thread(target=_run_lexicon_download, daemon=True).start()
    return dict(_lexicon_job)

class ReaderExperienceAnalyticsRequest(BaseModel):
    scene_id: str
    content: str = ""


def _reader_story_scenes(book_id: str) -> list[dict]:
    conn = get_db()
    book = conn.execute(
        "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'BOOK' AND COALESCE(is_archived, 0) = 0",
        (book_id,),
    ).fetchone()
    if not book:
        conn.close()
        raise HTTPException(404, "Manuscript not found")

    rows = conn.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id, parent_id, node_type, title, sort_order, content
            FROM binder_nodes WHERE id = ?
            UNION ALL
            SELECT child.id, child.parent_id, child.node_type, child.title, child.sort_order, child.content
            FROM binder_nodes child
            JOIN descendants parent ON child.parent_id = parent.id
            WHERE COALESCE(child.is_archived, 0) = 0
        )
        SELECT id, parent_id, node_type, title, sort_order, content FROM descendants
    """, (book_id,)).fetchall()
    conn.close()

    nodes = {row["id"]: dict(row) for row in rows}
    children = {}
    for node in nodes.values():
        children.setdefault(node["parent_id"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (node["sort_order"] or 0, node["title"], node["id"]))

    scenes = []

    def visit(parent_id: str):
        for node in children.get(parent_id, []):
            if node["node_type"] == "SCENE":
                scenes.append({
                    "scene_id": node["id"],
                    "title": node["title"],
                    "content": node["content"] or "",
                })
            visit(node["id"])

    visit(book_id)
    return scenes


@router.post("/api/analytics/reader-experience/{book_id}")
def get_reader_experience_analytics(book_id: str, payload: ReaderExperienceAnalyticsRequest):
    conn = get_db()
    book = conn.execute(
        "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'BOOK' AND COALESCE(is_archived, 0) = 0",
        (book_id,),
    ).fetchone()
    if not book:
        conn.close()
        raise HTTPException(404, "Manuscript not found")

    rows = conn.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id, parent_id, node_type, title, sort_order, content
            FROM binder_nodes
            WHERE id = ?
            UNION ALL
            SELECT child.id, child.parent_id, child.node_type, child.title, child.sort_order, child.content
            FROM binder_nodes child
            JOIN descendants parent ON child.parent_id = parent.id
            WHERE COALESCE(child.is_archived, 0) = 0
        )
        SELECT id, parent_id, node_type, title, sort_order, content
        FROM descendants
    """, (book_id,)).fetchall()
    conn.close()

    children = {}
    nodes = {row["id"]: dict(row) for row in rows}
    for node in nodes.values():
        children.setdefault(node["parent_id"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (node["sort_order"] or 0, node["title"], node["id"]))

    scenes = []

    def visit(parent_id: str, chapter_title: str = ""):
        for node in children.get(parent_id, []):
            current_chapter = node["title"] if node["node_type"] == "CHAPTER" else chapter_title
            if node["node_type"] == "SCENE":
                content = payload.content if node["id"] == payload.scene_id else node["content"] or ""
                scenes.append({
                    "scene_id": node["id"],
                    "title": node["title"],
                    "chapter_title": chapter_title,
                    "telemetry": calculate_text_telemetry(content),
                })
            visit(node["id"], current_chapter)

    visit(book_id)
    selected_index = next(
        (index for index, scene in enumerate(scenes) if scene["scene_id"] == payload.scene_id),
        None,
    )
    if selected_index is None:
        raise HTTPException(404, "Scene not found in this manuscript")

    return {
        "book_id": book_id,
        "scene_id": payload.scene_id,
        "scenes": scenes,
        "selected_index": selected_index,
    }


@router.post("/api/analytics/reader-story/{book_id}")
def get_reader_story_analytics(book_id: str, payload: ReaderExperienceAnalyticsRequest):
    scenes = _reader_story_scenes(book_id)
    # An unknown id (a chapter, or a scene moved or archived mid-edit) gets the analyzer's empty result, not an error.
    return analyze_reader_story(scenes, payload.scene_id, payload.content)


@router.get("/api/analytics/reader-story/{book_id}/all")
def get_all_reader_story_analytics(book_id: str):
    scenes = _reader_story_scenes(book_id)
    analyses = []
    failed = 0
    for scene in scenes:
        try:
            analysis = analyze_reader_story(scenes, scene["scene_id"], scene["content"])
        except Exception:
            # One unusual scene must not block the rest; the live panel retries it when opened.
            logging.getLogger(__name__).exception("Reader analysis failed for scene %s", scene["scene_id"])
            failed += 1
            continue
        analyses.append({
            "scene_id": scene["scene_id"],
            "title": scene["title"],
            "content": scene["content"],
            "analysis": analysis,
        })
    return {
        "book_id": book_id,
        "scene_count": len(scenes),
        "failed_scenes": failed,
        "analyses": analyses,
        "method": "Transparent text-pattern rules; no generative AI is used for these insights.",
    }
