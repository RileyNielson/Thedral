import re
import html
import time
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.text_utils import html_to_formatted_paragraphs, html_to_text
from backend.config import STUDIO_MODEL, ENABLE_AI

router = APIRouter(tags=["Binder"])


class AutoTitleRequest(BaseModel):
    book_id: str | None = None

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
        return {"status": "offline_mode", "updated_count": 0, "ai_generated": False}

    try:
        import ollama
    except ImportError:
        return {"status": "offline_mode", "updated_count": 0, "ai_generated": False}

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
        text = html_to_text(sc["content"] or "").strip()
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
    return {"status": "success", "updated_count": updated, "ai_generated": True}

@router.post("/api/binder/triage-scene/{scene_id}")
async def master_triage_scene(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT parent_id, sort_order, content FROM binder_nodes WHERE id = ?", (scene_id,))
    scene = c.fetchone()
    
    if not scene or not scene["content"]:
        conn.close()
        return {"status": "empty"}

    paragraphs = html_to_formatted_paragraphs(scene["content"])
    blocks = [[]]
    divider_pattern = re.compile(r"^(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|-{3,})$")
    for paragraph in paragraphs:
        plain_paragraph = "".join(text for text, _, _ in paragraph).strip()
        if divider_pattern.fullmatch(plain_paragraph):
            if blocks[-1]:
                blocks.append([])
            continue
        if plain_paragraph:
            blocks[-1].append(paragraph)
    blocks = [block for block in blocks if block]

    def render_block(block):
        rendered_paragraphs = []
        for paragraph in block:
            runs = []
            for run_text, bold, italic in paragraph:
                clean = re.sub(r'\.\.\.', '…', re.sub(r'--+', '—', run_text))
                rendered = html.escape(clean, quote=False)
                if bold and italic:
                    rendered = f"<strong><em>{rendered}</em></strong>"
                elif bold:
                    rendered = f"<strong>{rendered}</strong>"
                elif italic:
                    rendered = f"<em>{rendered}</em>"
                runs.append(rendered)
            rendered_paragraphs.append(f"<p>{''.join(runs)}</p>")
        return "".join(rendered_paragraphs)

    if not blocks:
        conn.close()
        return {"status": "empty"}
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    parent_id = scene["parent_id"]
    base_sort = float(scene["sort_order"])
    
    first_block = render_block(blocks[0])
    new_scene_ids = []

    with conn:
        conn.execute("UPDATE binder_nodes SET content = ?, word_count = ? WHERE id = ?", 
                    (first_block, len(html_to_text(first_block).split()), scene_id))

        for idx, block in enumerate(blocks[1:], 1):
            clean_block = render_block(block)
            if not clean_block:
                continue

            new_id = f"scene_{uuid.uuid4().hex[:8]}"
            new_sort = base_sort + (idx * 1.0)
            wc = len(html_to_text(clean_block).split())
            
            conn.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, content, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'SCENE', ?, ?, ?, 'DRAFT', ?, 0, '', '{}', ?, ?)
            """, (new_id, parent_id, f"Sliced Scene {idx}", new_sort, clean_block, wc, now, now))
            new_scene_ids.append(new_id)

    tk_count = len(re.findall(r'\[TK[^\]]*\]', html_to_text(first_block), re.IGNORECASE))

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

