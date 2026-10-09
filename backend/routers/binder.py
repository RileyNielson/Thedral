import re
import time
import json
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.hashing import find_severed_threads
from backend.telemetry import calculate_text_telemetry
from backend.astrolabe import build_astrolabe_manifest
from backend.config import STUDIO_MODEL, ENABLE_AI

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

class AutoTitleRequest(BaseModel):
    book_id: str | None = None

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
    
    if node.get("card_data"):
        try:
            node["card"] = json.loads(node["card_data"]) if isinstance(node["card_data"], str) else node["card_data"]
        except Exception:
            node["card"] = {}
    else:
        node["card"] = {}

    conn.close()
    return node

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
        wc = len(data["content"].split()) if data["content"] else 0
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

@router.get("/api/vault/books")
def get_vault_books():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, synopsis, status, word_count, is_archived, updated_at 
        FROM binder_nodes 
        WHERE node_type = 'BOOK' 
        ORDER BY updated_at DESC
    """)
    books = [dict(r) for r in c.fetchall()]
    for b in books:
        c.execute("SELECT COUNT(*) FROM binder_nodes WHERE parent_id = ? AND node_type = 'CHAPTER'", (b["id"],))
        b["chapter_count"] = c.fetchone()[0]
        c.execute("""
            SELECT SUM(s.word_count) 
            FROM binder_nodes s 
            JOIN binder_nodes ch ON s.parent_id = ch.id 
            WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
        """, (b["id"],))
        b["total_words"] = c.fetchone()[0] or 0
    conn.close()
    return books

@router.post("/api/vault/{book_id}/toggle")
def toggle_book_archive(book_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT is_archived FROM binder_nodes WHERE id = ?", (book_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Book not found")
        
    new_status = 0 if row["is_archived"] == 1 else 1
    with conn:
        conn.execute("""
            UPDATE binder_nodes 
            SET is_archived = ? 
            WHERE id = ? 
               OR parent_id = ? 
               OR parent_id IN (SELECT id FROM binder_nodes WHERE parent_id = ?)
        """, (new_status, book_id, book_id, book_id))
    conn.close()
    return {"status": "success", "is_archived": new_status}

@router.post("/api/binder/auto-title-scenes")
async def auto_title_scenes(payload: AutoTitleRequest):
    if not ENABLE_AI:
        return {"status": "offline_mode", "updated_count": 0}

    try:
        import ollama
    except ImportError:
        return {"status": "offline_mode", "updated_count": 0}

    conn = get_db()
    c = conn.cursor()
    target_b = payload.book_id
    if not target_b:
        c.execute("SELECT id FROM binder_nodes WHERE node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0) LIMIT 1")
        r = c.fetchone()
        if r: target_b = r["id"]

    c.execute("""
        SELECT s.id, s.title, s.content, ch.title as ch_title 
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
        ORDER BY ch.sort_order ASC, s.sort_order ASC
    """, (target_b,))
    scenes = c.fetchall()

    updated = 0
    prompt_tpl = "Read this scene opening and give it a punchy 2-to-4 word cinematic title. OUTPUT ONLY THE TITLE - NO QUOTES.\n\nScene Opening:\n"

    for sc in scenes:
        text = (sc["content"] or "").strip()
        if len(text) < 30: continue
        if not re.match(r"^Scene\s+\d+$", sc["title"], re.I): continue

        try:
            resp = await asyncio.to_thread(
                ollama.chat,
                model=STUDIO_MODEL,
                messages=[{"role": "user", "content": prompt_tpl + text[:400]}],
                options={"temperature": 0.3}
            )
            raw_title = resp["message"]["content"].replace('"', "").replace("'", "").strip(" .,")
            clean_title = re.sub(r'^(Title|Scene):\s*', '', raw_title, flags=re.I).strip()
            if 3 < len(clean_title) < 40:
                with conn:
                    conn.execute("UPDATE binder_nodes SET title = ? WHERE id = ?", (clean_title.title(), sc["id"]))
                updated += 1
        except Exception:
            continue

    conn.close()
    return {"status": "success", "updated_count": updated}

@router.post("/api/binder/triage-scene/{scene_id}")
async def master_triage_scene(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT parent_id, sort_order, content FROM binder_nodes WHERE id = ?", (scene_id,))
    scene = c.fetchone()
    
    if not scene or not scene["content"]:
        conn.close()
        return {"status": "empty"}

    text = scene["content"]

    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'--+', '—', text)
    text = re.sub(r'\.\.\.', '…', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    blocks = re.split(r'\n\n(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|-{3,})\n\n', text)
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    parent_id = scene["parent_id"]
    base_sort = float(scene["sort_order"])
    
    first_block = blocks[0].strip()
    new_scene_ids = []

    with conn:
        conn.execute("UPDATE binder_nodes SET content = ?, word_count = ? WHERE id = ?", 
                    (first_block, len(first_block.split()), scene_id))

        for idx, block in enumerate(blocks[1:], 1):
            clean_block = block.strip()
            if not clean_block: continue
            
            new_id = f"scene_{uuid.uuid4().hex[:8]}"
            new_sort = base_sort + (idx * 1.0)
            wc = len(clean_block.split())
            
            conn.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, content, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'SCENE', ?, ?, ?, 'DRAFT', ?, 0, '', '{}', ?, ?)
            """, (new_id, parent_id, f"Sliced Scene {idx}", new_sort, clean_block, wc, now, now))
            new_scene_ids.append(new_id)

    tk_count = len(re.findall(r'\[TK[^\]]*\]', first_block, re.IGNORECASE))

    if new_scene_ids:
        c.execute("SELECT id FROM binder_nodes WHERE node_type = 'BOOK' LIMIT 1")
        b_row = c.fetchone()
        if b_row:
            asyncio.create_task(auto_title_scenes(AutoTitleRequest(book_id=b_row["id"])))

    conn.close()

    return {
        "status": "success", 
        "formatted_text": first_block,
        "new_scenes": len(new_scene_ids),
        "tk_count": tk_count
    }
