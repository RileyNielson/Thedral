import os
import re
import time
import subprocess
import xml.etree.ElementTree as ET
from db import get_db, reindex_chapter
from editorial import export_local_mirror_files

def sanitize_prose(text: str) -> str:
    if not text: return ""
    text = text.replace('\x0b', '\n').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0e-\x1f]', '', text)
    return text.strip()

def get_scrivener_draft_items(scriv_path: str) -> list:
    scrivx_files = [f for f in os.listdir(scriv_path) if f.endswith('.scrivx')]
    if not scrivx_files: return []
    scrivx_path = os.path.join(scriv_path, scrivx_files[0])
    ordered_items = []
    try:
        tree = ET.parse(scrivx_path)
        root = tree.getroot()
        draft_node = None
        for item in root.iter('BinderItem'):
            if item.attrib.get('Type') == 'DraftFolder':
                draft_node = item
                break
        target_root = draft_node if draft_node is not None else root.find('Binder')
        if target_root is not None:
            def traverse(node, current_folder=""):
                for child in node.findall('Children/BinderItem') if node.find('Children') is not None else []:
                    uuid = child.attrib.get('UUID') or child.attrib.get('Id')
                    itype = child.attrib.get('Type', '')
                    title = ""
                    title_node = child.find('Title')
                    if title_node is not None and title_node.text:
                        title = title_node.text.strip()
                    if itype == 'Folder':
                        traverse(child, current_folder=title or "Chapter")
                    elif itype in ['Text', 'Document'] and uuid:
                        ordered_items.append({"uuid": str(uuid), "title": title, "parent_folder": current_folder})
                        traverse(child, current_folder=current_folder)
            traverse(target_root)
    except Exception as e:
        print(f"⚠️ Scrivener binder parse error: {e}")
    return ordered_items

def extract_scrivener(scriv_path: str) -> list:
    draft_items = get_scrivener_draft_items(scriv_path)
    output = []
    content_map = {}
    for root, _, files in os.walk(scriv_path):
        if any(x in root.lower() for x in ['settings', 'quicklook', 'snapshots', 'annotations']): continue
        parent_uuid = os.path.basename(root)
        primary_file = None
        for f in files:
            fl = f.lower()
            if fl in ['content.rtf', 'content.txt']:
                primary_file = os.path.join(root, f)
                break
        if not primary_file:
            for f in files:
                fl = f.lower()
                if fl.endswith(('.rtf', '.txt', '.pdf')) and not fl.startswith(('recents', 'synopsis', 'notes', 'comments', '.')):
                    primary_file = os.path.join(root, f)
                    break
        if primary_file:
            content_map[parent_uuid] = primary_file

    def read_file(fp: str) -> str:
        fl = fp.lower()
        if fl.endswith('.rtf'):
            res = subprocess.run(['textutil', '-convert', 'txt', fp, '-stdout'], capture_output=True, text=True)
            return res.stdout or ""
        elif fl.endswith('.pdf'):
            from pypdf import PdfReader
            try:
                reader = PdfReader(fp)
                return "".join([p.extract_text() or "" for p in reader.pages])
            except Exception: return ""
        elif fl.endswith('.txt'):
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as tf: return tf.read()
            except Exception: return ""
        return ""

    last_folder = None
    if draft_items:
        for item in draft_items:
            u = item["uuid"]
            if u not in content_map: continue
            if item["parent_folder"] and item["parent_folder"] != last_folder:
                last_folder = item["parent_folder"]
                output.append((f"Chapter: {last_folder}", True))
            else:
                if output: output.append(("* * *", False))
            raw_text = sanitize_prose(read_file(content_map[u]))
            if raw_text:
                for line in raw_text.split("\n\n"):
                    clean = line.strip()
                    if clean and not clean.startswith("{\\rtf"): output.append((clean, False))
    return output

def extract_docx(fpath: str) -> list:
    import docx
    doc = docx.Document(fpath)
    output = []
    for p in doc.paragraphs:
        txt = sanitize_prose(p.text)
        if txt:
            is_h = bool(p.style and p.style.name.lower().startswith(('heading', 'title', 'subtitle')))
            output.append((txt, is_h))
    return output

def extract_raw_paragraphs(fpath: str) -> list:
    ext = os.path.splitext(fpath)[1].lower()
    if ext == '.scriv' or os.path.isdir(fpath): return extract_scrivener(fpath)
    elif ext in [".docx", ".doc"]: return extract_docx(fpath)
    else:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            content = sanitize_prose(f.read())
            return [(p.strip(), False) for p in content.split("\n\n") if p.strip()]

def is_chapter_marker(text: str, is_h: bool = False) -> tuple:
    t = text.strip()
    if not t or len(t) > 90: return False, ""
    clean = re.sub(r"[\*#_~]", "", t).strip()
    if clean.isdigit() and int(clean) < 150: return True, f"Chapter {clean}"
    words = ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"]
    if clean.lower() in words: return True, f"Chapter {clean.title()}"
    if re.match(r"^(?:[IVXLCDM]+)\.?$", clean, re.IGNORECASE) and len(clean) <= 6: return True, f"Chapter {clean.upper()}"
    match_named = re.match(r"^(?:chapter|act|part|prologue|epilogue|interlude|book)\b(?:\s+[\w\d]+)?(?:\s*[:\-–—]\s*(.*))?$", clean, re.I)
    if match_named: return True, clean
    if is_h and len(clean) < 60: return True, clean
    return False, ""

def is_scene_break(text: str) -> bool:
    return bool(re.match(r"^(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|-{3,})$", text.strip()))

def is_front_matter(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["copyright", "all rights reserved", "isbn", "printed in", "dedication", "published by"])

def compile_chapter_digests(book_id: str):
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT chapter_num FROM paragraphs WHERE book_id = ? ORDER BY chapter_num ASC", (book_id,))
        chapters = [r[0] for r in c.fetchall()]
        for ch in chapters:
            c.execute("SELECT para_num, text, word_count FROM paragraphs WHERE book_id = ? AND chapter_num = ? ORDER BY seq_order ASC", (book_id, ch))
            rows = c.fetchall()
            if not rows: continue
            total_paras = len(rows)
            total_words = sum([r["word_count"] for r in rows])
            open_beat = " ".join([r["text"] for r in rows[:2]])[:400]
            close_beat = " ".join([r["text"] for r in rows[-2:]])[:400]
            dialogue_paras = sum([1 for r in rows if '"' in r["text"] or '“' in r["text"]])
            ratio = round(dialogue_paras / max(1, total_paras), 2)
            did = f"{book_id}_CH{ch:02d}"
            c.execute("INSERT OR REPLACE INTO chapter_digests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (did, book_id, ch, total_paras, total_words, open_beat, close_beat, ratio, time.strftime("%Y-%m-%d %H:%M:%S")))
    conn.close()

def replace_entire_chapter(book_id: str, chapter_num: int, raw_text: str) -> tuple:
    new_paras = [p.strip() for p in raw_text.split("\n\n") if len(p.strip()) > 5]
    if not new_paras: return 0, 0
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("SELECT id, text, version, para_uuid FROM paragraphs WHERE book_id = ? AND chapter_num = ?", (book_id, chapter_num))
        old_rows = c.fetchall()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        for r in old_rows:
            c.execute("INSERT INTO paragraph_revisions (para_uuid, display_id, version_num, text, change_note, created_at) VALUES (?, ?, ?, ?, 'Full chapter replacement', ?)",
                      (r["para_uuid"], r["id"], r["version"] or 1, r["text"], ts))
        c.execute("DELETE FROM paragraphs WHERE book_id = ? AND chapter_num = ?", (book_id, chapter_num))
        seq_order, total_words, p_num = 10.0, 0, 1
        import uuid
        for text in new_paras:
            is_ch, _ = is_chapter_marker(text)
            if is_ch: continue
            if is_scene_break(text): text = "* * *"
            pid = f"CH{chapter_num:02d}_P{p_num:03d}"
            puuid = str(uuid.uuid4())[:8]
            wc = len(text.split())
            total_words += wc
            c.execute("INSERT OR REPLACE INTO paragraphs VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DEV_PENDING', 2, ?)",
                      (pid, puuid, book_id, chapter_num, seq_order, p_num, text, wc, ts))
            p_num += 1
            seq_order += 10.0
    conn.close()
    reindex_chapter(book_id, chapter_num)
    compile_chapter_digests(book_id)
    export_local_mirror_files(book_id)
    return len(new_paras), total_words

def ingest_manuscript(fpath: str, book_id: str) -> tuple:
    raw_tuples = extract_raw_paragraphs(fpath)
    if not raw_tuples: return 0, 0, 0
    conn = get_db()
    with conn:
        c = conn.cursor()
        c.execute("DELETE FROM paragraphs WHERE book_id = ?", (book_id,))
        ch_num, p_num, seq_order, total_words, total_paras, started_story = 0, 1, 10.0, 0, 0, False
        import uuid
        for text, is_h in raw_tuples:
            t_clean = text.strip()
            if not started_story:
                if is_front_matter(t_clean): continue
                is_ch, _ = is_chapter_marker(t_clean, is_h)
                if is_ch or t_clean == "### CHAPTER BREAK":
                    started_story = True
                    ch_num = 1
                    continue
                if len(t_clean) > 80:
                    started_story = True
                    ch_num = 1
            is_ch, _ = is_chapter_marker(t_clean, is_h)
            if is_ch or t_clean == "### CHAPTER BREAK":
                if total_paras > 0:
                    ch_num += 1
                    p_num = 1
                    seq_order = 10.0
                continue
            if ch_num == 0: ch_num = 1
            if is_scene_break(t_clean): t_clean = "* * *"
            pid = f"CH{ch_num:02d}_P{p_num:03d}"
            puuid = str(uuid.uuid4())[:8]
            wc = len(t_clean.split())
            total_words += wc
            total_paras += 1
            c.execute("INSERT OR REPLACE INTO paragraphs VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'DEV_PENDING', 1, ?)",
                      (pid, puuid, book_id, ch_num, seq_order, p_num, t_clean, wc, time.strftime("%Y-%m-%d %H:%M:%S")))
            p_num += 1
            seq_order += 10.0
        c.execute("INSERT OR REPLACE INTO books (id, title, status, source_file) VALUES (?, ?, 'EDITING', ?)",
                  (book_id, os.path.basename(fpath), fpath))
    conn.close()
    compile_chapter_digests(book_id)
    export_local_mirror_files(book_id)
    return total_paras, total_words, max(1, ch_num)
