import json
import re
import time
from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import get_db
from backend.text_utils import html_to_text
from backend.config import STUDIO_MODEL, LLM_OPTIONS, ENABLE_AI
from backend.ai_helper import (
    ai_meta, deterministic_brief, find_name_candidates, relevant_rules, spelling_findings,
)
from backend.entity_names import entity_name_forms
from backend.wiktionary_lexicon import english_words, get_lexicon_status

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
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM style_sheet ORDER BY category ASC, term ASC")
    rules = [dict(r) for r in c.fetchall()]
    conn.close()
    return rules

@router.post("/api/lore")
def add_lore_rule(payload: LoreRule):
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
        return {"answer": "I cannot find any references to that in the current manuscript.", **ai_meta(False)}

    context_blocks = chr(10).join([f"--- Excerpt from {r['title']} ---\n{html_to_text(r['content'])[:1000]}" for r in results])
    
    if not ENABLE_AI:
        return {"answer": f"[Text search only, no AI] Matching manuscript excerpts:\n\n{context_blocks}", **ai_meta(False)}

    prompt = (
        f"You are the Librarian of this fictional universe.\n"
        f"Answer the author's question using ONLY the provided manuscript excerpts below.\n"
        f"If the answer is not contained in the excerpts, say 'The manuscript does not currently specify this.'\n"
        f"Be concise and factual.\n\n"
        f"MANUSCRIPT EXCERPTS:\n{context_blocks}\n\n"
        f"AUTHOR'S QUESTION: {q}\nANSWER:"
    )

    try:
        import ollama
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": prompt}], options=LLM_OPTIONS)
        return {"answer": resp["message"]["content"].strip(), **ai_meta(True)}
    except Exception as e:
        return {"answer": f"[AI unavailable, showing text search results]\n\n{context_blocks}", **ai_meta(False, str(e))}

def _known_terms(conn) -> set[str]:
    known = set()
    for row in conn.execute("SELECT name, aliases FROM canonical_entities"):
        for form in entity_name_forms(row["name"], row["aliases"]):
            known.update(part.casefold() for part in form.split())
    for row in conn.execute("SELECT term FROM style_sheet"):
        known.update(part.casefold() for part in row["term"].split())
    return known


@router.post("/api/lore/extract")
def auto_extract_lore(payload: ExtractLoreRequest):
    """Text scan finds invented names first; AI (when on) only adds definitions and other lore."""
    scene_text = html_to_text(payload.scene_text)
    if len(scene_text) < 100:
        return {"proposed_lore": [], **ai_meta(False)}

    conn = get_db()
    try:
        known = _known_terms(conn)
        brief = deterministic_brief(scene_text, conn)
    finally:
        conn.close()

    dictionary = english_words if get_lexicon_status()["available"] else None
    names = find_name_candidates(scene_text, known, dictionary)
    proposed = [
        {"term": n, "category": "LORE", "rule_definition": "", "source": "text-scan"}
        for n in names[:8]
    ]

    if not ENABLE_AI:
        return {"proposed_lore": proposed, **ai_meta(False)}

    prompt = (
        "You are a Worldbuilding Lexicon Extractor helping an author. A text scan has already found these "
        f"candidate invented terms: {', '.join(names) or 'none'}.\n"
        "Write a 1-sentence definition for each candidate that the scene actually explains, and add any other NEW factions, "
        "magic systems, unique technology or distinct locations the scan could not see. Skip ordinary words and known cast.\n\n"
        f"{brief}\n\n"
        "Output a STRICT JSON array of objects.\n[\n  {\n    \"term\": \"The precise name\",\n    \"category\": \"LORE\" | \"LOCATION\" | \"MAGIC\" | \"FACTION\",\n    \"rule_definition\": \"A 1-sentence definition based purely on the text.\"\n  }\n]"
    )

    try:
        import ollama
        resp = ollama.chat(
            model=STUDIO_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": scene_text[:3500]}
            ],
            format="json",
            options=LLM_OPTIONS
        )
        data = json.loads(resp["message"]["content"])
        if isinstance(data, dict):
            data = data.get("lore", data.get("terms", []))
        ai_items = [d for d in data if isinstance(d, dict) and d.get("term")] if isinstance(data, list) else []
        by_term = {p["term"].casefold(): p for p in proposed}
        for item in ai_items:
            key = str(item["term"]).casefold()
            if key in known:
                continue
            item["source"] = "ai"
            if key in by_term:
                by_term[key].update(item)
            else:
                proposed.append(item)
                by_term[key] = item
        return {"proposed_lore": proposed, **ai_meta(True)}
    except Exception as e:
        return {"proposed_lore": proposed, **ai_meta(False, str(e))}

@router.post("/api/lore/audit")
def audit_scene_lore(payload: AuditLoreRequest):
    """Misspellings of lore terms are caught by string matching; AI (when on) judges contradictions."""
    scene_text = html_to_text(payload.scene_text)
    if len(scene_text) < 50:
        return {"discrepancies": [], **ai_meta(False)}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT term, category, rule_definition FROM style_sheet WHERE category IN ('LORE', 'MAGIC', 'SPELLING')")
    rules = [dict(r) for r in c.fetchall()]
    conn.close()

    if not rules:
        return {"discrepancies": [], **ai_meta(False)}

    findings = spelling_findings(rules, scene_text)

    if not ENABLE_AI:
        return {"discrepancies": findings, **ai_meta(False)}

    chosen = relevant_rules(rules, scene_text)
    rules_text = chr(10).join([f"- [{r['category']}] {r['term']}: {r['rule_definition']}" for r in chosen])
    already = ", ".join(f['violation'] for f in findings) or "none"

    prompt = (
        "You are a Worldbuilding Continuity Auditor assisting an author.\n"
        "Cross-examine the scene text against the ESTABLISHED UNIVERSE RULES below.\n"
        "Only report hard contradictions or broken magic systems. Misspellings were already found by a text scan "
        f"(already reported: {already}); do not repeat them. Quote the exact violating text.\n\n"
        f"ESTABLISHED UNIVERSE RULES:\n{rules_text}\n\n"
        "OUTPUT STRICT JSON ONLY. If no rules are broken, return an empty array.\n"
        "{\n  \"discrepancies\": [\n    {\n      \"rule_broken\": \"The name of the rule or term\",\n      \"violation\": \"The exact quote from the scene that breaks it\",\n      \"explanation\": \"Why it is a contradiction\"\n    }\n  ]\n}"
    )

    try:
        import ollama
        resp = ollama.chat(
            model=STUDIO_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Scene Text:\n{scene_text[:4000]}"}
            ],
            format="json",
            options=LLM_OPTIONS
        )
        data = json.loads(resp["message"]["content"])
        ai_items = [d for d in data.get("discrepancies", []) if isinstance(d, dict)]
        for item in ai_items:
            item["source"] = "ai"
        return {"discrepancies": findings + ai_items, **ai_meta(True)}
    except Exception as e:
        return {"discrepancies": findings, **ai_meta(False, str(e))}
