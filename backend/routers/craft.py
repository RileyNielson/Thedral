import asyncio
import json
import time
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
import ollama

from backend.config import STUDIO_MODEL, LLM_OPTIONS
from backend.database import get_db
from backend.socratic import elevate_prose_diagnosis, get_socratic_lesson
from backend.telemetry import classify_sentence_energetics, classify_paragraph_energetics

router = APIRouter(tags=["Craft"])

class ElevateRequest(BaseModel):
    passage: str
    surrounding: str = ""
    scene_id: str | None = None

class XRayRequest(BaseModel):
    text: str

@router.post("/api/craft/elevate")
def elevate_prose(payload: ElevateRequest):
    critique = elevate_prose_diagnosis(
        passage=payload.passage,
        surrounding=payload.surrounding,
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
    paragraphs = classify_paragraph_energetics(payload.text)
    flat_sentences = [s for p in paragraphs for s in p]
    return {
        "paragraphs": paragraphs,
        "sentences": flat_sentences
    }

class ScanDisclosureRequest(BaseModel):
    scene_id: str
    text: str

class AddDisclosureRequest(BaseModel):
    scene_id: str
    disclosure_type: str
    narrative_claim: str
    clue_evidence: str = ""

@router.get("/api/disclosures/scene/{scene_id}")
def get_scene_disclosures(scene_id: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, disclosure_type, narrative_claim, clue_evidence, target_reveal_ch, status 
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

    prompt_content = "Scene Text:\n" + str(payload.text[:3500])
    try:
        resp = await asyncio.to_thread(
            ollama.chat,
            model=STUDIO_MODEL,
            messages=[
                {"role": "system", "content": "Analyze this scene prose and categorize the information flow to the READER into strict JSON:\n{\n  \"direct\": [\"Direct factual statements\"],\n  \"inferred\": [{\"claim\": \"Subtext\", \"clue\": \"Quote\"}],\n  \"delayed\": [\"Open dramatic mysteries\"]\n}\nOUTPUT STRICT JSON ONLY."},
                {"role": "user", "content": prompt_content}
            ],
            format="json",
            options=LLM_OPTIONS
        )
        data = json.loads(resp["message"]["content"])
    except Exception as e:
        return {"status": "error", "message": str(e), "disclosures": []}

    conn = get_db()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        c = conn.cursor()
        for d in data.get("direct", []):
            claim = d if isinstance(d, str) else d.get("claim", "")
            if claim:
                c.execute("""
                    INSERT INTO reader_disclosures 
                    (scene_id, disclosure_type, narrative_claim, clue_evidence, status, created_at)
                    VALUES (?, 'DIRECT', ?, '', 'CONFIRMED', ?)
                """, (payload.scene_id, claim, now))

        for inf in data.get("inferred", []):
            claim = inf.get("claim", "") if isinstance(inf, dict) else str(inf)
            clue = inf.get("clue", "") if isinstance(inf, dict) else ""
            if claim:
                c.execute("""
                    INSERT INTO reader_disclosures 
                    (scene_id, disclosure_type, narrative_claim, clue_evidence, status, created_at)
                    VALUES (?, 'INFERRED', ?, ?, 'ACTIVE', ?)
                """, (payload.scene_id, claim, clue, now))

        for del_q in data.get("delayed", []):
            claim = del_q if isinstance(del_q, str) else del_q.get("question", "")
            if claim:
                c.execute("""
                    INSERT INTO reader_disclosures 
                    (scene_id, disclosure_type, narrative_claim, clue_evidence, status, created_at)
                    VALUES (?, 'DELAYED', ?, '', 'ACTIVE', ?)
                """, (payload.scene_id, claim, now))

    c = conn.cursor()
    c.execute("SELECT * FROM reader_disclosures WHERE scene_id = ? ORDER BY id ASC", (payload.scene_id,))
    updated_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    return {"status": "success", "disclosures": updated_rows}

@router.delete("/api/disclosures/{item_id}")
def delete_disclosure(item_id: int):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM reader_disclosures WHERE id = ?", (item_id,))
    conn.close()
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