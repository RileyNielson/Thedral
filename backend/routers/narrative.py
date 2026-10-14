import re
import json
import time
import uuid
import asyncio
import hashlib
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.database import get_db
from backend.text_utils import html_to_text
from backend.astrolabe import build_astrolabe_manifest
from backend.guardrails import sanitize_entity_type
from backend.socratic import extract_ghost_proposals, discover_synaptic_resonance
from backend.config import ENABLE_AI
from backend.entity_names import entity_name_forms
from backend.ai_helper import ai_meta, known_cast_lines, deterministic_brief

router = APIRouter(tags=["Narrative 3D"])

class ConnectionCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: str
    description: str = ""

class PromiseCreate(BaseModel):
    book_id: str | None = None
    scene_id: str | None = None
    promise_desc: str
    target_volume: int = 2
    target_tick: float = 5.0
    target_location: str = ""

@router.get("/api/narrative/astrolabe")
def get_astrolabe(
    book_id: str | None = None, 
    projection: str = "ALL", 
    time_mode: str = "chronological",
    chapter_id: str | None = None,
    focus_id: str | None = None
):
    """Returns the complete 8-layer Plotly 3D spacetime manifold specification."""
    conn = get_db()
    manifest = build_astrolabe_manifest(
        conn, 
        book_id=book_id, 
        projection_mode=projection, 
        time_mode=time_mode,
        chapter_id=chapter_id,
        focus_scene_id=focus_id
    )
    conn.close()
    return manifest


@router.get("/api/narrative/proposals")
def get_survey_proposals(book_id: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT p.proposal_id, p.scene_id, p.detected_entity_name, p.entity_type,
               p.proposed_delta, p.confidence, p.epistemic_tier, p.attested_by,
               p.source_span_text, p.status, s.title AS scene_title, ch.title AS chapter_title
        FROM staged_proposals p
        JOIN binder_nodes s ON p.scene_id = s.id AND s.node_type = 'SCENE'
        JOIN binder_nodes ch ON s.parent_id = ch.id AND ch.node_type = 'CHAPTER'
        WHERE ch.parent_id = ? AND p.status = 'PENDING'
        ORDER BY ch.sort_order, s.sort_order, p.proposal_id
    """, (book_id,)).fetchall()
    conn.close()
    proposals = [dict(row) for row in rows]
    for proposal in proposals:
        proposal["proposed_delta"] = json.loads(proposal["proposed_delta"] or "{}")
    return proposals


@router.post("/api/narrative/proposals/{proposal_id}/approve")
def approve_survey_proposal(proposal_id: str):
    conn = get_db()
    proposal = conn.execute("""
        SELECT p.*, s.id AS valid_scene_id
        FROM staged_proposals p
        JOIN binder_nodes s ON s.id = p.scene_id AND s.node_type = 'SCENE'
        WHERE p.proposal_id = ? AND p.status = 'PENDING'
    """, (proposal_id,)).fetchone()
    if not proposal:
        conn.close()
        raise HTTPException(404, "Pending survey proposal not found")

    entity_type = proposal["entity_type"]
    if entity_type not in {"CHARACTER", "ITEM"}:
        conn.close()
        raise HTTPException(400, "Unsupported entity type in survey proposal")
    entity = conn.execute(
        "SELECT entity_id FROM canonical_entities WHERE lower(name) = lower(?) AND entity_type = ? LIMIT 1",
        (proposal["detected_entity_name"], entity_type),
    ).fetchone()
    if entity:
        entity_id = entity["entity_id"]
    else:
        entity_id = f"{entity_type.lower()}_{uuid.uuid4().hex}"

    try:
        delta = json.loads(proposal["proposed_delta"] or "{}")
    except json.JSONDecodeError as exc:
        conn.close()
        raise HTTPException(400, "Survey proposal contains invalid state data") from exc
    if not isinstance(delta, dict):
        conn.close()
        raise HTTPException(400, "Survey proposal state must be an object")

    now = time.strftime("%Y-%m-%d %H:%M:%S")
    event_id = f"ev_{uuid.uuid4().hex}"
    source_hash = hashlib.sha256(proposal["source_span_text"].encode("utf-8")).hexdigest()
    with conn:
        claimed = conn.execute(
            "UPDATE staged_proposals SET status = 'APPROVED' WHERE proposal_id = ? AND status = 'PENDING'",
            (proposal_id,),
        ).rowcount
        if claimed:
            if not entity:
                conn.execute("""
                    INSERT INTO canonical_entities (entity_id, name, entity_type, axioms, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (entity_id, proposal["detected_entity_name"], entity_type, json.dumps({"health_score": 1.0}), now))
            conn.execute("""
                INSERT INTO canonical_worldlines
                (event_id, entity_id, timeline_tick, scene_id, source_span_hash, state_delta, epistemic_tier, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, entity_id, proposal["timeline_tick"], proposal["scene_id"],
                source_hash, json.dumps(delta), proposal["epistemic_tier"], now,
            ))
    conn.close()
    if not claimed:
        raise HTTPException(404, "Pending survey proposal not found")
    return {"status": "approved"}


@router.post("/api/narrative/proposals/{proposal_id}/dismiss")
def dismiss_survey_proposal(proposal_id: str):
    conn = get_db()
    with conn:
        result = conn.execute(
            "UPDATE staged_proposals SET status = 'DISMISSED' WHERE proposal_id = ? AND status = 'PENDING'",
            (proposal_id,),
        )
    conn.close()
    if not result.rowcount:
        raise HTTPException(404, "Pending survey proposal not found")
    return {"status": "dismissed"}

@router.get("/api/narrative/survey-stream")
async def stream_survey(book_id: str | None = None):
    """Server-Sent Events streaming progress of local AI character/item/location worldline survey."""
    async def event_generator():
        conn = get_db()
        c = conn.cursor()
        target_b = book_id
        if not target_b:
            c.execute("""
                SELECT id FROM binder_nodes 
                WHERE node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0) 
                LIMIT 1
            """)
            r = c.fetchone()
            if r: 
                target_b = r["id"]

        c.execute("""
            SELECT s.id, s.title, s.content, ch.title as ch_title 
            FROM binder_nodes s
            JOIN binder_nodes ch ON s.parent_id = ch.id
            WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
            ORDER BY ch.sort_order ASC, s.sort_order ASC
        """, (target_b,))
        scenes = c.fetchall()
        conn.close()

        total = len(scenes)
        extracted_total = 0
        cast_conn = get_db()
        try:
            known_cast = "\n".join(f"- {line}" for line in known_cast_lines(cast_conn))
        finally:
            cast_conn.close()
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        for idx, sc in enumerate(scenes, 1):
            percent = int((idx / max(1, total)) * 100)
            payload = json.dumps({
                "current": idx, "total": total, "percent": percent, 
                "message": sc["title"], "extracted": extracted_total, "done": False
            })
            yield f"data: {payload}\n\n"

            text = html_to_text(sc["content"] or "")
            if len(text.strip()) >= 40:
                proposals = await asyncio.to_thread(extract_ghost_proposals, text, known_cast)
                db_conn = get_db()
                with db_conn:
                    for p in proposals:
                        name = p.get("detected_entity_name", "").title().strip()
                        if not name:
                            continue
                        raw_type = p.get("entity_type", "CHARACTER")
                        safe_type = sanitize_entity_type(name, raw_type)
                        if safe_type == "CLUTTER": 
                            continue
                        delta = p.get("proposed_delta", {})
                        if not isinstance(delta, dict):
                            continue
                        source_span = str(p.get("source_span_text", "")).strip()
                        confidence = p.get("confidence", 0.8)
                        try:
                            confidence = max(0.0, min(1.0, float(confidence)))
                        except (TypeError, ValueError):
                            confidence = 0.8
                        tick = idx * 0.8
                        db_conn.execute("""
                            INSERT INTO staged_proposals
                            (proposal_id, scene_id, timeline_tick, detected_entity_name, entity_type,
                             proposed_delta, confidence, epistemic_tier, attested_by, source_span_text,
                             collision_warning, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 'PENDING')
                        """, (
                            f"proposal_{uuid.uuid4().hex}", sc["id"], tick, name, safe_type,
                            json.dumps(delta), confidence,
                            p.get("epistemic_tier", "INFERENCE")
                                if p.get("epistemic_tier") in {"FACT", "CLAIM", "INFERENCE"} else "INFERENCE",
                            p.get("attested_by"), source_span,
                        ))
                        extracted_total += 1
                db_conn.close()

            await asyncio.sleep(0.02)

        final_payload = json.dumps({
            "current": total, "total": total, "percent": 100, 
            "message": "Complete!", "extracted": extracted_total, "done": True
        })
        yield f"data: {final_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

RELATIONSHIP_TYPES = {"ALLIED", "HOSTILE", "KNOWS_SECRET", "DEBT_TO", "ANCESTOR_OF", "FAMILY", "ROMANTIC", "MENTOR_OF", "RIVAL"}


@router.post("/api/narrative/connect")
def forge_connection(payload: ConnectionCreate):
    """Creates an active relationship arc between two entities in the Synaptic Web."""
    rel_type = payload.rel_type.strip().upper().replace(" ", "_")
    if not rel_type:
        raise HTTPException(400, "Choose a relationship type")
    if payload.source_id == payload.target_id:
        raise HTTPException(400, "A relationship needs two different entities")
    conn = get_db()
    try:
        found = conn.execute(
            "SELECT COUNT(*) FROM canonical_entities WHERE entity_id IN (?, ?)",
            (payload.source_id, payload.target_id),
        ).fetchone()[0]
        if found != 2:
            raise HTTPException(404, "Both entities must exist in the cast")
        duplicate = conn.execute(
            "SELECT rel_id FROM entity_relationships WHERE source_id = ? AND target_id = ? AND rel_type = ?",
            (payload.source_id, payload.target_id, rel_type),
        ).fetchone()
        rel_id = duplicate["rel_id"] if duplicate else f"rel_{uuid.uuid4().hex[:8]}"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO entity_relationships (rel_id, source_id, target_id, rel_type, description, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (rel_id, payload.source_id, payload.target_id, rel_type, payload.description.strip(), now))
        return {"status": "connected", "rel_id": rel_id}
    finally:
        conn.close()


@router.get("/api/narrative/connections")
def list_connections():
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT r.rel_id, r.source_id, r.target_id, r.rel_type, r.description, r.updated_at,
                   s.name AS source_name, t.name AS target_name
            FROM entity_relationships r
            JOIN canonical_entities s ON s.entity_id = r.source_id
            JOIN canonical_entities t ON t.entity_id = r.target_id
            ORDER BY s.name, t.name, r.rel_type
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.delete("/api/narrative/connections/{rel_id}")
def delete_connection(rel_id: str):
    conn = get_db()
    try:
        with conn:
            cur = conn.execute("DELETE FROM entity_relationships WHERE rel_id = ?", (rel_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Relationship not found")
        return {"status": "deleted"}
    finally:
        conn.close()


def _lore_forms(conn) -> list[dict]:
    """Every tracked name or lore term with the written forms that count as a mention."""
    items = []
    for row in conn.execute("SELECT name, aliases, entity_type FROM canonical_entities"):
        items.append({"label": row["name"], "kind": row["entity_type"].title(), "forms": entity_name_forms(row["name"], row["aliases"])})
    for row in conn.execute("SELECT term, category, rule_definition FROM style_sheet"):
        if row["term"].strip():
            items.append({"label": row["term"], "kind": "Lore", "detail": row["rule_definition"], "forms": [row["term"].strip()]})
    return items


def _mentioned(text: str, forms: list[str]) -> bool:
    return any(re.search(r"(?<!\w)" + re.escape(f) + r"(?!\w)", text, re.IGNORECASE) for f in forms if f)


@router.get("/api/narrative/serendipity/{scene_id}")
def get_scene_serendipity(scene_id: str):
    """Lore present in this scene, and lore that is established elsewhere in the book but dormant here."""
    conn = get_db()
    try:
        row = conn.execute("SELECT content FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'", (scene_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Scene not found")
        text = html_to_text(row["content"] or "")
        if not text.strip():
            return {"present": [], "dormant": [], "suggestion": "Draft more prose to discover lore connections.", **ai_meta(False)}

        book = conn.execute("""
            WITH RECURSIVE up(id, parent_id, node_type) AS (
                SELECT id, parent_id, node_type FROM binder_nodes WHERE id = ?
                UNION ALL SELECT p.id, p.parent_id, p.node_type FROM binder_nodes p JOIN up ON p.id = up.parent_id
            ) SELECT id FROM up WHERE node_type = 'BOOK' LIMIT 1
        """, (scene_id,)).fetchone()
        other_text = ""
        if book:
            others = conn.execute("""
                SELECT s.content FROM binder_nodes ch JOIN binder_nodes s ON s.parent_id = ch.id
                WHERE ch.parent_id = ? AND s.node_type = 'SCENE' AND s.id != ?
                  AND (s.is_archived IS NULL OR s.is_archived = 0)
            """, (book["id"], scene_id)).fetchall()
            other_text = "\n".join(html_to_text(o["content"] or "") for o in others)

        present, dormant = [], []
        for item in _lore_forms(conn):
            entry = {"label": item["label"], "kind": item["kind"], "detail": item.get("detail", "")}
            if _mentioned(text, item["forms"]):
                present.append(entry)
            elif other_text and _mentioned(other_text, item["forms"]):
                dormant.append(entry)

        lore_summary = "\n".join(f"{i['label']}: {i['detail']}" if i["detail"] else i["label"] for i in dormant[:10])
        suggestion, meta = "", ai_meta(False)
        if ENABLE_AI and dormant:
            suggestion = discover_synaptic_resonance(text, lore_summary)
            if not suggestion.startswith(("Resonance",)):
                meta = ai_meta(True)
            else:
                suggestion = ""
        return {"present": present, "dormant": dormant, "suggestion": suggestion, **meta}
    finally:
        conn.close()


@router.post("/api/narrative/promise")
def seed_promise(payload: PromiseCreate):
    """Registers a Chekhov Gravity Well foreshadowing attractor in SQLite."""
    conn = get_db()
    c = conn.cursor()
    b_id = payload.book_id
    if not b_id:
        c.execute("SELECT id FROM binder_nodes WHERE node_type = 'BOOK' LIMIT 1")
        row = c.fetchone()
        if row: 
            b_id = row["id"]
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO promises_ledger 
            (series_id, book_id, planted_scene_id, target_volume, target_tick, target_location, promise_desc, status, created_at)
            VALUES ('default', ?, ?, ?, ?, ?, ?, 'SEEDED', ?)
        """, (b_id, payload.scene_id or 'active_scene', payload.target_volume, payload.target_tick, payload.target_location, payload.promise_desc, ts))
    conn.close()
    return {"status": "success"}


class PromiseStatus(BaseModel):
    status: str


@router.get("/api/narrative/promises")
def list_promises(book_id: str):
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT p.id, p.book_id, p.planted_scene_id, p.target_tick, p.target_location,
                   p.promise_desc, p.status, p.created_at, n.title AS planted_scene_title
            FROM promises_ledger p LEFT JOIN binder_nodes n ON n.id = p.planted_scene_id
            WHERE p.book_id = ? ORDER BY p.id
        """, (book_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.put("/api/narrative/promises/{promise_id}")
def update_promise(promise_id: int, payload: PromiseStatus):
    status = payload.status.upper()
    if status not in {"SEEDED", "PAID_OFF", "DROPPED"}:
        raise HTTPException(400, "Status must be SEEDED, PAID_OFF or DROPPED")
    conn = get_db()
    try:
        with conn:
            cur = conn.execute("UPDATE promises_ledger SET status = ? WHERE id = ?", (status, promise_id))
        if not cur.rowcount:
            raise HTTPException(404, "Promise not found")
        return {"status": status}
    finally:
        conn.close()


@router.delete("/api/narrative/promises/{promise_id}")
def delete_promise(promise_id: int):
    conn = get_db()
    try:
        with conn:
            cur = conn.execute("DELETE FROM promises_ledger WHERE id = ?", (promise_id,))
        if not cur.rowcount:
            raise HTTPException(404, "Promise not found")
        return {"status": "deleted"}
    finally:
        conn.close()
