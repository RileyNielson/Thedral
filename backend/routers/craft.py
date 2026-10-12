import asyncio
import hashlib
import json
import sqlite3
import time
import uuid
import re
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import STUDIO_MODEL, LLM_OPTIONS, ENABLE_AI
from backend.database import get_db
from backend.socratic import elevate_prose_diagnosis, get_socratic_lesson
from backend.telemetry import classify_sentence_energetics, classify_paragraph_energetics
from backend.text_utils import html_to_text

router = APIRouter(tags=["Craft"])
READER_SIMULATION_PROMPT_VERSION = "first-read-v4"
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

class ElevateRequest(BaseModel):
    passage: str
    surrounding: str = ""
    scene_id: str | None = None

class XRayRequest(BaseModel):
    text: str
    staccato_threshold: int = 9
    expansive_threshold: int = 22
    clutter_sensitivity: int = 2

@router.post("/api/craft/elevate")
def elevate_prose(payload: ElevateRequest):
    critique = elevate_prose_diagnosis(
        passage=html_to_text(payload.passage),
        surrounding=html_to_text(payload.surrounding),
        scene_id=payload.scene_id
    )
    
    critique_id = f"crit_{uuid.uuid4().hex[:8]}"
    if payload.scene_id:
        conn = get_db()
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with conn:
            conn.execute("""
                INSERT INTO editorial_critiques 
                (id, scene_id, passage_text, critique_text, status, created_at)
                VALUES (?, ?, ?, ?, 'OPEN', ?)
            """, (critique_id, payload.scene_id, payload.passage[:300], critique, now))
        conn.close()

    return {"critique": critique, "critique_id": critique_id}

@router.post("/api/craft/xray")
def get_craft_xray(payload: XRayRequest):
    """Returns multi-lens paragraph data with zero document scrambling."""
    thresholds = {
        "staccato_threshold": payload.staccato_threshold,
        "expansive_threshold": payload.expansive_threshold,
        "clutter_sensitivity": payload.clutter_sensitivity,
    }
    paragraphs = classify_paragraph_energetics(html_to_text(payload.text), thresholds)
    flat_sentences = [s for p in paragraphs for s in p]
    return {
        "paragraphs": paragraphs,
        "sentences": flat_sentences,
        "thresholds": thresholds
    }

class ScanDisclosureRequest(BaseModel):
    scene_id: str
    text: str
    reading_mode: Literal["scene", "sequential"] = "scene"

class AddDisclosureRequest(BaseModel):
    scene_id: str
    disclosure_type: str
    narrative_claim: str
    clue_evidence: str = ""


class ReaderFeedbackCreate(BaseModel):
    scene_id: str
    revision_ref: str = "CURRENT"
    reader_label: str = Field(default="", max_length=80)
    confusion_rating: int | None = Field(default=None, ge=1, le=5)
    engagement_rating: int | None = Field(default=None, ge=1, le=5)
    tension_rating: int | None = Field(default=None, ge=1, le=5)
    empathy_rating: int | None = Field(default=None, ge=1, le=5)
    response: str = Field(default="", max_length=4000)


class AuthorHorizonNote(BaseModel):
    scene_id: str
    disclosure_type: str
    narrative_claim: str = Field(min_length=1, max_length=1000)
    source_excerpt: str = Field(default="", max_length=1000)
    clue_evidence: str = Field(default="", max_length=1000)


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


@router.get("/api/disclosures/scene/{scene_id}")
def get_scene_disclosures(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, disclosure_type, narrative_claim, clue_evidence, source_excerpt, confidence, source, target_reveal_ch, status
        FROM reader_disclosures 
        WHERE scene_id = ? 
        ORDER BY id ASC
    """, (scene_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@router.post("/api/disclosures/scan")
async def scan_scene_disclosures(payload: ScanDisclosureRequest):
    if not payload.text or len(payload.text.strip()) < 30:
        return {"status": "empty", "disclosures": []}

    conn = get_db()
    scene = conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (payload.scene_id,),
    ).fetchone()
    conn.close()
    if not scene:
        raise HTTPException(404, "Scene not found")

    source_text = html_to_text(payload.text)
    intended_takeaway = ""
    analyzed_text = source_text[:3500]
    takeaway_hash = hashlib.sha256(intended_takeaway.encode("utf-8")).hexdigest()
    conn = get_db()
    reading_context = (
        _preceding_scene_context(conn, payload.scene_id)
        if payload.reading_mode == "sequential"
        else ""
    )
    analyzed_hash = hashlib.sha256(
        json.dumps(
            [payload.reading_mode, reading_context, analyzed_text],
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    input_hash = hashlib.sha256(
        json.dumps(
            [payload.reading_mode, reading_context, source_text],
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    cached = conn.execute("""
        SELECT id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
               intended_takeaway_hash, prompt_version, source_text, analyzed_text,
               reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
               model_name, reused_from_id, created_at
        FROM reader_simulations
        WHERE scene_id = ? AND source_content_hash = ? AND intended_takeaway_hash = ?
          AND prompt_version = ?
    """, (
        payload.scene_id, input_hash, takeaway_hash, READER_SIMULATION_PROMPT_VERSION
    )).fetchone()
    if cached:
        conn.close()
        return {
            "status": "success",
            "simulation": _serialize_simulation(cached),
            "reused": True,
            "warnings": [],
        }
    reusable = conn.execute("""
        SELECT id, system_prompt, result_json, model_name
        FROM reader_simulations
        WHERE scene_id = ? AND analyzed_content_hash = ? AND intended_takeaway_hash = ?
          AND prompt_version = ? AND model_name = ?
        ORDER BY created_at DESC, rowid DESC LIMIT 1
    """, (
        payload.scene_id, analyzed_hash, takeaway_hash,
        READER_SIMULATION_PROMPT_VERSION, STUDIO_MODEL,
    )).fetchone()
    conn.close()

    if reusable:
        system_prompt = reusable["system_prompt"]
        result_json = reusable["result_json"]
        model_name = reusable["model_name"]
        reused_from_id = reusable["id"]
        warnings = []
    elif not ENABLE_AI:
        return {"status": "error", "message": "Reader simulation unavailable (local AI is disabled)."}
    else:
        if reading_context:
            prompt_content = (
                "Recent preceding manuscript text (a limited context window; no author notes):\n"
                + reading_context
                + "\n\nCurrent scene excerpt:\n"
                + analyzed_text
            )
        elif payload.reading_mode == "sequential":
            prompt_content = (
                "No earlier scenes with saved text precede this scene in manuscript order.\n\n"
                "Current scene excerpt:\n" + analyzed_text
            )
        else:
            prompt_content = "Current scene excerpt (the only manuscript text supplied):\n" + analyzed_text
        def find_evidence(quote: str) -> tuple[str, str]:
            excerpt = _quoted_excerpt(analyzed_text, quote)
            if excerpt:
                return excerpt, "current_scene"
            excerpt = _quoted_excerpt(reading_context, quote)
            return (excerpt, "prior_context") if excerpt else ("", "")

        try:
            import ollama
            resp = await asyncio.to_thread(
                ollama.chat,
                model=STUDIO_MODEL,
                messages=[
                    {"role": "system", "content": READER_SIMULATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_content}
                ],
                format="json",
                options=LLM_OPTIONS
            )
            data = json.loads(resp["message"]["content"])
        except Exception as e:
            return {"status": "error", "message": f"Reader simulation failed: {e}"}

        if not isinstance(data, dict):
            return {"status": "error", "message": "Reader simulation returned an invalid response object."}
        disclosure_types = ("direct", "inferred", "delayed", "friction", "revision_focus")
        for disclosure_type in disclosure_types:
            if disclosure_type not in data:
                data[disclosure_type] = []
            elif not isinstance(data[disclosure_type], list):
                return {
                    "status": "error",
                    "message": f"Reader simulation returned an invalid {disclosure_type} list.",
                }

        warnings = []
        items = []
        for disclosure_type in disclosure_types:
            for item in data[disclosure_type]:
                if not isinstance(item, dict):
                    warnings.append(f"Skipped an ungrounded {disclosure_type} item.")
                    continue
                claim = str(item.get("claim", "")).strip()
                evidence, evidence_source = find_evidence(str(item.get("evidence", "")))
                if not claim or not evidence:
                    warnings.append(f"Skipped a {disclosure_type} item without a matching text excerpt.")
                    continue
                items.append({
                    "disclosure_type": disclosure_type.upper(),
                    "narrative_claim": claim,
                    "source_excerpt": evidence,
                    "evidence_source": evidence_source,
                })
        experience = data.get("reader_experience", {})
        if not isinstance(experience, dict):
            warnings.append("The AI reader-experience estimate had an invalid structure.")
            experience = {}
        for dimension, (disclosure_type, estimate_key) in READER_EXPERIENCE_DIMENSIONS.items():
            observations = experience.get(dimension, [])
            if not isinstance(observations, list):
                warnings.append(f"Skipped reader-experience estimates with an invalid {dimension} list.")
                continue
            for observation in observations[:3]:
                if not isinstance(observation, dict):
                    warnings.append(f"Skipped an invalid {dimension} estimate.")
                    continue
                evidence, evidence_source = find_evidence(str(observation.get("evidence", "")))
                estimate = str(observation.get(estimate_key, "")).strip()
                cause = str(observation.get("cause", "")).strip()
                level = observation.get("level")
                if (
                    not evidence
                    or not estimate
                    or not cause
                    or isinstance(level, bool)
                    or not isinstance(level, int)
                    or not 1 <= level <= 5
                ):
                    warnings.append(f"Skipped an ungrounded {dimension} estimate.")
                    continue
                items.append({
                    "disclosure_type": disclosure_type,
                    "narrative_claim": estimate,
                    "source_excerpt": evidence,
                    "evidence_source": evidence_source,
                    "moment": str(observation.get("moment", "")).strip(),
                    "cause": cause,
                    "level": level,
                })
        system_prompt = READER_SIMULATION_SYSTEM_PROMPT
        result_json = json.dumps(items)
        model_name = STUDIO_MODEL
        reused_from_id = None

    conn = get_db()
    revision_ref = _scene_revision_ref(conn, payload.scene_id, payload.text, source_text)
    simulation_id = f"sim_{uuid.uuid4().hex}"
    saved = _store_reader_simulation(
        conn,
        simulation_id=simulation_id,
        scene_id=payload.scene_id,
        revision_ref=revision_ref,
        source_content_hash=input_hash,
        analyzed_content_hash=analyzed_hash,
        intended_takeaway_hash=takeaway_hash,
        source_text=source_text,
        analyzed_text=analyzed_text,
        reading_mode=payload.reading_mode,
        reading_context=reading_context,
        intended_takeaway=intended_takeaway,
        system_prompt=system_prompt,
        result_json=result_json,
        model_name=model_name,
        reused_from_id=reused_from_id,
    )
    conn.close()

    return {
        "status": "success",
        "simulation": _serialize_simulation(saved),
        "reused": reused_from_id is not None or saved["id"] != simulation_id,
        "warnings": warnings,
    }


@router.get("/api/reader-simulations/scene/{scene_id}")
def get_scene_reader_simulations(scene_id: str):
    conn = get_db()
    if not conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (scene_id,),
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Scene not found")
    rows = conn.execute("""
        SELECT id, scene_id, revision_ref, source_content_hash, analyzed_content_hash,
               intended_takeaway_hash, prompt_version, source_text, analyzed_text,
               reading_mode, reading_context, intended_takeaway, system_prompt, result_json,
               model_name, reused_from_id, created_at
        FROM reader_simulations
        WHERE scene_id = ?
        ORDER BY created_at DESC, rowid DESC
    """, (scene_id,)).fetchall()
    conn.close()
    simulations = [_serialize_simulation(row) for row in rows]
    return {
        "simulations": simulations,
        "loop_signal": _reader_loop_signal(simulations),
    }


@router.post("/api/disclosures/author-note")
def add_author_horizon_note(payload: AuthorHorizonNote):
    allowed_types = {"INTENDED", "DIRECT", "INFERRED", "DELAYED"}
    if payload.disclosure_type not in allowed_types:
        raise HTTPException(400, "Unsupported Reader Horizon note type")
    conn = get_db()
    scene = conn.execute(
        "SELECT id FROM binder_nodes WHERE id = ? AND node_type = 'SCENE'",
        (payload.scene_id,),
    ).fetchone()
    if not scene:
        conn.close()
        raise HTTPException(404, "Scene not found")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO reader_disclosures
            (scene_id, disclosure_type, narrative_claim, clue_evidence, source_excerpt, confidence, source, status, created_at)
            VALUES (?, ?, ?, ?, ?, NULL, 'AUTHOR', 'ACTIVE', ?)
        """, (
            payload.scene_id, payload.disclosure_type, payload.narrative_claim.strip(),
            payload.clue_evidence.strip(), payload.source_excerpt.strip(), now,
        ))
    conn.close()
    return {"status": "created"}

@router.delete("/api/disclosures/{item_id}")
def delete_disclosure(item_id: int):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM reader_disclosures WHERE id = ?", (item_id,))
    conn.close()
    return {"status": "deleted"}


@router.get("/api/reader-feedback/book/{book_id}")
def get_book_reader_feedback(book_id: str):
    conn = get_db()
    if not conn.execute(
        "SELECT 1 FROM binder_nodes WHERE id = ? AND node_type = 'BOOK'",
        (book_id,),
    ).fetchone():
        conn.close()
        raise HTTPException(404, "Manuscript not found")
    rows = conn.execute("""
        SELECT f.id, f.scene_id, f.revision_ref, f.reader_label, f.confusion_rating,
               f.engagement_rating, f.tension_rating, f.empathy_rating, f.response, f.created_at,
               s.title AS scene_title, ch.title AS chapter_title
        FROM reader_feedback f
        JOIN binder_nodes s ON s.id = f.scene_id AND s.node_type = 'SCENE'
        JOIN binder_nodes ch ON ch.id = s.parent_id AND ch.node_type = 'CHAPTER'
        WHERE f.book_id = ?
        ORDER BY ch.sort_order, s.sort_order, f.created_at, f.id
    """, (book_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.get("/api/reader-feedback/scene/{scene_id}")
def get_scene_reader_feedback(scene_id: str):
    conn = get_db()
    rows = conn.execute("""
        SELECT id, revision_ref, reader_label, confusion_rating, engagement_rating,
               tension_rating, empathy_rating, response, created_at
        FROM reader_feedback WHERE scene_id = ?
        ORDER BY created_at DESC, id DESC
    """, (scene_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@router.post("/api/reader-feedback")
def create_reader_feedback(payload: ReaderFeedbackCreate):
    revision_ref = payload.revision_ref.strip().upper()
    if revision_ref != "CURRENT" and not re.fullmatch(r"V[1-9]\d*", revision_ref):
        raise HTTPException(400, "Revision must be CURRENT or a saved version such as v3")
    if not any((
        payload.confusion_rating is not None,
        payload.engagement_rating is not None,
        payload.tension_rating is not None,
        payload.empathy_rating is not None,
        payload.response.strip(),
    )):
        raise HTTPException(400, "Add at least one rating or written response")
    conn = get_db()
    scene = conn.execute("""
        SELECT s.id, ch.parent_id AS book_id
        FROM binder_nodes s JOIN binder_nodes ch ON ch.id = s.parent_id
        WHERE s.id = ? AND s.node_type = 'SCENE' AND ch.node_type = 'CHAPTER'
    """, (payload.scene_id,)).fetchone()
    if not scene:
        conn.close()
        raise HTTPException(404, "Scene not found")
    if revision_ref != "CURRENT":
        version_num = int(revision_ref[1:])
        if not conn.execute(
            "SELECT 1 FROM node_revisions WHERE node_id = ? AND version_num = ?",
            (payload.scene_id, version_num),
        ).fetchone():
            conn.close()
            raise HTTPException(400, "That saved scene revision does not exist")
    feedback_id = f"reader_{uuid.uuid4().hex}"
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute("""
            INSERT INTO reader_feedback
            (id, book_id, scene_id, revision_ref, reader_label, confusion_rating, engagement_rating,
             tension_rating, empathy_rating, response, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            feedback_id, scene["book_id"], payload.scene_id, revision_ref, payload.reader_label.strip(),
            payload.confusion_rating, payload.engagement_rating, payload.tension_rating,
            payload.empathy_rating, payload.response.strip(), now,
        ))
    conn.close()
    return {"id": feedback_id, "status": "saved"}


@router.delete("/api/reader-feedback/{feedback_id}")
def delete_reader_feedback(feedback_id: str):
    conn = get_db()
    with conn:
        result = conn.execute("DELETE FROM reader_feedback WHERE id = ?", (feedback_id,))
    conn.close()
    if not result.rowcount:
        raise HTTPException(404, "Reader feedback entry not found")
    return {"status": "deleted"}

class CritiqueStatusUpdate(BaseModel):
    status: str

@router.get("/api/critiques/scene/{scene_id}")
def get_scene_critiques(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, scene_id, passage_text, critique_text, status, created_at, resolved_at 
        FROM editorial_critiques 
        WHERE scene_id = ? 
        ORDER BY created_at DESC
    """, (scene_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

@router.put("/api/critiques/{critique_id}/status")
def update_critique_status(critique_id: str, payload: CritiqueStatusUpdate):
    conn = get_db()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    resolved_time = now if payload.status == "ADDRESSED" else None
    with conn:
        conn.execute("""
            UPDATE editorial_critiques 
            SET status = ?, resolved_at = ? 
            WHERE id = ?
        """, (payload.status, resolved_time, critique_id))
    conn.close()
    return {"status": "updated"}

class TutorRequest(BaseModel):
    question: str
    context: str = ""

@router.post("/api/craft/teach")
def ask_socratic_tutor(payload: TutorRequest):
    lesson = get_socratic_lesson(payload.question, payload.context)
    return {"lesson": lesson}
