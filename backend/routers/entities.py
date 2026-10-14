import re
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_db
from backend.entity_names import parse_entity_aliases, serialize_entity_aliases
from backend.guardrails import sanitize_entity_type
from backend.text_utils import html_to_text
from backend.wiktionary_lexicon import english_words, get_lexicon_status

router = APIRouter(tags=["Entities"])

class QuickEntity(BaseModel):
    name: str
    entity_type: str = "CHARACTER"
    role: str = "SUPPORTING"
    aliases: str | list[str] = ""


class EntityAliasesUpdate(BaseModel):
    aliases: list[str]


_NON_NAME_CAPITALS = {
    "a", "an", "and", "as", "at", "but", "for", "he", "her", "hers", "him",
    "his", "i", "if", "in", "it", "its", "me", "my", "nor", "of", "on",
    "or", "our", "she", "so", "the", "their", "them", "they", "this", "to",
    "us", "we", "you", "your",
}
_SENTENCE_OPENERS = {
    "then", "when", "but", "after", "before", "while", "suddenly", "now", "with", "without", "by", "from",
    "once", "later", "still", "there", "here", "what", "why", "how", "where", "who", "yes", "no", "oh",
    "well", "maybe", "perhaps", "however", "meanwhile", "although", "though", "because", "since", "until",
    "every", "each", "some", "all", "one", "two", "that", "these", "those", "there's", "i'm", "i'll", "i'd",
}
_ENTITY_TYPES = {"CHARACTER", "ITEM", "LOCATION", "FACTION", "WORLD_TERM"}


def _candidate_names(
    scenes: list[dict],
    existing: list[dict],
    dictionary_words: set[str] | None = None,
) -> list[dict]:
    known_names = set()
    for entity in existing:
        known_names.add(entity["name"].casefold().strip())
        known_names.update(alias.casefold() for alias in parse_entity_aliases(entity.get("aliases")))

    occurrences = defaultdict(list)
    sentence_split = re.compile(r"(?<=[.!?])\s+|\n+")
    capitalized = re.compile(r"[A-Z][A-Za-z0-9'’.-]*")
    for scene in scenes:
        text = html_to_text(scene["content"] or "")
        for sentence in sentence_split.split(text):
            matches = list(capitalized.finditer(sentence))
            run = []
            runs = []
            for match in matches:
                if run and sentence[run[-1].end():match.start()].strip():
                    runs.append(run)
                    run = []
                run.append(match)
            if run:
                runs.append(run)
            for name_parts in runs:
                if name_parts[0].start() < 3:
                    # A sentence opener is only a name when it leads a multi-word name such as "Rowan Hale".
                    if name_parts[0].group(0).casefold() in _SENTENCE_OPENERS:
                        name_parts = name_parts[1:]
                    elif len(name_parts) < 2:
                        continue
                if not name_parts:
                    continue
                name = " ".join(part.group(0) for part in name_parts).strip(" .-'’")
                if len(name) < 2 or name.casefold() in _NON_NAME_CAPITALS:
                    continue
                if name.casefold() not in known_names:
                    occurrences[name.casefold()].append({
                        "name": name,
                        "scene_id": scene["id"],
                        "scene_title": scene["title"],
                        "excerpt": sentence.strip()[:280],
                    })

    candidates = []
    for mentions in occurrences.values():
        scene_ids = {mention["scene_id"] for mention in mentions}
        name = mentions[0]["name"]
        if (len(mentions) < 2 and len(scene_ids) < 2) or (len(name.split()) == 1 and len(mentions) < 3 and len(scene_ids) < 2):
            continue
        candidates.append({
            "name": name,
            "mentions": len(mentions),
            "scene_count": len(scene_ids),
            "examples": mentions[:3],
            "in_wiktionary": name.casefold() in dictionary_words if dictionary_words is not None else None,
        })
    return sorted(candidates, key=lambda item: (-item["mentions"], item["name"].casefold()))[:100]


@router.get("/api/entities")
def get_all_entities():
    """Returns all verified characters and key plot artifacts."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM canonical_entities ORDER BY entity_type ASC, name ASC")
    entities = [dict(r) for r in c.fetchall()]
    conn.close()
    return entities


@router.get("/api/entities/candidates/{book_id}")
def get_entity_candidates(book_id: str):
    """Find recurring capitalized manuscript terms for author review; never auto-register them."""
    conn = get_db()
    try:
        book = conn.execute(
            "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'BOOK' AND (is_archived IS NULL OR is_archived = 0)",
            (book_id,),
        ).fetchone()
        if not book:
            raise HTTPException(404, "Manuscript not found")
        scenes = [
            dict(row)
            for row in conn.execute("""
                SELECT s.id, s.title, s.content
                FROM binder_nodes ch
                JOIN binder_nodes s ON s.parent_id = ch.id
                WHERE ch.parent_id = ? AND s.node_type = 'SCENE'
                  AND (s.is_archived IS NULL OR s.is_archived = 0)
                ORDER BY ch.sort_order, s.sort_order
            """, (book_id,))
        ]
        entities = [
            dict(row)
            for row in conn.execute("SELECT name, aliases FROM canonical_entities")
        ]
        candidates = _candidate_names(scenes, entities)
        lexicon = get_lexicon_status()
        if lexicon["available"]:
            dictionary_words = english_words(candidate["name"] for candidate in candidates)
            for candidate in candidates:
                candidate["in_wiktionary"] = candidate["name"].casefold() in dictionary_words
        return {"candidates": candidates, "wiktionary_available": lexicon["available"]}
    finally:
        conn.close()


_PLACE_WORDS = {
    "castle", "city", "river", "mountain", "mountains", "forest", "kingdom", "village", "town", "lake",
    "sea", "ocean", "tower", "island", "valley", "bridge", "harbor", "harbour", "keep", "hall", "road",
    "street", "bay", "port", "woods", "desert", "temple", "inn", "tavern", "palace", "fortress",
}
_GROUP_WORDS = {"guild", "order", "house", "clan", "council", "army", "legion", "company", "brotherhood", "court"}


def _guess_entity_type(name: str) -> str:
    words = {part.casefold() for part in name.split()}
    if len(words) > 1 and words & _PLACE_WORDS:
        return "LOCATION"
    if len(words) > 1 and words & _GROUP_WORDS:
        return "FACTION"
    return "CHARACTER"


def _is_confident(candidate: dict, lexicon_available: bool) -> bool:
    if candidate["mentions"] < 3 or candidate["scene_count"] < 2:
        return False
    if lexicon_available and candidate.get("in_wiktionary"):
        return False
    return lexicon_available or len(candidate["name"].split()) > 1 or candidate["mentions"] >= 5


@router.post("/api/entities/auto-detect/{book_id}")
def auto_detect_entities(book_id: str):
    """Track confident recurring names automatically; the author only corrects mistakes."""
    data = get_entity_candidates(book_id)
    conn = get_db()
    added = []
    try:
        dismissed = {row[0] for row in conn.execute("SELECT name_key FROM entity_dismissals")}
        for candidate in data["candidates"]:
            if candidate["name"].casefold() in dismissed or not _is_confident(candidate, data["wiktionary_available"]):
                continue
            entity_type = sanitize_entity_type(candidate["name"], _guess_entity_type(candidate["name"]))
            if entity_type == "CLUTTER":
                continue
            eid = re.sub(r'\W+', '_', candidate["name"].lower())
            try:
                _reject_name_conflicts(conn, eid, candidate["name"], [])
            except HTTPException:
                continue
            with conn:
                cursor = conn.execute("""
                    INSERT OR IGNORE INTO canonical_entities
                    (entity_id, name, entity_type, role, aliases, sensory_profile, status, axioms, created_at, auto_detected)
                    VALUES (?, ?, ?, 'SUPPORTING', '[]', '', 'ALIVE', '{}', ?, 1)
                """, (eid, candidate["name"], entity_type, time.strftime("%Y-%m-%d %H:%M:%S")))
            if cursor.rowcount:
                added.append({"entity_id": eid, "name": candidate["name"], "entity_type": entity_type})
        return {"added": added}
    finally:
        conn.close()


@router.post("/api/entities/{entity_id}/confirm")
def confirm_entity(entity_id: str):
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute("UPDATE canonical_entities SET auto_detected = 0 WHERE entity_id = ?", (entity_id,))
        if not cursor.rowcount:
            raise HTTPException(404, "Entity not found")
        return {"status": "confirmed"}
    finally:
        conn.close()


@router.post("/api/entities/quick-register")
def register_entity(payload: QuickEntity):
    """Registers a character or artifact, enforcing the Clutter Shield."""
    name_clean = payload.name.strip()
    requested_type = payload.entity_type.strip().upper()
    if requested_type not in _ENTITY_TYPES:
        raise HTTPException(400, f"Unsupported entity type: {requested_type}")
    safe_type = sanitize_entity_type(name_clean, requested_type)
    if safe_type == "CLUTTER":
        raise HTTPException(400, f"'{name_clean}' is background clutter, not a character or key artifact.")

    conn = get_db()
    try:
        eid = re.sub(r'\W+', '_', name_clean.lower())
        aliases = parse_entity_aliases(payload.aliases)
        _reject_name_conflicts(conn, eid, name_clean, aliases)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute("""
                INSERT INTO canonical_entities
                (entity_id, name, entity_type, role, aliases, sensory_profile, status, axioms, created_at)
                VALUES (?, ?, ?, ?, ?, '', 'ALIVE', '{}', ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    entity_type = excluded.entity_type,
                    auto_detected = 0,
                    aliases = CASE WHEN excluded.aliases != '[]' THEN excluded.aliases ELSE canonical_entities.aliases END
            """, (eid, name_clean, safe_type, payload.role, serialize_entity_aliases(aliases), now))
        with conn:
            conn.execute("DELETE FROM entity_dismissals WHERE name_key = ?", (name_clean.casefold(),))
        return {"status": "registered", "entity_id": eid, "entity_type": safe_type}
    finally:
        conn.close()


def _reject_name_conflicts(conn, entity_id: str, name: str, aliases: list[str]) -> None:
    forms = {name.casefold(), *(alias.casefold() for alias in aliases)}
    for entity in conn.execute("SELECT entity_id, name, aliases FROM canonical_entities"):
        if entity["entity_id"] == entity_id:
            continue
        existing_forms = {
            entity["name"].casefold(),
            *(alias.casefold() for alias in parse_entity_aliases(entity["aliases"])),
        }
        overlap = forms & existing_forms
        if overlap:
            conflict = sorted(overlap)[0]
            raise HTTPException(
                409,
                f"'{conflict}' already identifies another canon entity ({entity['name']}). "
                "Choose a more specific name to keep manuscript tracking unambiguous.",
            )


@router.put("/api/entities/{entity_id}/aliases")
def update_entity_aliases(entity_id: str, payload: EntityAliasesUpdate):
    """Replace the confirmed alternate names for one canon entity."""
    conn = get_db()
    try:
        entity = conn.execute(
            "SELECT entity_id, name FROM canonical_entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if not entity:
            raise HTTPException(404, "Entity not found")
        aliases = parse_entity_aliases(payload.aliases)
        _reject_name_conflicts(conn, entity_id, entity["name"], aliases)
        with conn:
            conn.execute(
                "UPDATE canonical_entities SET aliases = ? WHERE entity_id = ?",
                (serialize_entity_aliases(aliases), entity_id),
            )
        return {"status": "updated", "entity_id": entity_id, "aliases": aliases}
    finally:
        conn.close()

@router.delete("/api/entities/{entity_id}")
def delete_entity(entity_id: str):
    """Safely deletes an entity, clearing referencing worldlines and relationships first to satisfy foreign keys."""
    conn = get_db()
    with conn:
        row = conn.execute("SELECT name, auto_detected FROM canonical_entities WHERE entity_id = ?", (entity_id,)).fetchone()
        if row and row["auto_detected"]:
            conn.execute("INSERT OR IGNORE INTO entity_dismissals (name_key) VALUES (?)", (row["name"].casefold(),))
        conn.execute("DELETE FROM canonical_worldlines WHERE entity_id = ?", (entity_id,))
        conn.execute("DELETE FROM entity_relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
        conn.execute("DELETE FROM canonical_entities WHERE entity_id = ?", (entity_id,))
    conn.close()
    return {"status": "deleted"}
