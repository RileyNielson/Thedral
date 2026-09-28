import re
import json
import time
import uuid
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.database import get_db
from backend.astrolabe import build_astrolabe_manifest
from backend.guardrails import sanitize_entity_type
from backend.socratic import extract_ghost_proposals, discover_synaptic_resonance

router = APIRouter(tags=["Narrative 3D"])

class ConnectionCreate(BaseModel):
    source_id: str
    target_id: str
    rel_type: str
    description: str = ""

class PromiseCreate(BaseModel):
    book_id: str | None = None
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
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        for idx, sc in enumerate(scenes, 1):
            percent = int((idx / max(1, total)) * 100)
            payload = json.dumps({
                "current": idx, "total": total, "percent": percent, 
                "message": sc["title"], "extracted": extracted_total, "done": False
            })
            yield f"data: {payload}\n\n"

            text = sc["content"] or ""
            if len(text.strip()) >= 40:
                proposals = await asyncio.to_thread(extract_ghost_proposals, text)
                db_conn = get_db()
                with db_conn:
                    for p in proposals:
                        name = p.get("detected_entity_name", "").title().strip()
                        raw_type = p.get("entity_type", "CHARACTER")
                        safe_type = sanitize_entity_type(name, raw_type)
                        if safe_type == "CLUTTER": 
                            continue

                        eid = re.sub(r'\W+', '_', name.lower())
                        default_axioms = json.dumps({'health_score': 1.0})
                        
                        db_conn.execute("""
                            INSERT INTO canonical_entities (entity_id, name, entity_type, axioms, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(entity_id) DO NOTHING
                        """, (eid, name, safe_type, default_axioms, now))

                        ev_id = f"ev_{uuid.uuid4().hex[:8]}"
                        delta = p.get("proposed_delta", {})
                        
                        # Automatically register extracted story locations into Y-axis corridors
                        loc_name = delta.get("location")
                        if loc_name and len(loc_name.strip()) > 2 and loc_name != "Unknown":
                            loc_clean = loc_name.strip().title()
                            loc_id = f"loc_{re.sub(r'\\W+', '_', loc_clean.lower())}"
                            db_conn.execute("""
                                INSERT INTO canonical_entities (entity_id, name, entity_type, axioms, created_at)
                                VALUES (?, ?, 'LOCATION', '{}', ?)
                                ON CONFLICT(entity_id) DO NOTHING
                            """, (loc_id, loc_clean, now))
                        else:
                            delta["location"] = sc["ch_title"].replace("Chapter: ", "").strip()

                        tick = idx * 0.8
                        db_conn.execute("""
                            INSERT INTO canonical_worldlines 
                            (event_id, entity_id, timeline_tick, scene_id, source_span_hash, state_delta, epistemic_tier, created_at)
                            VALUES (?, ?, ?, ?, 'surveyed', ?, ?, ?)
                        """, (ev_id, eid, tick, sc["id"], json.dumps(delta), p.get("epistemic_tier", "FACT"), now))
                        extracted_total += 1
                db_conn.close()

            await asyncio.sleep(0.02)

        final_payload = json.dumps({
            "current": total, "total": total, "percent": 100, 
            "message": "Complete!", "extracted": extracted_total, "done": True
        })
        yield f"data: {final_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/api/narrative/connect")
def forge_connection(payload: ConnectionCreate):
    """Creates an active relationship arc between two entities in the Synaptic Web."""
    conn = get_db()
    rel_id = f"rel_{uuid.uuid4().hex[:8]}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT OR REPLACE INTO entity_relationships (rel_id, source_id, target_id, rel_type, description, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (rel_id, payload.source_id, payload.target_id, payload.rel_type, payload.description, now))
    conn.close()
    return {"status": "connected"}

@router.get("/api/narrative/serendipity/{scene_id}")
def get_scene_serendipity(scene_id: str):
    """Uncovers dormant connections between the current scene and established series lore."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT content FROM binder_nodes WHERE id = ?", (scene_id,))
    row = c.fetchone()
    if not row or not row["content"]:
        conn.close()
        return {"suggestion": "Draft more prose to discover lore connections."}

    c.execute("SELECT term, rule_definition FROM style_sheet LIMIT 10")
    rules = [f"{r['term']}: {r['rule_definition']}" for r in c.fetchall()]
    lore_summary = chr(10).join(rules) if rules else "No established style lore."
    conn.close()

    suggestion = discover_synaptic_resonance(row["content"], lore_summary)
    return {"suggestion": suggestion}

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
            VALUES ('default', ?, 'active_scene', ?, ?, ?, ?, 'SEEDED', ?)
        """, (b_id, payload.target_volume, payload.target_tick, payload.target_location, payload.promise_desc, ts))
    conn.close()
    return {"status": "success"}