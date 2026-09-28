import json
import time
import ollama
from config import STUDIO_MODEL, LLM_OPTIONS, ACTIVE_CONTEXT
from db import get_db

READER_TRACK_PROMPT = """Analyze the scene paragraphs and categorize the reader's disclosure into strict JSON:
{
  "direct": [{"claim": "Direct established fact", "para_num": int}],
  "inferred": [{"claim": "Subtextual deduction", "clue": "Quoted clue", "para_num": int}],
  "delayed": [{"question": "Open dramatic question", "target_chapter_hint": int or null, "para_num": int}]
}
"""

def extract_chapter_disclosures(book_id: str, chapter_num: int) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT para_num, text FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, chapter_num))
    rows = c.fetchall()
    if not rows:
        conn.close()
        return {}
    sample_text = "\n\n".join([f"[P{r['para_num']}]: {r['text']}" for r in rows[:15]])
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    counts = {"direct": 0, "inferred": 0, "delayed": 0}
    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "system", "content": READER_TRACK_PROMPT}, {"role": "user", "content": f"Chapter {chapter_num}:\n{sample_text}"}], format="json", options=LLM_OPTIONS)
        data = json.loads(resp['message']['content'])
        with conn:
            for d in data.get("direct", []):
                c.execute("INSERT INTO reader_disclosures (book_id, chapter_num, para_num, disclosure_type, narrative_claim, clue_evidence, resolution_status, created_at) VALUES (?, ?, ?, 'DIRECT', ?, '', 'CONFIRMED', ?)",
                          (book_id, chapter_num, d.get("para_num", 1), d.get("claim", ""), ts))
                counts["direct"] += 1
            for inf in data.get("inferred", []):
                c.execute("INSERT INTO reader_disclosures (book_id, chapter_num, para_num, disclosure_type, narrative_claim, clue_evidence, resolution_status, created_at) VALUES (?, ?, ?, 'INFERRED', ?, ?, 'ACTIVE', ?)",
                          (book_id, chapter_num, inf.get("para_num", 1), inf.get("claim", ""), inf.get("clue", ""), ts))
                counts["inferred"] += 1
            for del_q in data.get("delayed", []):
                c.execute("INSERT INTO reader_disclosures (book_id, chapter_num, para_num, disclosure_type, narrative_claim, target_reveal_ch, resolution_status, created_at) VALUES (?, ?, ?, 'DELAYED', ?, ?, 'ACTIVE', ?)",
                          (book_id, chapter_num, del_q.get("para_num", 1), del_q.get("question", ""), del_q.get("target_chapter_hint"), ts))
                counts["delayed"] += 1
    except Exception as e: print(f"⚠️ Disclosure extraction error: {e}")
    conn.close()
    return counts

def audit_reader_experience(book_id: str, current_chapter: int) -> list:
    conn = get_db()
    c = conn.cursor()
    alerts = []
    c.execute("SELECT chapter_num, para_num, narrative_claim, target_reveal_ch FROM reader_disclosures WHERE book_id = ? AND disclosure_type = 'DELAYED' AND resolution_status = 'ACTIVE' AND chapter_num <= ?", (book_id, current_chapter))
    for q in c.fetchall():
        age = current_chapter - q["chapter_num"]
        if age >= 5 and (not q["target_reveal_ch"] or q["target_reveal_ch"] <= current_chapter):
            alerts.append(f"⏳ **Stale Mystery**: Question from CH{q['chapter_num']:02d}_P{q['para_num']:03d} (\"{q['narrative_claim']}\") has had zero clues for {age} chapters.")
    c.execute("SELECT narrative_claim, chapter_num FROM reader_disclosures WHERE book_id = ? AND disclosure_type = 'INFERRED' AND chapter_num < ?", (book_id, current_chapter))
    prior_inferred = c.fetchall()
    c.execute("SELECT narrative_claim, para_num FROM reader_disclosures WHERE book_id = ? AND disclosure_type = 'DIRECT' AND chapter_num = ?", (book_id, current_chapter))
    for d in c.fetchall():
        for inf in prior_inferred:
            common = set(d["narrative_claim"].lower().split()).intersection(set(inf["narrative_claim"].lower().split()))
            if len(common) >= 3 and not any(w in common for w in ["the", "and", "with", "that"]):
                alerts.append(f"💡 **Subtext Murder**: In Ch {current_chapter} (P{d['para_num']}), you explicitly state *\"{d['narrative_claim']}\"*, which was already inferred in Ch {inf['chapter_num']}.")
    conn.close()
    return alerts

def get_reader_experience_dossier(book_id: str, chapter_num: int) -> str:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT disclosure_type, narrative_claim, clue_evidence FROM reader_disclosures WHERE book_id = ? AND chapter_num = ? ORDER BY id ASC", (book_id, chapter_num))
    rows = c.fetchall()
    conn.close()
    if not rows: return f"No reader disclosure telemetry logged for Chapter {chapter_num}. Text *'track reader'* first."
    direct = [r for r in rows if r["disclosure_type"] == "DIRECT"]
    inferred = [r for r in rows if r["disclosure_type"] == "INFERRED"]
    delayed = [r for r in rows if r["disclosure_type"] == "DELAYED"]
    report = f"🧠 **READER EXPERIENCE DOSSIER — CHAPTER {chapter_num}:**\n\n🎯 **DIRECT (Facts):**\n"
    report += "\n".join([f"• {d['narrative_claim']}" for d in direct]) if direct else "• None directly stated.\n"
    report += "\n\n🔍 **INFERRED (Subtext & Breadcrumbs):**\n"
    report += "\n".join([f"• {inf['narrative_claim']}" + (f" → _{inf['clue_evidence']}_" if inf['clue_evidence'] else "") for inf in inferred]) if inferred else "• None planted.\n"
    report += "\n\n⏳ **DELAYED (Open Mysteries):**\n"
    report += "\n".join([f"• {q['narrative_claim']}" for q in delayed]) if delayed else "• None active.\n"
    return report
