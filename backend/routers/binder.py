import time
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.hashing import find_severed_threads
from backend.telemetry import calculate_text_telemetry
from backend.text_utils import html_to_text
from backend.astrolabe import build_astrolabe_manifest

router = APIRouter(tags=["Binder"])

class NodeUpdate(BaseModel):
    title: str | None = None
    synopsis: str | None = None
    content: str | None = None
    epigraph: str | None = None
    notes: str | None = None
    status: str | None = None
    card_data: str | dict | None = None

class NodeCreate(BaseModel):
    parent_id: str | None = None
    node_type: str
    title: str

@router.put("/api/scenes/{node_id}")
@router.put("/api/node/{node_id}")
def update_node(node_id: str, payload: NodeUpdate):
    conn = get_db()
    fields, values = [], []
    data = payload.model_dump(exclude_unset=True)

    for k, v in data.items():
        if k == "card_data" and isinstance(v, dict):
            fields.append("card_data = ?")
            values.append(json.dumps(v))
        elif k != "card_data":
            fields.append(f"{k} = ?")
            values.append(v)
        else:
            fields.append("card_data = ?")
            values.append(v or "{}")

    if "content" in data and data["content"] is not None:
        wc = len(html_to_text(data["content"]).split()) if data["content"] else 0
        fields.append("word_count = ?")
        values.append(wc)

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    fields.append("updated_at = ?")
    values.append(now)
    values.append(node_id)

    with conn:
        conn.execute(f"UPDATE binder_nodes SET {', '.join(fields)} WHERE id = ?", values)
        if "content" in data and data["content"]:
            c = conn.cursor()
            c.execute("SELECT MAX(version_num) FROM node_revisions WHERE node_id = ?", (node_id,))
            max_v = c.fetchone()[0] or 0
            c.execute("""
                INSERT INTO node_revisions (node_id, version_num, content, change_summary, created_at)
                VALUES (?, ?, ?, 'Auto-save snapshot', ?)
            """, (node_id, max_v + 1, data["content"], now))

    conn.close()
    return {"status": "saved"}

class RestoreRevisionRequest(BaseModel):
    version_num: int

@router.post("/api/node/{node_id}/restore")
@router.post("/api/scenes/{node_id}/restore")
def restore_node_revision(node_id: str, payload: RestoreRevisionRequest):
    conn = get_db()
    c = conn.cursor()
    row = c.execute(
        "SELECT content FROM node_revisions WHERE node_id = ? AND version_num = ? ORDER BY id DESC LIMIT 1",
        (node_id, payload.version_num),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Revision not found")

    restored_content = row["content"]
    current = c.execute("SELECT content FROM binder_nodes WHERE id = ?", (node_id,)).fetchone()
    if not current:
        conn.close()
        raise HTTPException(404, "Scene not found")
    current_content = current["content"] or ""
    word_count = len(html_to_text(restored_content).split()) if restored_content else 0
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        max_v = c.execute("SELECT MAX(version_num) FROM node_revisions WHERE node_id = ?", (node_id,)).fetchone()[0] or 0
        if current_content != (restored_content or ""):
            max_v += 1
            c.execute(
                "INSERT INTO node_revisions (node_id, version_num, content, change_summary, created_at) VALUES (?, ?, ?, 'Pre-restore snapshot', ?)",
                (node_id, max_v, current_content, now),
            )
        c.execute(
            "UPDATE binder_nodes SET content = ?, word_count = ?, updated_at = ? WHERE id = ?",
            (restored_content, word_count, now, node_id),
        )
        c.execute(
            "INSERT INTO node_revisions (node_id, version_num, content, change_summary, created_at) VALUES (?, ?, ?, ?, ?)",
            (node_id, max_v + 1, restored_content, f"Restored from revision v{payload.version_num}", now),
        )
    conn.close()
    return {"status": "restored", "version_num": payload.version_num, "word_count": word_count}

@router.get("/api/node/{node_id}/revisions")
@router.get("/api/scenes/{node_id}/revisions")
def get_node_revisions(node_id: str):
    conn = get_db()
    rows = [
        dict(r) for r in conn.execute(
            "SELECT id, version_num, content, change_summary, created_at FROM node_revisions WHERE node_id = ? ORDER BY version_num DESC LIMIT 10",
            (node_id,),
        ).fetchall()
    ]
    conn.close()
    return rows

@router.get("/api/scenes/{node_id}/telemetry")
@router.get("/api/node/{node_id}/telemetry")
def get_node_telemetry_endpoint(node_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT content FROM binder_nodes WHERE id = ?", (node_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Node not found")
    return calculate_text_telemetry(row["content"] or "")

@router.get("/api/scenes/{node_id}/lens")
@router.get("/api/node/{node_id}/lens")
def get_node_lens_endpoint(node_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT parent_id FROM binder_nodes WHERE id = ?", (node_id,))
    row = c.fetchone()
    if not row or not row["parent_id"]:
        conn.close()
        return {"data": [], "layout": {}, "anomalies": []}
    manifest = build_astrolabe_manifest(conn, chapter_id=row["parent_id"], focus_scene_id=node_id)
    conn.close()
    return manifest

@router.post("/api/node")
def create_node(payload: NodeCreate):
    conn = get_db()
    node_id = f"{payload.node_type.lower()}_{uuid.uuid4().hex[:8]}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, is_archived, card_data, created_at, updated_at)
            VALUES (?, ?, 'default', ?, ?, 999.0, 0, '{}', ?, ?)
        """, (node_id, payload.parent_id, payload.node_type, payload.title, now, now))
    conn.close()
    return {"id": node_id, "title": payload.title}

@router.delete("/api/node/{node_id}")
def delete_node(node_id: str):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM binder_nodes WHERE id = ?", (node_id,))
        conn.execute("DELETE FROM canonical_worldlines WHERE scene_id = ?", (node_id,))
        conn.execute("DELETE FROM reader_disclosures WHERE scene_id = ?", (node_id,))
        conn.execute("DELETE FROM staged_proposals WHERE scene_id = ?", (node_id,))
    conn.close()
    return {"status": "deleted"}


@router.get("/api/binder")
@router.get("/api/tree")
def get_binder_tree():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, parent_id, node_type, title, sort_order, synopsis, word_count, status, epigraph, card_data 
        FROM binder_nodes 
        WHERE (is_archived IS NULL OR is_archived = 0) 
        ORDER BY sort_order ASC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    lookup = {r["id"]: {**r, "children": []} for r in rows}
    root_nodes = []
    for r in rows:
        node = lookup[r["id"]]
        pid = r["parent_id"]
        if pid and pid in lookup:
            lookup[pid]["children"].append(node)
        else:
            root_nodes.append(node)
    return root_nodes

@router.get("/api/scenes/{node_id}")
@router.get("/api/node/{node_id}")
def get_node(node_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM binder_nodes WHERE id = ?", (node_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Node not found")
        
    node = dict(row)
    node["telemetry"] = calculate_text_telemetry(node["content"] or "")
    node["severed_threads"] = find_severed_threads(conn, node_id, node["content"] or "")
    node["revisions"] = [
        dict(r) for r in c.execute(
            "SELECT id, version_num, content, change_summary, created_at FROM node_revisions WHERE node_id = ? ORDER BY version_num DESC LIMIT 10",
            (node_id,),
        ).fetchall()
    ]
    
    if node.get("card_data"):
        try:
            node["card"] = json.loads(node["card_data"]) if isinstance(node["card_data"], str) else node["card_data"]
        except Exception:
            node["card"] = {}
    else:
        node["card"] = {}

    conn.close()
    return node


from backend.routers.analytics import (  # noqa: E402,F401
    ReaderExperienceAnalyticsRequest,
    _reader_story_scenes,
    get_all_reader_story_analytics,
    get_reader_experience_analytics,
    get_reader_story_analytics,
)
from backend.routers.binder_tools import (  # noqa: E402,F401
    AutoTitleRequest,
    auto_title_scenes,
    get_vault_books,
    master_triage_scene,
    toggle_book_archive,
)
