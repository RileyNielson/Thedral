import re
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_db
from backend.guardrails import sanitize_entity_type

router = APIRouter(tags=["Entities"])

class QuickEntity(BaseModel):
    name: str
    entity_type: str = "CHARACTER"
    role: str = "SUPPORTING"
    aliases: str = ""

@router.get("/api/entities")
def get_all_entities():
    """Returns all verified characters and key plot artifacts."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM canonical_entities ORDER BY entity_type ASC, name ASC")
    entities = [dict(r) for r in c.fetchall()]
    conn.close()
    return entities

@router.post("/api/entities/quick-register")
def register_entity(payload: QuickEntity):
    """Registers a character or artifact, enforcing the Clutter Shield."""
    name_clean = payload.name.strip()
    safe_type = sanitize_entity_type(name_clean, payload.entity_type)
    if safe_type == "CLUTTER":
        raise HTTPException(400, f"'{name_clean}' is background clutter, not a character or key artifact.")

    conn = get_db()
    eid = re.sub(r'\W+', '_', name_clean.lower())
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO canonical_entities 
            (entity_id, name, entity_type, role, aliases, sensory_profile, status, axioms, created_at)
            VALUES (?, ?, ?, ?, ?, '', 'ALIVE', '{}', ?)
            ON CONFLICT(entity_id) DO UPDATE SET 
                entity_type = excluded.entity_type,
                aliases = CASE WHEN excluded.aliases != '' THEN excluded.aliases ELSE canonical_entities.aliases END
        """, (eid, name_clean, safe_type, payload.role, payload.aliases, now))
    conn.close()
    return {"status": "registered", "entity_id": eid, "entity_type": safe_type}

@router.delete("/api/entities/{entity_id}")
def delete_entity(entity_id: str):
    """Safely deletes an entity, clearing referencing worldlines and relationships first to satisfy foreign keys."""
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM canonical_worldlines WHERE entity_id = ?", (entity_id,))
        conn.execute("DELETE FROM entity_relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
        conn.execute("DELETE FROM canonical_entities WHERE entity_id = ?", (entity_id,))
    conn.close()
    return {"status": "deleted"}
