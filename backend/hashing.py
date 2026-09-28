import re
import hashlib
import sqlite3

def compute_block_hash(paragraph_text: str) -> str:
    """
    Computes a 16-character content-normalized semantic hash for a paragraph block.
    Normalizes internal whitespace, strips punctuation, and lowercases text.
    Ensures typo corrections or punctuation edits do NOT trigger false severed thread alarms.
    """
    if not paragraph_text:
        return ""
    # Strip all punctuation and symbols, retain alphanumeric characters and basic whitespace
    normalized = re.sub(r'[^\w\s]', '', paragraph_text.lower())
    # Collapse multiple spaces, newlines, and tabs into single spaces
    clean_text = " ".join(normalized.split())
    if not clean_text:
        return ""
    return hashlib.sha256(clean_text.encode('utf-8')).hexdigest()[:16]

def get_scene_block_hashes(scene_text: str) -> list[str]:
    """
    Splits scene text on double newlines and returns semantic hashes
    for all non-empty paragraph blocks.
    """
    if not scene_text or not scene_text.strip():
        return []
    paragraphs = [p.strip() for p in scene_text.split("\n\n") if p.strip()]
    hashes = []
    for p in paragraphs:
        h = compute_block_hash(p)
        if h:
            hashes.append(h)
    return hashes

def find_severed_threads(conn: sqlite3.Connection, scene_id: str, current_scene_text: str) -> list[dict]:
    """
    Inspects canonical_worldlines for the given scene_id.
    Flags any worldline event whose origin text anchor (source_span_hash)
    has been cut, excised, or fundamentally altered in the current scene text.
    """
    active_hashes = set(get_scene_block_hashes(current_scene_text))
    c = conn.cursor()
    c.execute("""
        SELECT event_id, entity_id, timeline_tick, state_delta, epistemic_tier, source_span_hash
        FROM canonical_worldlines
        WHERE scene_id = ?
    """, (scene_id,))
    rows = c.fetchall()

    severed = []
    for r in rows:
        span_hash = r["source_span_hash"]
        # Ignore non-block placeholders (e.g. bulk surveyed tags)
        if span_hash in {"surveyed", "initial_seed", ""}:
            continue
        if span_hash not in active_hashes:
            severed.append({
                "event_id": r["event_id"],
                "entity_id": r["entity_id"],
                "timeline_tick": r["timeline_tick"],
                "state_delta": r["state_delta"],
                "epistemic_tier": r["epistemic_tier"],
                "missing_hash": span_hash
            })
    return severed
