import re
import time
import uuid
import json
from backend.database import get_db
from backend.text_utils import html_to_text
from backend.importing.text_cleaning import _safe_inline_markup
from backend.importing.structure import is_chapter_heading, is_scene_divider, derive_smart_scene_title

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
    book_card = json.dumps({"scrivener": manifest.get("scrivener", {})}, ensure_ascii=False)
    c.execute("""
        INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
        VALUES (?, NULL, 'default', 'BOOK', ?, 10.0, 'Imported Manuscript', '', '', 'DRAFT', 0, 0, '', ?, ?, ?)
    """, (book_id, book_title, book_card, now, now))

    current_ch_id = None
    current_sc_id = None
    current_ch_title = "Chapter 1"
    current_custom_title = None
    current_synopsis = ""
    current_notes = ""
    current_scene_metadata = {}
    current_chapter_metadata = {}
    ch_sort = 10.0
    sc_sort = 10.0
    sc_num = 0
    current_scene_paras = []
    first_created_scene_id = None

    def flush_scene():
        nonlocal current_sc_id, current_scene_paras, first_created_scene_id, current_custom_title, current_synopsis, current_notes, current_scene_metadata
        if current_sc_id:
            full_text = "\n".join(
                f"<p>{_safe_inline_markup(paragraph)}</p>"
                for paragraph in current_scene_paras
            ).strip()
            wc = len(html_to_text(full_text).split())
            plain_text = html_to_text(full_text)
            final_synopsis = current_synopsis.strip() if current_synopsis.strip() else ((plain_text[:140] + "...") if len(plain_text) > 140 else plain_text)
            first_para = html_to_text(current_scene_paras[0]) if current_scene_paras else ""
            final_title = derive_smart_scene_title(first_para, sc_num, current_ch_title, current_custom_title)
            imported_card = json.dumps({"scrivener": current_scene_metadata}, ensure_ascii=False) if current_scene_metadata else "{}"
            
            c.execute("""
                UPDATE binder_nodes 
                SET content = ?, word_count = ?, synopsis = ?, notes = ?, title = ?, card_data = ?
                WHERE id = ?
            """, (full_text, wc, final_synopsis, current_notes, final_title, imported_card, current_sc_id))
            
            if not first_created_scene_id:
                first_created_scene_id = current_sc_id
                
            current_scene_paras = []
            current_custom_title = None
            current_synopsis = ""
            current_notes = ""
            current_scene_metadata = {}
            current_sc_id = None

    def ensure_chapter():
        nonlocal current_ch_id
        if current_ch_id:
            return
        current_ch_id = f"ch_{uuid.uuid4().hex[:8]}"
        c.execute("""
            INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
            VALUES (?, ?, 'default', 'CHAPTER', 'Chapter 1', 10.0, '', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
        """, (current_ch_id, book_id, now, now))

    def ensure_scene():
        nonlocal current_sc_id, sc_num, sc_sort, current_scene_metadata
        if current_sc_id:
            return
        ensure_chapter()
        sc_num += 1
        current_sc_id = f"scene_{uuid.uuid4().hex[:8]}"
        placeholder_title = current_custom_title or f"Scene {sc_num}"
        c.execute("""
            INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
            VALUES (?, ?, 'default', 'SCENE', ?, ?, '', '', '', 'DRAFT', 0, 0, '', ?, ?, ?)
        """, (current_sc_id, current_ch_id, placeholder_title, sc_sort, json.dumps({"scrivener": current_scene_metadata}, ensure_ascii=False) if current_scene_metadata else "{}", now, now))
        sc_sort += 10.0

    for item in tuples:
        text = item[0]
        is_h = item[1]
        custom_sc_title = item[2] if len(item) > 2 else None
        item_synopsis = item[3] if len(item) > 3 else ""
        item_notes = item[4] if len(item) > 4 else ""
        item_scrivener_metadata = item[5] if len(item) > 5 and isinstance(item[5], dict) else {}

        t_clean = text.strip()
        is_ch, ch_heading = is_chapter_heading(t_clean, is_heading_style=is_h)

        if t_clean.startswith("### SCENE_TITLE: "):
            flush_scene()
            current_custom_title = t_clean.replace("### SCENE_TITLE: ", "").strip()
            current_synopsis = item_synopsis
            current_notes = item_notes
            current_scene_metadata = item_scrivener_metadata
            ensure_scene()
            continue

        if is_ch or t_clean.startswith("Chapter: "):
            flush_scene()
            current_sc_id = None
            sc_num = 0
            sc_sort = 10.0
            current_ch_id = f"ch_{uuid.uuid4().hex[:8]}"
            current_ch_title = ch_heading if is_ch else t_clean.replace("Chapter: ", "").strip()
            current_chapter_metadata = item_scrivener_metadata
            
            c.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'CHAPTER', ?, ?, ?, '', ?, 'DRAFT', 0, 0, '', ?, ?, ?)
            """, (current_ch_id, book_id, current_ch_title, ch_sort, item_synopsis, item_notes, json.dumps({"scrivener": current_chapter_metadata}, ensure_ascii=False), now, now))
            ch_sort += 10.0
            continue

        if is_scene_divider(t_clean):
            flush_scene()
            continue

        current_scene_metadata = item_scrivener_metadata or current_scene_metadata
        current_synopsis = item_synopsis or current_synopsis
        current_notes = item_notes or current_notes
        if not current_custom_title and custom_sc_title:
            current_custom_title = custom_sc_title
        ensure_scene()

        current_scene_paras.append(t_clean)

    flush_scene()

    # Commit Character Sheets
    for ch in characters:
        name_clean = ch["name"].strip()
        if name_clean and len(name_clean) >= 2:
            eid = re.sub(r'\W+', '_', name_clean.lower())
            axioms = json.dumps({
                "bio": ch.get("bio", ""),
                "synopsis": ch.get("synopsis", ""),
                "notes": ch.get("notes", ""),
                "scrivener": ch.get("metadata", {}),
            }, ensure_ascii=False)
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
            axioms = json.dumps({
                "description": loc.get("desc", ""),
                "synopsis": loc.get("synopsis", ""),
                "notes": loc.get("notes", ""),
                "scrivener": loc.get("metadata", {}),
            }, ensure_ascii=False)
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
                INSERT OR REPLACE INTO style_sheet (term, category, rule_definition, pronunciation, metadata_json, created_at)
                VALUES (?, 'LORE', ?, '', ?, ?)
            """, (term, definition, json.dumps({
                "notes": rule.get("notes", ""),
                "scrivener": rule.get("metadata", {}),
            }, ensure_ascii=False), now))

    conn.commit()
    conn.close()
    return first_created_scene_id or book_id

