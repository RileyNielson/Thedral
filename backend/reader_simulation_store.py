import json
import sqlite3
import time
import re
from fastapi import HTTPException

from backend.text_utils import html_to_text


READER_SIMULATION_PROMPT_VERSION = "first-read-v5"
SIMULATION_VERSION = "3.0-cognitive"
READER_CONTEXT_CHAR_LIMIT = 3500
READER_SIMULATION_SYSTEM_PROMPT = """Simulate a careful first-time reader encountering only the supplied manuscript text, without author notes, goals, summaries, character sheets, or intended takeaways. When earlier text is provided, it is a limited excerpt of what the reader encountered before the current scene; do not assume it represents the entire manuscript. This is an AI hypothesis to help the author revise before recruiting readers; it is not actual reader feedback and must not be presented as representative or certain. Consider what a reader can understand from the text alone, what they may infer, wonder about, or misunderstand, and where they might lose the thread. Do not guess what the author intended.
Estimate the likely experience as the scene unfolds: emotional state and shifts, interest/engagement, tension, mystery/curiosity, suspense/anticipation, character connection, confusion, and attention or pacing changes. Explain what textual beat appears to cause each estimate. These are qualitative AI estimates, not measurements. Use integer levels 1–5 only as an ordinal shorthand: 1 very low, 2 low, 3 moderate, 4 high, 5 very high. Do not imply clinical emotion detection or certainty about actual readers. A score without a specific textual cause and evidence is not useful.
Every item MUST cite an exact, short verbatim excerpt from the supplied manuscript text. Keep claims specific to that excerpt. Provide no item when there is no useful observation. For emotional_arc, identify the beat position (opening, early, middle, late, ending) and name a plausible emotion or emotional mix; do not force a change if the text does not support one. Interest and tension may rise, fall, or stay steady. Distinguish mystery (a question or information gap the reader wants resolved) from suspense (anticipation of a consequential outcome). Revision experiments should be optional and open-ended, not prescriptive rewrites. Include at most three useful items per dimension; empty arrays are preferable to invented insight.
Return strict JSON:
{"reader_experience":{"emotional_arc":[{"moment":"opening|early|middle|late|ending","estimate":"emotion or emotional mix","level":1,"cause":"What in the beat may prompt this","evidence":"Exact quote"}],"interest":[{"moment":"beat position","estimate":"interest level","level":1,"cause":"What draws or loses attention","evidence":"Exact quote"}],"tension":[{"moment":"beat position","estimate":"tension level","level":1,"cause":"What raises, releases, or sustains pressure","evidence":"Exact quote"}],"mystery":[{"moment":"beat position","estimate":"question or information gap","level":1,"cause":"What creates curiosity","evidence":"Exact quote"}],"suspense":[{"moment":"beat position","estimate":"anticipated consequence or outcome","level":1,"cause":"What creates anticipation or uncertainty","evidence":"Exact quote"}],"character_connection":[{"moment":"beat position","estimate":"possible reader connection or distance","level":1,"cause":"What in the character's behavior or situation prompts it","evidence":"Exact quote"}],"confusion":[{"moment":"beat position","estimate":"what may be unclear","level":1,"cause":"What makes orientation or meaning difficult","evidence":"Exact quote"}],"attention":[{"moment":"beat position","estimate":"attention or momentum change","level":1,"cause":"What in the prose or event sequence prompts the change","evidence":"Exact quote"}]},"direct":[{"claim":"What a first-time reader may clearly understand","evidence":"Exact quote"}],"inferred":[{"claim":"A possible reader inference or reaction","evidence":"Exact quote"}],"delayed":[{"claim":"A question or expectation the reader may carry forward","evidence":"Exact quote"}],"friction":[{"claim":"A possible point of confusion or attention break","evidence":"Exact quote"}],"revision_focus":[{"claim":"An optional revision experiment or question for the author","evidence":"Exact quote"}]}"""

READER_EXPERIENCE_DIMENSIONS = {
    "emotional_arc": ("EMOTIONAL_ARC", "estimate"),
    "interest": ("READER_INTEREST", "estimate"),
    "tension": ("TENSION", "estimate"),
    "mystery": ("MYSTERY", "estimate"),
    "suspense": ("SUSPENSE", "estimate"),
    "character_connection": ("CHARACTER_CONNECTION", "estimate"),
    "confusion": ("CONFUSION", "estimate"),
    "attention": ("ATTENTION", "estimate"),
}

def _quoted_excerpt(text: str, excerpt: str) -> str:
    excerpt = " ".join((excerpt or "").split())
    if not excerpt:
        return ""
    normalized_text = " ".join(text.split())
    match = re.search(re.escape(excerpt), normalized_text, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _serialize_simulation(row: sqlite3.Row | dict) -> dict:
    result = dict(row)
    result["items"] = json.loads(result.pop("result_json"))
    source_text = result.pop("source_text")
    result["source_characters"] = len(source_text)
    result["reading_mode"] = result.get("reading_mode") or "scene"
    result["reading_context"] = result.get("reading_context") or ""
    result["context_characters"] = len(result["reading_context"])
    result["analyzed_scene_characters"] = len(result["analyzed_text"])
    result["analyzed_characters"] = result["analyzed_scene_characters"] + result["context_characters"]
    return result


def _preceding_scene_context(conn: sqlite3.Connection, scene_id: str) -> str:
    book = conn.execute("""
        WITH RECURSIVE ancestors(id, parent_id, node_type) AS (
            SELECT id, parent_id, node_type FROM binder_nodes WHERE id = ?
            UNION ALL
            SELECT parent.id, parent.parent_id, parent.node_type
            FROM binder_nodes parent
            JOIN ancestors child ON parent.id = child.parent_id
        )
        SELECT id FROM ancestors WHERE node_type = 'BOOK' LIMIT 1
    """, (scene_id,)).fetchone()
    if not book:
        raise HTTPException(404, "Scene is not part of a manuscript")

    rows = conn.execute("""
        WITH RECURSIVE descendants AS (
            SELECT id, parent_id, node_type, title, sort_order, content
            FROM binder_nodes WHERE id = ?
            UNION ALL
            SELECT child.id, child.parent_id, child.node_type, child.title, child.sort_order, child.content
            FROM binder_nodes child
            JOIN descendants parent ON child.parent_id = parent.id
            WHERE COALESCE(child.is_archived, 0) = 0
        )
        SELECT id, parent_id, node_type, title, sort_order, content FROM descendants
    """, (book["id"],)).fetchall()
    nodes = {row["id"]: dict(row) for row in rows}
    children = {}
    for node in nodes.values():
        children.setdefault(node["parent_id"], []).append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (node["sort_order"] or 0, node["title"], node["id"]))

    ordered_scenes = []

    def visit(parent_id):
        for node in children.get(parent_id, []):
            if node["node_type"] == "SCENE":
                ordered_scenes.append(node)
            visit(node["id"])

    visit(book["id"])
    selected_index = next(
        (index for index, node in enumerate(ordered_scenes) if node["id"] == scene_id),
        None,
    )
    if selected_index is None:
        raise HTTPException(404, "Scene not found in manuscript order")

    remaining = READER_CONTEXT_CHAR_LIMIT
    context_blocks = []
    for node in reversed(ordered_scenes[:selected_index]):
        scene_text = html_to_text(node["content"] or "").strip()
        if not scene_text or remaining <= 0:
            continue
        separator_length = 2 if context_blocks else 0
        available_text = max(0, remaining - separator_length)
        excerpt = scene_text[-available_text:] if available_text else ""
        context_blocks.append(excerpt)
        remaining -= len(excerpt) + separator_length
    return "\n\n".join(reversed(context_blocks))


def _scene_revision_ref(conn, scene_id: str, content: str, plain_text: str) -> str:
    current = conn.execute(
        "SELECT content FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (scene_id,),
    ).fetchone()
    if current and html_to_text(current["content"] or "") == plain_text:
        return "CURRENT"
    matching_revision = conn.execute("""
        SELECT version_num FROM node_revisions
        WHERE node_id = ? AND content = ?
        ORDER BY version_num DESC LIMIT 1
    """, (scene_id, content)).fetchone()
    return f"V{matching_revision['version_num']}" if matching_revision else "UNSAVED"


def _store_reader_simulation(
    conn,
    *,
    simulation_id: str,
    scene_id: str,
    revision_ref: str,
    source_content_hash: str,
    analyzed_content_hash: str,
    intended_takeaway_hash: str,
    source_text: str,
    analyzed_text: str,
    reading_mode: str,
    reading_context: str,
    intended_takeaway: str,
    system_prompt: str,
    result_json: str,
    model_name: str,
    reused_from_id: str | None,
) -> sqlite3.Row:
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO reader_simulations
            (id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
             intended_takeaway_hash, prompt_version, source_text, analyzed_text,
             reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
             model_name, reused_from_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scene_id, source_content_hash, intended_takeaway_hash, prompt_version) DO NOTHING
        """, (
            simulation_id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
            intended_takeaway_hash, READER_SIMULATION_PROMPT_VERSION, source_text,
            analyzed_text, reading_mode, reading_context, intended_takeaway, system_prompt,
            result_json, model_name,
            reused_from_id, now,
        ))
    return conn.execute("""
        SELECT id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
               intended_takeaway_hash, prompt_version, source_text, analyzed_text,
               reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
               model_name, reused_from_id, created_at
        FROM reader_simulations
        WHERE scene_id = ? AND source_content_hash = ? AND intended_takeaway_hash = ?
          AND prompt_version = ?
    """, (
        scene_id, source_content_hash, intended_takeaway_hash, READER_SIMULATION_PROMPT_VERSION
    )).fetchone()


def _reader_loop_signal(simulations: list[dict]) -> dict:
    distinct_revisions = []
    seen_hashes = set()
    reading_mode = simulations[0].get("reading_mode", "scene") if simulations else "scene"
    for simulation in simulations:
        if simulation.get("reading_mode", "scene") != reading_mode:
            continue
        content_hash = simulation["analyzed_content_hash"]
        if content_hash not in seen_hashes:
            distinct_revisions.append(simulation)
            seen_hashes.add(content_hash)
        if len(distinct_revisions) == 3:
            break

    claim_sets = [
        {
            token
            for item in simulation["items"]
            for token in re.findall(r"\w+", item["narrative_claim"].lower())
        }
        for simulation in distinct_revisions
    ]
    similarity = None
    if len(claim_sets) == 3 and all(claim_sets):
        pair_scores = []
        for index, first in enumerate(claim_sets):
            for second in claim_sets[index + 1:]:
                pair_scores.append(len(first & second) / len(first | second))
        similarity = round(sum(pair_scores) / len(pair_scores), 2)

    active = similarity is not None and similarity >= 0.8
    return {
        "active": active,
        "similarity": similarity,
        "revisions_compared": len(distinct_revisions),
        "method": f"token Jaccard overlap across {reading_mode} AI observation text",
        "threshold": 0.8,
    }


