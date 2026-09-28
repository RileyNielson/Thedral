import sqlite3
import os
import time

DOCS_DIR = os.path.expanduser("~/Documents")
V_DIR = None
for d in ["Victorian skies", "Victorian Skies", "victorian skies"]:
    p = os.path.join(DOCS_DIR, d)
    if os.path.exists(p):
        V_DIR = p
        break
if not V_DIR:
    V_DIR = os.path.join(DOCS_DIR, "Victorian skies")

WORKSPACE_DIR = os.path.join(V_DIR, "_Studio_Workspace")
DB_PATH = os.path.join(WORKSPACE_DIR, "Database", "manuscript.db")
MIRROR_DIR = os.path.join(WORKSPACE_DIR, "Manuscript_Mirror")
EXPORTS_DIR = os.path.join(WORKSPACE_DIR, "Exports")

for p in [os.path.dirname(DB_PATH), MIRROR_DIR, EXPORTS_DIR]:
    os.makedirs(p, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # 1. Series & Books
    c.execute("""
    CREATE TABLE IF NOT EXISTS series (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL
    )""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id TEXT PRIMARY KEY,
        series_id TEXT,
        volume_num INTEGER,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'PLANNING',
        source_file TEXT
    )""")

    # 2. Master Paragraphs (Fractional Sequence Ordering)
    c.execute("""
    CREATE TABLE IF NOT EXISTS paragraphs (
        id TEXT PRIMARY KEY,
        book_id TEXT,
        chapter_num INTEGER DEFAULT 1,
        seq_order REAL DEFAULT 10.0,
        para_num INTEGER DEFAULT 1,
        text TEXT,
        word_count INTEGER DEFAULT 0,
        phase_status TEXT DEFAULT 'DEV_PENDING',
        version INTEGER DEFAULT 1,
        updated_at TEXT
    )""")

    # 3. Chapter Digests
    c.execute("""
    CREATE TABLE IF NOT EXISTS chapter_digests (
        id TEXT PRIMARY KEY,
        book_id TEXT,
        chapter_num INTEGER,
        total_paras INTEGER,
        total_words INTEGER,
        opening_beat TEXT,
        closing_beat TEXT,
        dialogue_ratio REAL,
        compiled_at TEXT
    )""")

    # 4. Paragraph Revisions (Vault)
    c.execute("""
    CREATE TABLE IF NOT EXISTS paragraph_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paragraph_id TEXT,
        version_num INTEGER,
        text TEXT,
        change_note TEXT,
        created_at TEXT
    )""")

    # 5. Living Style Sheet (Glossary)
    c.execute("""
    CREATE TABLE IF NOT EXISTS style_sheet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT,
        term TEXT UNIQUE,
        rule TEXT,
        created_at TEXT
    )""")

    # 6. Chekhov's Foreshadowing & Promises
    c.execute("""
    CREATE TABLE IF NOT EXISTS promises_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        series_id TEXT,
        book_id TEXT,
        planted_para_id TEXT,
        target_volume INTEGER,
        promise_desc TEXT,
        status TEXT DEFAULT 'SEEDED',
        created_at TEXT
    )""")

    c.execute("INSERT OR IGNORE INTO series VALUES ('Victorian_Skies', 'Victorian Skies')")
    c.execute("INSERT OR IGNORE INTO books VALUES ('ACTIVE_BOOK', 'Victorian_Skies', 1, 'Active Manuscript', 'EDITING', '')")
    
    conn.commit()
    conn.close()

init_db()

def get_paragraphs_range(book_id: str, chapter_num: int, start_p: int, count: int) -> list:
    conn = get_db()
    c = conn.cursor()
    end_p = start_p + count - 1
    c.execute("""
    SELECT para_num, text FROM paragraphs 
    WHERE book_id = ? AND chapter_num = ? AND para_num BETWEEN ? AND ?
    ORDER BY seq_order ASC
    """, (book_id, chapter_num, start_p, end_p))
    rows = c.fetchall()
    conn.close()
    return rows

def get_paragraph_with_scene_context(book_id: str, ch: int, p: int) -> tuple[dict, str]:
    conn = get_db()
    c = conn.cursor()
    pid = f"CH{ch:02d}_P{p:03d}"
    c.execute("SELECT id, text, chapter_num, para_num, version FROM paragraphs WHERE id = ?", (pid,))
    target = c.fetchone()
    if not target:
        conn.close()
        return None, ""

    c.execute("""
    SELECT para_num, text FROM paragraphs 
    WHERE book_id = ? AND chapter_num = ? AND para_num BETWEEN ? AND ?
    ORDER BY seq_order ASC
    """, (book_id, ch, max(1, p - 2), p + 1))
    surrounding = c.fetchall()
    conn.close()

    context_str = ""
    for s in surrounding:
        if s["para_num"] == p:
            context_str += f"\n👉 [TARGET PARAGRAPH P{s['para_num']}]:\n\"{s['text']}\"\n"
        elif s["para_num"] < p:
            context_str += f"\n[PRECEDING P{s['para_num']}]:\n\"{s['text']}\"\n"
        else:
            context_str += f"\n[IMMEDIATE NEXT P{s['para_num']}]:\n\"{s['text']}\"\n"
            
    return dict(target), context_str

def save_paragraph_revision(pid: str, new_text: str) -> int:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT text, version FROM paragraphs WHERE id = ?", (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 0

    old_text = row["text"]
    old_ver = row["version"] or 1
    new_ver = old_ver + 1
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    c.execute("INSERT INTO paragraph_revisions (paragraph_id, version_num, text, change_note, created_at) VALUES (?, ?, ?, 'Rewrite', ?)",
              (pid, old_ver, old_text, ts))
    new_wc = len(new_text.split())
    c.execute("UPDATE paragraphs SET text = ?, word_count = ?, version = ?, updated_at = ? WHERE id = ?",
              (new_text, new_wc, new_ver, ts, pid))
    conn.commit()
    conn.close()
    return new_ver

def get_last_revision(pid: str) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT version_num, text, created_at FROM paragraph_revisions WHERE paragraph_id = ? ORDER BY version_num DESC LIMIT 1", (pid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def execute_rollback(pid: str, target_ver: int, target_text: str) -> bool:
    conn = get_db()
    c = conn.cursor()
    new_wc = len(target_text.split())
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE paragraphs SET text = ?, word_count = ?, version = ?, updated_at = ? WHERE id = ?",
              (target_text, new_wc, target_ver, ts, pid))
    conn.commit()
    conn.close()
    return True

def insert_beat_fractional(book_id: str, ch: int, after_p: int, text: str) -> str:
    conn = get_db()
    c = conn.cursor()
    target_pid = f"CH{ch:02d}_P{after_p:03d}"
    c.execute("SELECT seq_order FROM paragraphs WHERE id = ?", (target_pid,))
    curr = c.fetchone()
    if not curr:
        conn.close()
        return ""
    
    curr_seq = curr["seq_order"]
    c.execute("SELECT seq_order FROM paragraphs WHERE book_id = ? AND chapter_num = ? AND seq_order > ? ORDER BY seq_order ASC LIMIT 1",
              (book_id, ch, curr_seq))
    next_row = c.fetchone()
    next_seq = next_row["seq_order"] if next_row else curr_seq + 10.0
    new_seq = round((curr_seq + next_seq) / 2.0, 3)

    new_pid = f"CH{ch:02d}_P{after_p:03d}_b"
    wc = len(text.split())
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""
    INSERT INTO paragraphs (id, book_id, chapter_num, seq_order, para_num, text, word_count, version, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (new_pid, book_id, ch, new_seq, after_p, text, wc, ts))
    conn.commit()
    conn.close()
    return new_pid

def add_style_rule(term: str, rule: str, series_id: str = "Victorian_Skies"):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO style_sheet (series_id, term, rule, created_at) VALUES (?, ?, ?, ?)",
              (series_id, term, rule, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def log_foreshadowing_promise(series_id: str, book_id: str, pid: str, target_vol: int, desc: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO promises_ledger (series_id, book_id, planted_para_id, target_volume, promise_desc, created_at) VALUES (?, ?, ?, ?, ?, ?)",
              (series_id, book_id, pid, target_vol, desc, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_open_promises(series_id: str = "Victorian_Skies") -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM promises_ledger WHERE series_id = ? AND status = 'SEEDED' ORDER BY target_volume ASC", (series_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
