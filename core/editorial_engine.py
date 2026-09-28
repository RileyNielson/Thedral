import os
import re
import time
import docx
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.story_db import get_db, WORKSPACE_DIR, MIRROR_DIR, EXPORTS_DIR

# Common filter verbs that weaken prose in Stage 2 Line Editing
FILTER_VERBS = ["saw", "heard", "felt", "noticed", "watched", "wondered", "realized", "seemed", "appeared", "smelled", "tasted"]
CRUTCH_WORDS = ["suddenly", "glanced", "nodded", "frowned", "slightly", "almost", "began to", "started to", "just", "very", "really"]

# ==========================================
# 1. DETERMINISTIC PROSE TELEMETRY (Non-AI)
# ==========================================

def calculate_chapter_telemetry(book_id: str, chapter_num: int) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT text, word_count FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, chapter_num))
    rows = c.fetchall()
    conn.close()

    if not rows: return {}

    total_words = sum([r["word_count"] for r in rows])
    total_paras = len(rows)
    all_text = " ".join([r["text"] for r in rows])
    text_lower = all_text.lower()

    # Filter verb counts
    filters_found = {v: len(re.findall(r"\b" + v + r"\b", text_lower)) for v in FILTER_VERBS if v in text_lower}
    filters_sorted = dict(sorted(filters_found.items(), key=lambda item: item[1], reverse=True))

    # Crutch word counts
    crutch_found = {w: len(re.findall(r"\b" + w + r"\b", text_lower)) for w in CRUTCH_WORDS if w in text_lower}
    crutch_sorted = dict(sorted(crutch_found.items(), key=lambda item: item[1], reverse=True))

    # Sentence lengths & cadence
    sentences = re.split(r'[.!?]+', all_text)
    sentence_lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]
    avg_sentence_len = round(sum(sentence_lengths) / max(1, len(sentence_lengths)), 1)
    
    # Variance score (musicality)
    variance = round(sum((x - avg_sentence_len) ** 2 for x in sentence_lengths) / max(1, len(sentence_lengths)), 1)

    # Dialogue ratio
    dialogue_paras = sum([1 for r in rows if '"' in r["text"] or '“' in r["text"]])
    dialogue_ratio = round((dialogue_paras / max(1, total_paras)) * 100, 1)

    return {
        "chapter_num": chapter_num,
        "total_words": total_words,
        "total_paras": total_paras,
        "avg_sentence_len": avg_sentence_len,
        "cadence_variance": variance,
        "dialogue_ratio": dialogue_ratio,
        "top_filters": filters_sorted,
        "top_crutches": crutch_sorted
    }

# ==========================================
# 2. LIVING STYLE SHEET & GLOSSARY AUDIT
# ==========================================

def audit_style_sheet(text: str, series_id: str = "Victorian_Skies") -> list:
    """Finds proper-noun spelling drift or capitalization errors."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT term, rule, category FROM style_sheet WHERE series_id = ?", (series_id,))
    terms = c.fetchall()
    conn.close()

    flags = []
    for row in terms:
        t = row["term"]
        # Fuzzy check: match common misspellings or case drift
        pattern = re.compile(r"\b" + re.escape(t) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            found_word = match.group(0)
            if found_word != t:
                flags.append(f"Style Drift: Found '{found_word}', style sheet rule requires '{t}' ({row['rule']}).")
    return flags

def add_style_term(term: str, category: str, rule: str, series_id: str = "Victorian_Skies"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO style_sheet (series_id, term, category, rule) VALUES (?, ?, ?, ?)",
              (series_id, term, category, rule))
    conn.commit()
    conn.close()

# ==========================================
# 3. STRUCTURAL SURGERY (Fractional Ordering)
# ==========================================

def insert_paragraph(book_id: str, chapter_num: int, after_pid: str, text: str) -> str:
    """Inserts a new paragraph between existing ones using fractional seq_order without breaking IDs."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT seq_order, para_num FROM paragraphs WHERE id = ?", (after_pid,))
    curr = c.fetchone()
    if not curr:
        conn.close()
        return ""

    curr_order = curr["seq_order"]
    # Look for next paragraph's order
    c.execute("""
    SELECT seq_order FROM paragraphs 
    WHERE book_id = ? AND chapter_num = ? AND seq_order > ? 
    ORDER BY seq_order ASC LIMIT 1
    """, (book_id, chapter_num, curr_order))
    next_row = c.fetchone()
    
    next_order = next_row["seq_order"] if next_row else curr_order + 10.0
    new_order = round((curr_order + next_order) / 2.0, 3) # Fractional insertion!

    new_pid = f"CH{chapter_num:02d}_P{curr['para_num']}_INS"
    wc = len(text.split())

    c.execute("""
    INSERT INTO paragraphs (id, book_id, chapter_num, seq_order, para_num, text, word_count, version, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (new_pid, book_id, chapter_num, new_order, curr['para_num'], text, wc, time.strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()
    export_local_mirror_files(book_id)
    return new_pid

def delete_paragraph(paragraph_id: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT book_id FROM paragraphs WHERE id = ?", (paragraph_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    book_id = row["book_id"]
    c.execute("DELETE FROM paragraphs WHERE id = ?", (paragraph_id,))
    conn.commit()
    conn.close()
    export_local_mirror_files(book_id)
    return True

# ==========================================
# 4. TWO-WAY LOCAL MAC MIRROR SYNC
# ==========================================

def export_local_mirror_files(book_id: str):
    """Exports clean, editable Markdown files to _Studio_Workspace/Manuscript_Mirror/."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT DISTINCT chapter_num FROM paragraphs WHERE book_id = ? ORDER BY chapter_num ASC", (book_id,))
    chapters = [r[0] for r in c.fetchall()]

    for ch in chapters:
        c.execute("SELECT id, seq_order, text FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, ch))
        rows = c.fetchall()
        ch_file = os.path.join(MIRROR_DIR, f"Chapter_{ch:02d}.md")
        
        with open(ch_file, "w") as f:
            f.write(f"# Chapter {ch}\n\n")
            for r in rows:
                f.write(f"<!-- ID: {r['id']} | SEQ: {r['seq_order']} -->\n{r['text']}\n\n")
    conn.close()
    print(f"📁 [Local Mirror]: Synced {len(chapters)} chapters to _Studio_Workspace/Manuscript_Mirror/")

def sync_from_local_mirror(book_id: str) -> int:
    """Reads any edits made on your Mac inside Manuscript_Mirror/ and syncs to SQLite."""
    conn = get_db()
    c = conn.cursor()
    updated = 0

    for ch_file in sorted(glob.glob(os.path.join(MIRROR_DIR, "Chapter_*.md"))):
        with open(ch_file, "r") as f:
            content = f.read()

        blocks = re.split(r"<!-- ID:\s*(\w+)\s*\|\s*SEQ:\s*([\d\.]+)\s*-->", content)
        for i in range(1, len(blocks), 3):
            pid = blocks[i].strip()
            seq = float(blocks[i+1].strip())
            body = blocks[i+2].strip()

            c.execute("SELECT text FROM paragraphs WHERE id = ?", (pid,))
            old = c.fetchone()
            if old and old["text"] != body:
                wc = len(body.split())
                c.execute("UPDATE paragraphs SET text = ?, word_count = ?, seq_order = ?, updated_at = ? WHERE id = ?",
                          (body, wc, seq, time.strftime("%Y-%m-%d %H:%M:%S"), pid))
                updated += 1

    conn.commit()
    conn.close()
    return updated

# ==========================================
# 5. EXPORT TO WORD (.DOCX)
# ==========================================

def export_book_to_docx(book_id: str) -> str:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT b.title, s.title as series_name, b.volume_num FROM books b JOIN series s ON b.series_id = s.id WHERE b.id = ?", (book_id,))
    b_info = c.fetchone()
    
    c.execute("SELECT chapter_num, text FROM paragraphs WHERE book_id = ? ORDER BY chapter_num ASC, seq_order ASC", (book_id,))
    paras = c.fetchall()
    conn.close()

    if not paras: return ""

    doc = docx.Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title_p.add_run(f"{b_info['title']}\n")
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(24)
    run_title.bold = True

    current_ch = 0
    for p in paras:
        if p["chapter_num"] != current_ch:
            current_ch = p["chapter_num"]
            doc.add_page_break()
            ch_p = doc.add_paragraph()
            ch_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            ch_run = ch_p.add_run(f"Chapter {current_ch}\n\n")
            ch_run.font.name = "Times New Roman"
            ch_run.font.size = Pt(16)
            ch_run.bold = True

        para_obj = doc.add_paragraph()
        para_obj.paragraph_format.first_line_indent = Inches(0.5)
        para_obj.paragraph_format.line_spacing = 1.5
        run = para_obj.add_run(p["text"])
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)

    filename = f"{b_info['series_name']}_Book{b_info['volume_num']:02d}_{b_info['title']}.docx".replace(" ", "_")
    output_path = os.path.join(EXPORTS_DIR, filename)
    doc.save(output_path)
    return output_path
