import os
import re
import sys
import time
import uuid
import json
import docx
import subprocess
import xml.etree.ElementTree as ET
from backend.database import get_db

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\x0b', '\n').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0e-\x1f]', '', text)
    return text.strip()

def strip_rtf_native(rtf_text: str) -> str:
    """
    Cross-Platform RTF Stripper for Windows and Linux:
    Strips RTF control words, fonts, and headers without external dependencies.
    """
    if not rtf_text:
        return ""
    # Strip RTF groups and control words
    text = re.sub(r'[{\\][^{}\\]*?[}]', '', rtf_text)
    text = re.sub(r'\\[a-z]{1,32}(-?\d+)? ?', '', text)
    text = re.sub(r'\\\'[0-9a-fA-F]{2}', '', text)
    return sanitize_text(text)

def read_file_content(fp: str) -> str:
    """Reads RTF, TXT, or MD files across macOS, Windows 10, and Linux."""
    if not fp or not os.path.exists(fp):
        return ""
    try:
        if fp.lower().endswith('.rtf'):
            # If on macOS, use textutil
            if sys.platform == 'darwin':
                try:
                    res = subprocess.run(['textutil', '-convert', 'txt', fp, '-stdout'], capture_output=True, text=True)
                    if res.returncode == 0 and res.stdout:
                        return res.stdout
                except Exception:
                    pass
            
            # Windows 10 / Linux native fallback
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                return strip_rtf_native(f.read())

        elif fp.lower().endswith(('.txt', '.md')):
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except Exception:
        pass
    return ""

def normalize_paragraphs(raw_text: str) -> list[str]:
    cleaned = sanitize_text(raw_text)
    if not cleaned:
        return []
    if "\n\n" in cleaned:
        chunks = re.split(r'\n{2,}', cleaned)
    else:
        chunks = cleaned.split("\n")
    paragraphs = []
    for c in chunks:
        p = re.sub(r'^[ \t]+', '', c).strip()
        if p and not p.startswith("{\\rtf"):
            paragraphs.append(p)
    return paragraphs

def is_chapter_heading(text: str, is_heading_style: bool = False, is_bold: bool = False) -> tuple[bool, str]:
    t = text.strip()
    if not t or len(t) > 85:
        return False, ""
    
    clean = re.sub(r"[\*#_~]", "", t).strip()
    clean_lower = clean.lower()

    if clean.isdigit() and int(clean) < 150:
        return True, f"Chapter {clean}"
    if re.match(r"^(?:[IVXLCDM]+)\.?$", clean, re.IGNORECASE) and len(clean) <= 6:
        return True, f"Chapter {clean.upper()}"

    words = ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"]
    if clean_lower in words:
        return True, f"Chapter {clean.title()}"

    match = re.match(r"^(?:chapter|act|part|prologue|epilogue|interlude|book)\b(?:\s+[\w\d]+)?(?:\s*[:\-–—]\s*(.*))?$", clean, re.I)
    if match:
        return True, clean

    if (is_heading_style or is_bold) and len(clean) < 55:
        if not clean.endswith(('.', '!', '?')) and len(clean.split()) <= 7:
            return True, clean

    return False, ""

def is_scene_divider(text: str) -> bool:
    t = text.strip()
    return bool(re.match(r"^(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|(?:•\s*){3,}|-{3,})$", t))

def derive_smart_scene_title(first_para: str, sc_num: int, ch_title: str, custom_title: str | None = None) -> str:
    if custom_title and custom_title.strip() and not custom_title.lower().startswith(("scene ", "untitled")):
        return custom_title.strip()
    sub_match = re.search(r"[:\-–—]\s*(.+)$", ch_title)
    if sc_num == 1 and sub_match:
        return sub_match.group(1).strip()
    if first_para:
        first_sentence = re.split(r'[.!?]', first_para)[0].strip()
        words = first_sentence.split()
        if len(words) >= 2:
            candidate = " ".join(words[:5]).strip('.,;:"!?')
            candidate = re.sub(r'^(and|but|then|so|because|when|the|a|an)\s+', '', candidate, flags=re.I)
            if len(candidate) > 3:
                return candidate.title()
    return f"Scene {sc_num}"

def parse_docx(fpath: str) -> list[tuple[str, bool, str, str, str]]:
    doc = docx.Document(fpath)
    output = []
    for p in doc.paragraphs:
        txt = sanitize_text(p.text)
        if not txt:
            continue
        is_h = bool(p.style and p.style.name.lower().startswith(('heading', 'title', 'subtitle')))
        is_bold = False
        if p.runs and len(p.runs) > 0:
            is_bold = all(run.bold for run in p.runs if run.text.strip())

        is_ch, ch_title = is_chapter_heading(txt, is_heading_style=is_h, is_bold=is_bold)
        if is_ch:
            output.append((f"Chapter: {ch_title}", True, ch_title, "", ""))
        elif is_scene_divider(txt):
            output.append(("* * *", False, "", "", ""))
        else:
            output.append((txt, False, "", "", ""))
    return output

def parse_plaintext(fpath: str) -> list[tuple[str, bool, str, str, str]]:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        output = []
        for p in normalize_paragraphs(content):
            is_ch, ch_title = is_chapter_heading(p)
            if is_ch:
                output.append((f"Chapter: {ch_title}", True, ch_title, "", ""))
            elif is_scene_divider(p):
                output.append(("* * *", False, "", "", ""))
            else:
                output.append((p, False, "", "", ""))
        return output

def parse_scrivener_project(scriv_path: str) -> dict:
    files_map = {}
    for root, _, files in os.walk(scriv_path):
        low_root = root.lower()
        if any(x in low_root for x in ['settings', 'quicklook', 'snapshots', 'annotations']):
            continue
        parent_dir = os.path.basename(root)
        for f in files:
            full_p = os.path.join(root, f)
            fl = f.lower()
            file_stem = os.path.splitext(f)[0]

            for key in [parent_dir, file_stem]:
                if key not in files_map:
                    files_map[key] = {}
                if fl in ['content.rtf', 'content.txt'] or fl.endswith(('.rtf', '.txt')):
                    if 'content' not in files_map[key]:
                        files_map[key]['content'] = full_p
                if 'synopsis' in fl:
                    files_map[key]['synopsis'] = full_p
                if 'notes' in fl or 'note' in fl:
                    files_map[key]['notes'] = full_p

    scrivx_files = [f for f in os.listdir(scriv_path) if f.endswith('.scrivx')]
    manuscript_tuples = []
    characters = []
    locations = []
    lore_entries = []

    if scrivx_files:
        scrivx_path = os.path.join(scriv_path, scrivx_files[0])
        try:
            tree = ET.parse(scrivx_path)
            root = tree.getroot()

            def traverse_folder(item_node, current_folder=""):
                nonlocal manuscript_tuples, characters, locations, lore_entries
                title_node = item_node.find('Title')
                raw_title = title_node.text.strip() if title_node is not None and title_node.text else ""
                title_lower = raw_title.lower()
                itype = item_node.attrib.get('Type', '')
                uuid_val = str(item_node.attrib.get('UUID') or item_node.attrib.get('Id') or "")

                is_char_folder = "character" in title_lower or "cast" in title_lower or "people" in title_lower
                is_loc_folder = "place" in title_lower or "location" in title_lower or "setting" in title_lower
                is_lore_folder = "research" in title_lower or "lore" in title_lower or "glossary" in title_lower or "world" in title_lower

                file_bundle = files_map.get(uuid_val, {})
                content_text = read_file_content(file_bundle.get('content', ''))
                synopsis_text = read_file_content(file_bundle.get('synopsis', ''))
                notes_text = read_file_content(file_bundle.get('notes', ''))

                if is_char_folder:
                    children = item_node.findall('Children/BinderItem') if item_node.find('Children') is not None else []
                    for ch in children:
                        c_title = ch.find('Title').text.strip() if ch.find('Title') is not None and ch.find('Title').text else ""
                        c_uuid = str(ch.attrib.get('UUID') or ch.attrib.get('Id') or "")
                        c_bundle = files_map.get(c_uuid, {})
                        c_bio = read_file_content(c_bundle.get('content', '')) or read_file_content(c_bundle.get('notes', ''))
                        c_syn = read_file_content(c_bundle.get('synopsis', ''))
                        if c_title:
                            characters.append({"name": c_title, "bio": c_bio, "synopsis": c_syn})
                    return

                if is_loc_folder:
                    children = item_node.findall('Children/BinderItem') if item_node.find('Children') is not None else []
                    for loc in children:
                        l_title = loc.find('Title').text.strip() if loc.find('Title') is not None and loc.find('Title').text else ""
                        l_uuid = str(loc.attrib.get('UUID') or loc.attrib.get('Id') or "")
                        l_bundle = files_map.get(l_uuid, {})
                        l_desc = read_file_content(l_bundle.get('content', '')) or read_file_content(l_bundle.get('notes', ''))
                        if l_title:
                            locations.append({"name": l_title, "desc": l_desc})
                    return

                if is_lore_folder:
                    children = item_node.findall('Children/BinderItem') if item_node.find('Children') is not None else []
                    for rule in children:
                        r_title = rule.find('Title').text.strip() if rule.find('Title') is not None and rule.find('Title').text else ""
                        r_uuid = str(rule.attrib.get('UUID') or rule.attrib.get('Id') or "")
                        r_bundle = files_map.get(r_uuid, {})
                        r_def = read_file_content(r_bundle.get('content', '')) or read_file_content(r_bundle.get('synopsis', ''))
                        if r_title and r_def:
                            lore_entries.append({"term": r_title, "definition": r_def})
                    return

                children = item_node.findall('Children/BinderItem') if item_node.find('Children') is not None else []
                if itype == 'Folder' or (children and itype != 'Text'):
                    folder_name = raw_title or current_folder or "Chapter"
                    manuscript_tuples.append((f"Chapter: {folder_name}", True, folder_name, synopsis_text, notes_text))
                    for child in children:
                        traverse_folder(child, folder_name)
                elif itype in ['Text', 'Document'] or not children:
                    doc_title = raw_title or "Scene"
                    paras = normalize_paragraphs(content_text)
                    if paras:
                        manuscript_tuples.append((f"### SCENE_TITLE: {doc_title}", False, doc_title, synopsis_text, notes_text))
                        for p in paras:
                            manuscript_tuples.append((p, False, doc_title, synopsis_text, notes_text))

            target_root = root.find('Binder') or root
            for top_item in target_root.findall('BinderItem') if target_root.find('BinderItem') is not None else target_root.findall('Children/BinderItem'):
                traverse_folder(top_item)

        except Exception as e:
            print(f"Scrivener parse notice: {e}")

    if not manuscript_tuples and files_map:
        for key, bundle in sorted(files_map.items()):
            content_text = read_file_content(bundle.get('content', ''))
            synopsis_text = read_file_content(bundle.get('synopsis', ''))
            notes_text = read_file_content(bundle.get('notes', ''))
            paras = normalize_paragraphs(content_text)
            if len(paras) >= 1:
                manuscript_tuples.append((f"### SCENE_TITLE: {key}", False, str(key), synopsis_text, notes_text))
                for p in paras:
                    manuscript_tuples.append((p, False, str(key), synopsis_text, notes_text))

    return {
        "manuscript": manuscript_tuples,
        "characters": characters,
        "locations": locations,
        "lore": lore_entries
    }

def build_binder_from_manifest(manifest: dict, book_title: str) -> str:
    tuples = manifest.get("manuscript", [])
    characters = manifest.get("characters", [])
    locations = manifest.get("locations", [])
    lore_entries = manifest.get("lore", [])

    if not tuples:
        raise ValueError(f"No narrative prose could be extracted from '{book_title}'.")

    conn = get_db()
    c = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    book_id = f"book_{uuid.uuid4().hex[:8]}"
    c.execute("""
        INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
        VALUES (?, NULL, 'default', 'BOOK', ?, 10.0, 'Imported Manuscript', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
    """, (book_id, book_title, now, now))

    current_ch_id = None
    current_sc_id = None
    current_ch_title = "Chapter 1"
    current_custom_title = None
    current_synopsis = ""
    current_notes = ""
    ch_sort = 10.0
    sc_sort = 10.0
    sc_num = 0
    current_scene_paras = []
    first_created_scene_id = None

    def flush_scene():
        nonlocal current_sc_id, current_scene_paras, first_created_scene_id, current_custom_title, current_synopsis, current_notes
        if current_sc_id and current_scene_paras:
            full_text = "\n\n".join(current_scene_paras).strip()
            wc = len(full_text.split())
            final_synopsis = current_synopsis.strip() if current_synopsis.strip() else ((full_text[:140] + "...") if len(full_text) > 140 else full_text)
            final_title = derive_smart_scene_title(current_scene_paras[0], sc_num, current_ch_title, current_custom_title)
            
            c.execute("""
                UPDATE binder_nodes 
                SET content = ?, word_count = ?, synopsis = ?, notes = ?, title = ?
                WHERE id = ?
            """, (full_text, wc, final_synopsis, current_notes, final_title, current_sc_id))
            
            if not first_created_scene_id:
                first_created_scene_id = current_sc_id
                
            current_scene_paras = []
            current_custom_title = None
            current_synopsis = ""
            current_notes = ""

    for item in tuples:
        text = item[0]
        is_h = item[1]
        custom_sc_title = item[2] if len(item) > 2 else None
        item_synopsis = item[3] if len(item) > 3 else ""
        item_notes = item[4] if len(item) > 4 else ""

        t_clean = text.strip()
        is_ch, ch_heading = is_chapter_heading(t_clean, is_heading_style=is_h)

        if t_clean.startswith("### SCENE_TITLE: "):
            flush_scene()
            current_sc_id = None
            current_custom_title = t_clean.replace("### SCENE_TITLE: ", "").strip()
            current_synopsis = item_synopsis
            current_notes = item_notes
            continue

        if is_ch or t_clean.startswith("Chapter: "):
            flush_scene()
            current_sc_id = None
            sc_num = 0
            sc_sort = 10.0
            current_ch_id = f"ch_{uuid.uuid4().hex[:8]}"
            current_ch_title = ch_heading if is_ch else t_clean.replace("Chapter: ", "").strip()
            
            c.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'CHAPTER', ?, ?, ?, '', ?, 'DRAFT', 0, 0, '', '{}', ?, ?)
            """, (current_ch_id, book_id, current_ch_title, ch_sort, item_synopsis, item_notes, now, now))
            ch_sort += 10.0
            continue

        if not current_ch_id:
            current_ch_id = f"ch_{uuid.uuid4().hex[:8]}"
            c.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'CHAPTER', 'Chapter 1', 10.0, '', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
            """, (current_ch_id, book_id, now, now))

        if is_scene_divider(t_clean):
            flush_scene()
            current_sc_id = None
            continue

        if not current_sc_id:
            sc_num += 1
            current_sc_id = f"scene_{uuid.uuid4().hex[:8]}"
            placeholder_title = current_custom_title or custom_sc_title or f"Scene {sc_num}"
            current_synopsis = item_synopsis or current_synopsis
            current_notes = item_notes or current_notes

            c.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'SCENE', ?, ?, '', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
            """, (current_sc_id, current_ch_id, placeholder_title, sc_sort, now, now))
            sc_sort += 10.0

        current_scene_paras.append(t_clean)

    flush_scene()

    # Commit Character Sheets
    for ch in characters:
        name_clean = ch["name"].strip()
        if name_clean and len(name_clean) >= 2:
            eid = re.sub(r'\W+', '_', name_clean.lower())
            axioms = json.dumps({"bio": ch.get("bio", "")[:2000], "synopsis": ch.get("synopsis", "")})
            sensory = ch.get("synopsis", "")[:200]
            c.execute("""
                INSERT INTO canonical_entities (entity_id, name, entity_type, role, aliases, sensory_profile, status, axioms, created_at)
                VALUES (?, ?, 'CHARACTER', 'SUPPORTING', '', ?, 'ALIVE', ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET 
                    axioms = excluded.axioms,
                    sensory_profile = CASE WHEN canonical_entities.sensory_profile = '' THEN excluded.sensory_profile ELSE canonical_entities.sensory_profile END
            """, (eid, name_clean, sensory, axioms, now))

    # Commit Locations
    for loc in locations:
        loc_name = loc["name"].strip()
        if loc_name:
            eid = f"loc_{re.sub(r'\W+', '_', loc_name.lower())}"
            axioms = json.dumps({"description": loc.get("desc", "")[:2000]})
            c.execute("""
                INSERT INTO canonical_entities (entity_id, name, entity_type, role, aliases, sensory_profile, status, axioms, created_at)
                VALUES (?, ?, 'LOCATION', 'SUPPORTING', '', '', 'ALIVE', ?, ?)
                ON CONFLICT(entity_id) DO NOTHING
            """, (eid, loc_name, axioms, now))

    # Commit Lore
    for rule in lore_entries:
        term = rule["term"].strip()
        definition = rule["definition"].strip()
        if term and definition:
            c.execute("""
                INSERT OR REPLACE INTO style_sheet (term, category, rule_definition, pronunciation, created_at)
                VALUES (?, 'LORE', ?, '', ?)
            """, (term, definition[:800], now))

    conn.commit()
    conn.close()
    return first_created_scene_id or book_id

def scan_local_manuscripts() -> list[dict]:
    docs_dir = os.path.expanduser("~/Documents")
    found = []
    if not os.path.exists(docs_dir):
        return []
        
    ignored = {'venv', '.venv', 'site-packages', 'library', 'temp', 'node_modules', '.git'}
    for root, dirs, files in os.walk(docs_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ignored]
        
        for d in list(dirs):
            if d.lower().endswith('.scriv'):
                abs_p = os.path.join(root, d)
                found.append({
                    "type": "SCRIVENER",
                    "title": os.path.splitext(d)[0],
                    "path": abs_p,
                    "rel_path": os.path.relpath(abs_p, docs_dir)
                })
                dirs.remove(d)

        for f in files:
            if f.lower().endswith('.docx') and not f.startswith(('~$', '.')):
                abs_p = os.path.join(root, f)
                found.append({
                    "type": "DOCX",
                    "title": os.path.splitext(f)[0].replace("_", " "),
                    "path": abs_p,
                    "rel_path": os.path.relpath(abs_p, docs_dir)
                })

    found.sort(key=lambda x: x["title"].lower())
    return found[:25]