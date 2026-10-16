import json
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.story_shape import STRAND_KEYS, analyze_text, build_story_shape

router = APIRouter(tags=["Story Shape"])


class TargetPayload(BaseModel):
    book_id: str
    targets: dict[str, float] = Field(default_factory=dict)


def _book_units(conn, book_id: str) -> list[dict]:
    book = conn.execute(
        "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'BOOK' AND COALESCE(is_archived, 0) = 0",
        (book_id,),
    ).fetchone()
    if not book:
        raise HTTPException(404, "Manuscript not found")
    rows = conn.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id, parent_id, node_type, title, sort_order, content FROM binder_nodes WHERE id = ?
            UNION ALL
            SELECT c.id, c.parent_id, c.node_type, c.title, c.sort_order, c.content
            FROM binder_nodes c JOIN descendants p ON c.parent_id = p.id
            WHERE COALESCE(c.is_archived, 0) = 0
        )
        SELECT id, parent_id, node_type, title, sort_order, content FROM descendants
    """, (book_id,)).fetchall()
    nodes = {r["id"]: dict(r) for r in rows}
    children: dict = {}
    for node in nodes.values():
        children.setdefault(node["parent_id"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda n: (n["sort_order"] or 0, n["title"], n["id"]))

    units = []

    def visit(parent_id, chapter):
        for node in children.get(parent_id, []):
            if node["node_type"] == "SCENE":
                group = chapter or {"id": node["id"], "title": node["title"]}
                units.append({
                    "scene_id": node["id"], "title": node["title"],
                    "chapter_id": group["id"], "chapter_title": group["title"],
                    "content": node["content"] or "",
                })
            elif node["node_type"] == "CHAPTER" and chapter is None:
                visit(node["id"], node)
            else:
                visit(node["id"], chapter)

    visit(book_id, None)
    return units


def _lore_terms(conn) -> list[str]:
    terms = []
    for row in conn.execute("SELECT name FROM canonical_entities").fetchall():
        terms.append(row["name"])
    try:
        for row in conn.execute("SELECT term FROM style_sheet").fetchall():
            terms.append(row["term"])
    except Exception:
        pass
    return terms


@router.get("/api/analytics/story-shape/{book_id}")
def get_story_shape(book_id: str):
    conn = get_db()
    try:
        units = _book_units(conn, book_id)
        lore = _lore_terms(conn)
        targets = {
            row["node_id"]: json.loads(row["targets"] or "{}")
            for row in conn.execute("SELECT node_id, targets FROM story_shape_targets WHERE book_id = ?", (book_id,)).fetchall()
        }
    finally:
        conn.close()
    shape = build_story_shape(units, lore)
    shape["book_id"] = book_id
    shape["targets"] = targets
    return shape


@router.get("/api/analytics/story-shape/{book_id}/evidence/{scene_id}")
def get_story_shape_evidence(book_id: str, scene_id: str, strand: str):
    if strand not in STRAND_KEYS and strand != "lore":
        raise HTTPException(400, "Unknown strand")
    conn = get_db()
    try:
        units = _book_units(conn, book_id)
        lore = _lore_terms(conn)
    finally:
        conn.close()
    unit = next((u for u in units if u["scene_id"] == scene_id), None)
    if not unit:
        raise HTTPException(404, "Scene not found in this manuscript")
    result = analyze_text(unit["content"], lore)
    return {"scene_id": scene_id, "strand": strand, "evidence": result["evidence"].get(strand, [])}


@router.put("/api/analytics/story-shape/targets/{node_id}")
def set_story_shape_target(node_id: str, payload: TargetPayload):
    clean = {k: max(0.0, min(100.0, float(v))) for k, v in payload.targets.items() if k in STRAND_KEYS or k == "lore"}
    conn = get_db()
    try:
        node = conn.execute("SELECT id FROM binder_nodes WHERE id = ?", (node_id,)).fetchone()
        if not node:
            raise HTTPException(404, "Node not found")
        if clean:
            conn.execute(
                "INSERT INTO story_shape_targets (node_id, book_id, targets, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(node_id) DO UPDATE SET book_id = excluded.book_id, targets = excluded.targets, updated_at = excluded.updated_at",
                (node_id, payload.book_id, json.dumps(clean), time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
        else:
            conn.execute("DELETE FROM story_shape_targets WHERE node_id = ?", (node_id,))
        conn.commit()
    finally:
        conn.close()
    return {"node_id": node_id, "targets": clean}
