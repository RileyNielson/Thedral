import json
import re
import time
from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import get_db
from backend.config import STUDIO_MODEL, LLM_OPTIONS
import ollama

router = APIRouter(tags=["Lore & Lexicon"])

class LoreRule(BaseModel):
    term: str
    category: str = "LORE"
    rule_definition: str
    pronunciation: str = ""

class AskRequest(BaseModel):
    question: str

class ExtractLoreRequest(BaseModel):
    scene_text: str

class AuditLoreRequest(BaseModel):
    scene_text: str

@router.get("/api/lore")
def get_all_lore():
    """Fetches the Living Style Sheet and Worldbuilding Axioms."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM style_sheet ORDER BY category ASC, term ASC")
    rules = [dict(r) for r in c.fetchall()]
    conn.close()
    return rules

@router.post("/api/lore")
def add_lore_rule(payload: LoreRule):
    """Adds or updates a rule in the Living Style Sheet."""
    conn = get_db()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO style_sheet (term, category, rule_definition, pronunciation, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.term.strip(), payload.category.upper(), payload.rule_definition.strip(), payload.pronunciation.strip(), now)
        )
    conn.close()
    return {"status": "saved"}

@router.delete("/api/lore/{term}")
def delete_lore_rule(term: str):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM style_sheet WHERE term = ?", (term,))
    conn.close()
    return {"status": "deleted"}

@router.post("/api/ask")
def ask_the_universe(payload: AskRequest):
    """Answers a natural language question using FTS5 manuscript retrieval (Local RAG)."""
    q = payload.question.strip()
    if not q: return {"answer": "Ask a question."}

    stop_words = {"what", "where", "who", "why", "when", "how", "did", "is", "the", "a", "an", "and", "in", "on", "of"}
    keywords = [w for w in re.sub(r"[^\w\s]", "", q.lower()).split() if w not in stop_words]
    
    if not keywords: return {"answer": "Please provide more specific nouns to search."}

    conn = get_db()
    c = conn.cursor()
    match_query = " OR ".join([f"{k}*" for k in keywords])
    
    c.execute("""
        SELECT b.title, f.content 
        FROM binder_fts f 
        JOIN binder_nodes b ON f.node_id = b.id 
        WHERE binder_fts MATCH ? LIMIT 10
    """, (match_query,))
    results = c.fetchall()
    conn.close()

    if not results:
        return {"answer": "I cannot find any references to that in the current manuscript."}

    context_blocks = chr(10).join([f"--- Excerpt from {r['title']} ---\n{r['content'][:1000]}" for r in results])
    
    prompt = (
        f"You are the Librarian of this fictional universe.\n"
        f"Answer the author's question using ONLY the provided manuscript excerpts below.\n"
        f"If the answer is not contained in the excerpts, say 'The manuscript does not currently specify this.'\n"
        f"Be concise and factual.\n\n"
        f"MANUSCRIPT EXCERPTS:\n{context_blocks}\n\n"
        f"AUTHOR'S QUESTION: {q}\nANSWER:"
    )

    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": prompt}], options=LLM_OPTIONS)
        return {"answer": resp["message"]["content"].strip()}
    except Exception as e:
        return {"answer": f"Librarian offline: {e}"}

@router.post("/api/lore/extract")
def auto_extract_lore(payload: ExtractLoreRequest):
    """Scans scene prose to propose new worldbuilding rules and lexicon terms."""
    if not payload.scene_text or len(payload.scene_text) < 100:
        return {"proposed_lore": []}

    prompt = (
        "You are a Worldbuilding Lexicon Extractor.\n"
        "Read the scene below and identify any NEW proper nouns, factions, magic systems, unique technology, or distinct locations.\n"
        "Ignore standard conversational words and established main characters.\n\n"
        "Output a STRICT JSON array of objects.\n[\n  {\n    \"term\": \"The precise name of the lore element\",\n    \"category\": \"LORE\" | \"LOCATION\" | \"MAGIC\" | \"FACTION\",\n    \"rule_definition\": \"A 1-sentence definition based purely on the text.\"\n  }\n]"
    )
    
    try:
        resp = ollama.chat(
            model=STUDIO_MODEL, 
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": payload.scene_text[:3500]}
            ], 
            format="json", 
            options=LLM_OPTIONS
        )
        data = json.loads(resp["message"]["content"])
        if isinstance(data, dict):
            data = data.get("lore", data.get("terms", []))
        return {"proposed_lore": data if isinstance(data, list) else []}
    except Exception as e:
        return {"proposed_lore": []}

@router.post("/api/lore/audit")
def audit_scene_lore(payload: AuditLoreRequest):
    """Cross-examines the active scene prose against the established Living Lexicon for contradictions."""
    if not payload.scene_text or len(payload.scene_text.strip()) < 50:
        return {"discrepancies": []}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT term, category, rule_definition FROM style_sheet WHERE category IN ('LORE', 'MAGIC', 'SPELLING')")
    rules = c.fetchall()
    conn.close()

    if not rules:
        return {"discrepancies": []}

    rules_text = chr(10).join([f"- [{r['category']}] {r['term']}: {r['rule_definition']}" for r in rules])

    prompt = (
        "You are an uncompromising Worldbuilding Continuity Auditor.\n"
        "Cross-examine the author's scene text against the ESTABLISHED UNIVERSE RULES below.\n"
        "Your only job is to find hard contradictions, broken magic systems, or misspelled lore terms.\n\n"
        f"ESTABLISHED UNIVERSE RULES:\n{rules_text}\n\n"
        "OUTPUT STRICT JSON ONLY. If no rules are broken, return an empty array.\n"
        "{\n  \"discrepancies\": [\n    {\n      \"rule_broken\": \"The name of the rule or term\",\n      \"violation\": \"The exact quote from the scene that breaks it\",\n      \"explanation\": \"Why it is a contradiction\"\n    }\n  ]\n}"
    )

    try:
        resp = ollama.chat(
            model=STUDIO_MODEL, 
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Scene Text:\n{payload.scene_text[:4000]}"}
            ],
            format="json",
            options=LLM_OPTIONS
        )
        data = json.loads(resp["message"]["content"])
        return {"discrepancies": data.get("discrepancies", [])}
    except Exception as e:
        return {"discrepancies": [{"rule_broken": "Engine Offline", "violation": "", "explanation": str(e)}]}