import re
import time
from collections import defaultdict, Counter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_db
from backend.entity_names import parse_entity_aliases, serialize_entity_aliases, text_mentions_entity
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

def _candidate_names(scenes: list[dict], existing: list[dict], dictionary_words: set[str] | None = None) -> list[dict]:
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
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM canonical_entities ORDER BY entity_type ASC, name ASC")
    entities = [dict(r) for r in c.fetchall()]
    conn.close()
    return entities


@router.get("/api/entities/{entity_id}/dossier")
def get_entity_dossier(entity_id: str):
    """
    100% Deterministic Character Dossier Generator.
    Extracts observed physical traits, first appearance, scene frequency,
    top associates, and dialogue statistics directly from the manuscript text.
    """
    conn = get_db()
    try:
        entity = conn.execute(
            "SELECT entity_id, name, entity_type, role, aliases, sensory_profile, status FROM canonical_entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if not entity:
            raise HTTPException(404, "Entity not found")

        name = entity["name"]
        aliases = parse_entity_aliases(entity["aliases"])
        all_name_forms = [name] + aliases

        # Fetch all scenes in order
        scenes = [
            dict(r) for r in conn.execute("""
                SELECT s.id, s.title, s.content, ch.title as chapter_title, ch.sort_order as ch_sort, s.sort_order as sc_sort
                FROM binder_nodes s
                JOIN binder_nodes ch ON s.parent_id = ch.id
                WHERE s.node_type = 'SCENE' AND (s.is_archived IS NULL OR s.is_archived = 0)
                ORDER BY ch.sort_order ASC, s.sort_order ASC
            """).fetchall()
        ]

        # Fetch all other registered characters for associate tracking
        other_chars = [
            dict(r) for r in conn.execute(
                "SELECT entity_id, name, aliases FROM canonical_entities WHERE entity_id != ? AND entity_type = 'CHARACTER'",
                (entity_id,),
            ).fetchall()
        ]

        first_appearance = None
        present_scenes = []
        present_chapters = []
        associate_counts = Counter()
        observed_traits = set()
        spoken_lines = 0
        spoken_words = 0

        # Regex for character appositive descriptions: "Cali, the queen's orbiter,"
        appositive_pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(f) for f in all_name_forms) + r")\s*,\s+(the\s+[a-z\s]{3,35}?)\s*,",
            re.IGNORECASE,
        )

        # Regex for physical traits: "hazel-yellow eyes", "red beard"
        trait_pattern = re.compile(
            r"\b(?:her|his|their|" + "|".join(re.escape(f) for f in all_name_forms) + r")['’]?s?\s+([a-z\-]+(?:\s+[a-z\-]+)?\s+(?:eyes|hair|beard|armor|dress|voice|face|hands?|smile))\b",
            re.IGNORECASE,
        )

        for sc in scenes:
            raw_text = html_to_text(sc["content"] or "")
            if not raw_text:
                continue

            # Check if entity appears in this scene
            if any(text_mentions_entity(raw_text, form, None) for form in all_name_forms):
                if not first_appearance:
                    first_appearance = f"{sc['chapter_title']} / {sc['title']}"
                present_scenes.append(sc["title"])
                if sc["chapter_title"] not in present_chapters:
                    present_chapters.append(sc["chapter_title"])

                # Check co-occurrence with other cast members
                for other in other_chars:
                    if text_mentions_entity(raw_text, other["name"], other["aliases"]):
                        associate_counts[other["name"]] += 1

                # Extract appositive roles
                for m in appositive_pattern.finditer(raw_text):
                    observed_traits.add(m.group(1).strip().lower())

                # Extract physical modifications
                for m in trait_pattern.finditer(raw_text):
                    trait = m.group(1).strip().lower()
                    if len(trait) > 5 and not any(sw in trait for sw in ("the", "this", "that")):
                        observed_traits.add(trait)

                # Dialogue stats (Count turns attributed to this entity)
                dialogue_matches = re.findall(
                    r'["“]([^"”]{1,400})["”]\s*,?\s*(?:' + "|".join(re.escape(f) for f in all_name_forms) + r')\s+(?:said|asked|replied|whispered|hissed|laughed|says)',
                    raw_text,
                    re.IGNORECASE,
                )
                spoken_lines += len(dialogue_matches)
                spoken_words += sum(len(line.split()) for line in dialogue_matches)

        top_associates = [
            {"name": char_name, "shared_scenes": count}
            for char_name, count in associate_counts.most_common(5)
        ]

        return {
            "entity_id": entity["entity_id"],
            "name": entity["name"],
            "entity_type": entity["entity_type"],
            "role": entity["role"],
            "aliases": aliases,
            "first_appearance": first_appearance or "Not yet in manuscript",
            "total_scenes": len(present_scenes),
            "chapters_present": present_chapters,
            "traits": sorted(list(observed_traits))[:6],
            "top_associates": top_associates,
            "dialogue_stats": {
                "lines_spoken": spoken_lines,
                "words_spoken": spoken_words,
            },
        }
    finally:
        conn.close()


@router.get("/api/entities/candidates/{book_id}")
def get_entity_candidates(book_id: str):
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


@router.post("/api/entities/quick-register")
def register_entity(payload: QuickEntity):
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
        return {"status": "registered", "entity_id": eid, "entity_type": safe_type}
    finally:
        conn.close()


@router.put("/api/entities/{entity_id}/aliases")
def update_entity_aliases(entity_id: str, payload: EntityAliasesUpdate):
    conn = get_db()
    try:
        entity = conn.execute(
            "SELECT entity_id, name FROM canonical_entities WHERE entity_id = ?",
            (entity_id,),
        ).fetchone()
        if not entity:
            raise HTTPException(404, "Entity not found")
        aliases = parse_entity_aliases(payload.aliases)
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
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM canonical_worldlines WHERE entity_id = ?", (entity_id,))
        conn.execute("DELETE FROM entity_relationships WHERE source_id = ? OR target_id = ?", (entity_id, entity_id))
        conn.execute("DELETE FROM canonical_entities WHERE entity_id = ?", (entity_id,))
    conn.close()
    return {"status": "deleted"}
