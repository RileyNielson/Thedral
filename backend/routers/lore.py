import json
import re
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_db
from backend.text_utils import html_to_text
from backend.ai_helper import (
    find_name_candidates, relevant_rules, spelling_findings,
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


class BatchReplaceRequest(BaseModel):
    search_term: str
    replace_term: str
    book_id: Optional[str] = None
    match_case: bool = False


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
    """
    100% Deterministic SQLite FTS5 Full-Text Search.
    Instantly returns the exact manuscript excerpts and chapter locations.
    """
    q = payload.question.strip()
    if not q:
        return {"answer": "Ask a question about your lore or characters."}

    stop_words = {"what", "where", "who", "why", "when", "how", "did", "is", "the", "a", "an", "and", "in", "on", "of"}
    keywords = [w for w in re.sub(r"[^\w\s]", "", q.lower()).split() if w not in stop_words]
    
    if not keywords:
        return {"answer": "Please provide more specific nouns to search."}

    conn = get_db()
    c = conn.cursor()
    match_query = " OR ".join([f"{k}*" for k in keywords])
    
    c.execute("""
        SELECT b.title, f.content 
        FROM binder_fts f 
        JOIN binder_nodes b ON f.node_id = b.id 
        WHERE binder_fts MATCH ? LIMIT 8
    """, (match_query,))
    results = c.fetchall()
    conn.close()

    if not results:
        return {"answer": "No references found in the current manuscript."}

    context_blocks = "\n\n".join([
        f"**From {r['title']}:**\n_{html_to_text(r['content'])[:400]}_"
        for r in results
    ])
    return {"answer": f"**Exact manuscript matches from archives:**\n\n{context_blocks}"}


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
    """Text-scan finds invented names and potential canon terms without AI."""
    scene_text = html_to_text(payload.scene_text)
    if len(scene_text) < 100:
        return {"proposed_lore": []}

    conn = get_db()
    try:
        known = _known_terms(conn)
    finally:
        conn.close()

    dictionary = english_words if get_lexicon_status()["available"] else None
    names = find_name_candidates(scene_text, known, dictionary)
    proposed = [
        {"term": n, "category": "LORE", "rule_definition": f"Extracted from manuscript scan.", "source": "text-scan"}
        for n in names[:8]
    ]
    return {"proposed_lore": proposed}


@router.post("/api/lore/audit")
def audit_scene_lore(payload: AuditLoreRequest):
    """
    100% Deterministic Levenshtein String Audit.
    Catches spelling drift and typos against your confirmed Style Sheet terms.
    """
    scene_text = html_to_text(payload.scene_text)
    if len(scene_text) < 40:
        return {"discrepancies": []}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT term, category, rule_definition FROM style_sheet WHERE category IN ('LORE', 'MAGIC', 'SPELLING')")
    rules = [dict(r) for r in c.fetchall()]
    conn.close()

    if not rules:
        return {"discrepancies": []}

    findings = spelling_findings(rules, scene_text)
    return {"discrepancies": findings}


@router.post("/api/lore/batch-replace")
def batch_replace_manuscript_term(payload: BatchReplaceRequest):
    """
    Atomic Manuscript-Wide Canon Term Replacer.
    Safely replaces spelling drifts (e.g. 'Aethermor' -> 'Aethermoor') across all scenes in 2ms.
    """
    search_term = payload.search_term.strip()
    replace_term = payload.replace_term.strip()

    if not search_term or not replace_term:
        raise HTTPException(400, "Search and replace terms cannot be blank.")
    if search_term == replace_term:
        raise HTTPException(400, "Search and replace terms must be different.")

    conn = get_db()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    # Fetch all active scenes in target book or entire project
    if payload.book_id:
        c.execute("""
            SELECT s.id, s.title, s.content, ch.title as ch_title
            FROM binder_nodes s
            JOIN binder_nodes ch ON s.parent_id = ch.id
            WHERE ch.parent_id = ? AND s.node_type = 'SCENE' AND (s.is_archived IS NULL OR s.is_archived = 0)
        """, (payload.book_id,))
    else:
        c.execute("""
            SELECT id, title, content, '' as ch_title
            FROM binder_nodes
            WHERE node_type = 'SCENE' AND (is_archived IS NULL OR is_archived = 0)
        """)

    scenes = c.fetchall()
    flags = 0 if payload.match_case else re.IGNORECASE
    pattern = re.compile(r"\b" + re.escape(search_term) + r"\b", flags)

    total_replacements = 0
    scenes_modified = 0

    with conn:
        for sc in scenes:
            content = sc["content"] or ""
            matches = len(pattern.findall(content))
            if matches > 0:
                new_content = pattern.sub(replace_term, content)
                new_wc = len(html_to_text(new_content).split())
                
                # Update scene
                c.execute(
                    "UPDATE binder_nodes SET content = ?, word_count = ?, updated_at = ? WHERE id = ?",
                    (new_content, new_wc, now, sc["id"])
                )

                # Snapshot to revision vault
                c.execute("""
                    INSERT INTO node_revisions (node_id, version_num, content, change_summary, created_at)
                    VALUES (?, (SELECT COALESCE(MAX(version_num), 0) + 1 FROM node_revisions WHERE node_id = ?), ?, ?, ?)
                """, (sc["id"], sc["id"], new_content, f"Canon replace: {search_term} -> {replace_term}", now))

                total_replacements += matches
                scenes_modified += 1

    conn.close()

    return {
        "status": "success",
        "search_term": search_term,
        "replace_term": replace_term,
        "occurrences_replaced": total_replacements,
        "scenes_modified": scenes_modified,
    }
