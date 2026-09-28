import sqlite3
import os
import time
import uuid
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS series (id TEXT PRIMARY KEY, title TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS books (id TEXT PRIMARY KEY, series_id TEXT, volume_num INTEGER, title TEXT NOT NULL, status TEXT DEFAULT 'PLANNING', source_file TEXT, FOREIGN KEY(series_id) REFERENCES series(id))")
        c.execute("""CREATE TABLE IF NOT EXISTS paragraphs (
            id TEXT PRIMARY KEY, para_uuid TEXT UNIQUE, book_id TEXT, chapter_num INTEGER DEFAULT 1,
            seq_order REAL DEFAULT 10.0, para_num INTEGER DEFAULT 1, text TEXT, word_count INTEGER DEFAULT 0,
            phase_status TEXT DEFAULT 'DEV_PENDING', version INTEGER DEFAULT 1, updated_at TEXT,
            FOREIGN KEY(book_id) REFERENCES books(id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS chapter_digests (
            id TEXT PRIMARY KEY, book_id TEXT, chapter_num INTEGER, total_paras INTEGER, total_words INTEGER,
            opening_beat TEXT, closing_beat TEXT, dialogue_ratio REAL, compiled_at TEXT,
            FOREIGN KEY(book_id) REFERENCES books(id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS paragraph_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, para_uuid TEXT, display_id TEXT, version_num INTEGER,
            text TEXT, change_note TEXT, created_at TEXT
        )""")
        c.execute("CREATE TABLE IF NOT EXISTS style_sheet (id INTEGER PRIMARY KEY AUTOINCREMENT, series_id TEXT, term TEXT UNIQUE, rule TEXT, created_at TEXT)")
        c.execute("""CREATE TABLE IF NOT EXISTS promises_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT, series_id TEXT, book_id TEXT, planted_para_id TEXT,
            target_volume INTEGER, promise_desc TEXT, status TEXT DEFAULT 'SEEDED', created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS story_worldlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, chapter_num INTEGER, para_num INTEGER,
            entity_name TEXT, geographic_location TEXT, physical_state TEXT, epistemic_knowledge TEXT, timeline_day REAL
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS reader_disclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT, book_id TEXT, chapter_num INTEGER, para_num INTEGER,
            disclosure_type TEXT, narrative_claim TEXT, clue_evidence TEXT, target_reveal_ch INTEGER,
            resolution_status TEXT DEFAULT 'ACTIVE', created_at TEXT
        )""")
                # Self-healing column checks
        for table, col, ctype in [
            ('paragraph_revisions', 'para_uuid', 'TEXT'),
            ('paragraph_revisions', 'display_id', 'TEXT'),
            ('paragraph_revisions', 'version_num', 'INTEGER DEFAULT 1'),
            ('paragraphs', 'para_uuid', 'TEXT'),
            ('paragraphs', 'seq_order', 'REAL DEFAULT 10.0'),
            ('paragraphs', 'version', 'INTEGER DEFAULT 1'),
            ('paragraphs', 'phase_status', "TEXT DEFAULT 'DEV_PENDING'"),
            ('books', 'series_id', "TEXT DEFAULT 'Victorian_Skies'"),
            ('books', 'volume_num', 'INTEGER DEFAULT 1')
        ]:
            c.execute(f'PRAGMA table_info({table})')
            if col not in [r[1] for r in c.fetchall()]:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {col} {ctype};')

        c.execute("CREATE INDEX IF NOT EXISTS idx_para_flow ON paragraphs (book_id, chapter_num, seq_order);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_para_num ON paragraphs (book_id, chapter_num, para_num);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_rev_lookup ON paragraph_revisions (para_uuid, version_num);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_disclosure_type ON reader_disclosures (book_id, disclosure_type, resolution_status);")
        c.execute("INSERT OR IGNORE INTO series VALUES ('Victorian_Skies', 'Victorian Skies')")
        c.execute("INSERT OR IGNORE INTO books VALUES ('ACTIVE_BOOK', 'Victorian_Skies', 1, 'Active Manuscript', 'EDITING', '')")

def reindex_chapter(book_id: str, chapter_num: int):
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("SELECT rowid, para_uuid FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, chapter_num))
        rows = c.fetchall()
        for r in rows:
            c.execute("UPDATE paragraphs SET id = ? WHERE rowid = ?", (f"TEMP_{uuid.uuid4().hex[:12]}", r["rowid"]))
        for idx, r in enumerate(rows, 1):
            clean_pid = f"CH{chapter_num:02d}_P{idx:03d}"
            clean_seq = idx * 10.0
            puuid = r["para_uuid"] or str(uuid.uuid4())[:8]
            c.execute("UPDATE paragraphs SET id = ?, para_num = ?, seq_order = ?, para_uuid = ? WHERE rowid = ?",
                      (clean_pid, idx, clean_seq, puuid, r["rowid"]))
    conn.close()

def insert_paragraph_and_reindex(book_id: str, ch: int, after_p: int, text: str) -> str:
    conn = get_db()
    with conn:
        c = conn.cursor()
        target_pid = f"CH{ch:02d}_P{after_p:03d}"
        c.execute("SELECT seq_order FROM paragraphs WHERE id = ?", (target_pid,))
        curr = c.fetchone()
        curr_seq = curr["seq_order"] if curr else after_p * 10.0
        temp_seq = curr_seq + 5.0
        temp_id = f"INSERT_{uuid.uuid4().hex[:8]}"
        puuid = str(uuid.uuid4())[:8]
        wc = len(text.split())
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO paragraphs (id, para_uuid, book_id, chapter_num, seq_order, para_num, text, word_count, version, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""", (temp_id, puuid, book_id, ch, temp_seq, after_p + 1, text, wc, ts))
    conn.close()
    reindex_chapter(book_id, ch)
    return f"CH{ch:02d}_P{after_p + 1:03d}"

def delete_paragraph_and_reindex(book_id: str, ch: int, para_num: int) -> bool:
    conn = get_db()
    with conn:
        c = conn.cursor()
        target_pid = f"CH{ch:02d}_P{para_num:03d}"
        c.execute("SELECT para_uuid, text, version FROM paragraphs WHERE id = ?", (target_pid,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO paragraph_revisions (para_uuid, display_id, version_num, text, change_note, created_at) VALUES (?, ?, ?, ?, 'Deleted paragraph', ?)",
                  (row["para_uuid"], target_pid, row["version"], row["text"], ts))
        c.execute("DELETE FROM paragraphs WHERE id = ?", (target_pid,))
    conn.close()
    reindex_chapter(book_id, ch)
    return True

def get_paragraphs_range(book_id: str, chapter_num: int, start_p: int, count: int) -> list:
    conn = get_db()
    c = conn.cursor()
    end_p = start_p + count - 1
    c.execute("SELECT para_num, text FROM paragraphs WHERE book_id = ? AND chapter_num = ? AND para_num BETWEEN ? AND ? ORDER BY seq_order ASC",
              (book_id, chapter_num, start_p, end_p))
    rows = c.fetchall()
    conn.close()
    return rows

def get_paragraph_with_scene_context(book_id: str, ch: int, p: int) -> tuple:
    conn = get_db()
    c = conn.cursor()
    pid = f"CH{ch:02d}_P{p:03d}"
    c.execute("SELECT id, text, chapter_num, para_num, version FROM paragraphs WHERE id = ?", (pid,))
    target = c.fetchone()
    if not target:
        conn.close()
        return None, ""
    c.execute("SELECT para_num, text FROM paragraphs WHERE book_id = ? AND chapter_num = ? AND para_num BETWEEN ? AND ? ORDER BY seq_order ASC",
              (book_id, ch, max(1, p - 2), p + 1))
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
    with conn:
        c = conn.cursor()
        c.execute("SELECT para_uuid, text, version FROM paragraphs WHERE id = ?", (pid,))
        row = c.fetchone()
        if not row:
            conn.close()
            return 0
        old_text = row["text"]
        old_ver = row["version"] or 1
        new_ver = old_ver + 1
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO paragraph_revisions (para_uuid, display_id, version_num, text, change_note, created_at) VALUES (?, ?, ?, ?, 'Author rewrite', ?)",
                  (row["para_uuid"], pid, old_ver, old_text, ts))
        new_wc = len(new_text.split())
        c.execute("UPDATE paragraphs SET text = ?, word_count = ?, version = ?, updated_at = ? WHERE id = ?",
                  (new_text, new_wc, new_ver, ts, pid))
    conn.close()
    return new_ver

def get_last_revision(pid: str) -> dict:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT r.version_num, r.text, r.created_at FROM paragraph_revisions r JOIN paragraphs p ON r.para_uuid = p.para_uuid WHERE p.id = ? ORDER BY r.version_num DESC LIMIT 1", (pid,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def execute_rollback(pid: str, target_ver: int, target_text: str) -> bool:
    conn = get_db()
    with conn:
        c = conn.cursor()
        new_wc = len(target_text.split())
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE paragraphs SET text = ?, word_count = ?, version = ?, updated_at = ? WHERE id = ?",
                  (target_text, new_wc, target_ver, ts, pid))
    conn.close()
    return True

def add_style_rule(term: str, rule: str, series_id: str = "Victorian_Skies"):
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO style_sheet (series_id, term, rule, created_at) VALUES (?, ?, ?, ?)",
                  (series_id, term, rule, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.close()

def log_foreshadowing_promise(series_id: str, book_id: str, pid: str, target_vol: int, desc: str):
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("INSERT INTO promises_ledger (series_id, book_id, planted_para_id, target_volume, promise_desc, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (series_id, book_id, pid, target_vol, desc, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.close()

def get_open_promises(series_id: str = "Victorian_Skies") -> list:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM promises_ledger WHERE series_id = ? AND status = 'SEEDED' ORDER BY target_volume ASC", (series_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_db()
