import json
import sqlite3

def get_entity_state_at_tick(conn: sqlite3.Connection, entity_id: str, target_tick: float) -> dict:
    """
    Folds all canonical event deltas up to target_tick into an authoritative state dictionary.
    Replays the append-only event ledger chronologically over the entity's baseline axioms.
    """
    c = conn.cursor()
    c.execute("SELECT axioms FROM canonical_entities WHERE entity_id = ?", (entity_id,))
    base_row = c.fetchone()
    if not base_row:
        return {}
        
    current_state = json.loads(base_row["axioms"]) if base_row["axioms"] else {}

    c.execute("""
        SELECT state_delta, timeline_tick, epistemic_tier 
        FROM canonical_worldlines 
        WHERE entity_id = ? AND timeline_tick <= ?
        ORDER BY timeline_tick ASC, rowid ASC
    """, (entity_id, target_tick))
    
    events = c.fetchall()
    for row in events:
        try:
            delta = json.loads(row["state_delta"])
            current_state.update(delta)
        except Exception:
            continue
            
    return current_state

def detect_causal_collisions(
    conn: sqlite3.Connection, 
    entity_id: str, 
    target_tick: float, 
    incoming_action: str | None = None, 
    proposed_location: str | None = None
) -> list[str]:
    """
    Audits incoming scene proposals against the entity's folded canonical state at target_tick.
    Identifies physiological contradictions and spatial teleportation paradoxes.
    """
    state = get_entity_state_at_tick(conn, entity_id, target_tick)
    collisions = []

    # 1. Biological Health Strain Collision
    health = float(state.get("health_score", 1.0))
    strenuous_actions = {"combat", "climb", "sprint", "duel", "hull_climb", "heist"}
    if incoming_action and incoming_action.lower() in strenuous_actions and health < 0.40:
        collisions.append(
            f"BIOLOGICAL CONTRADICTION: {entity_id.title()} attempted high-strain action '{incoming_action}' "
            f"while health_score is {health:.2f} (< 0.40)."
        )

    # 2. Spatial Teleportation Collision
    current_loc = state.get("location")
    if proposed_location and current_loc and proposed_location != current_loc:
        c = conn.cursor()
        c.execute("""
            SELECT timeline_tick FROM canonical_worldlines 
            WHERE entity_id = ? AND timeline_tick <= ?
            ORDER BY timeline_tick DESC LIMIT 1
        """, (entity_id, target_tick))
        last_event = c.fetchone()
        if last_event and abs(target_tick - float(last_event["timeline_tick"])) <= 0.05:
            collisions.append(
                f"SPATIAL TELEPORTATION: {entity_id.title()} transitioned from '{current_loc}' to '{proposed_location}' "
                f"with negligible elapsed story time (delta <= 0.05 days)."
            )

    return collisions
