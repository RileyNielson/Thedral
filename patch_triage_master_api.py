import re

with open("backend/routers/binder.py", "r") as f:
    code = f.read()

master_triage_route = '''
@router.post("/api/binder/triage-scene/{scene_id}")
async def master_triage_scene(scene_id: str):
    """
    The 1-Click Master Cleanse:
    - Strips manual tabs/spaces (fixes paragraph indenting).
    - Polishes typography (em-dashes, ellipses).
    - Slices scene by *** dividers.
    - Triggers AI auto-titling for new slices.
    - Counts [TK] markers.
    """
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT parent_id, sort_order, content FROM binder_nodes WHERE id = ?", (scene_id,))
    scene = c.fetchone()
    
    if not scene or not scene["content"]:
        conn.close()
        return {"status": "empty"}

    text = scene["content"]

    # 1. PARAGRAPHING & TYPOGRAPHY CLEANUP
    # Remove leading spaces/tabs (prevents manual indenting corruption)
    text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
    # Remove trailing spaces
    text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
    # Typography
    text = re.sub(r'--+', '—', text)
    text = re.sub(r'\.\.\.', '…', text)
    # Collapse 3+ line breaks into exactly 2 (standard block paragraphing)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 2. SCENE SLICING
    blocks = re.split(r'\n\n(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|-{3,})\n\n', text)
    
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    parent_id = scene["parent_id"]
    base_sort = float(scene["sort_order"])
    
    first_block = blocks[0].strip()
    new_scene_ids = []

    with conn:
        # Update original scene
        conn.execute("UPDATE binder_nodes SET content = ?, word_count = ? WHERE id = ?", 
                    (first_block, len(first_block.split()), scene_id))

        # Create new scenes if dividers were found
        for idx, block in enumerate(blocks[1:], 1):
            clean_block = block.strip()
            if not clean_block: continue
            
            new_id = f"scene_{uuid.uuid4().hex[:8]}"
            new_sort = base_sort + (idx * 1.0)
            wc = len(clean_block.split())
            
            conn.execute("""
                INSERT INTO binder_nodes (id, parent_id, project_id, node_type, title, sort_order, content, status, word_count, is_archived, created_at, updated_at)
                VALUES (?, ?, 'default', 'SCENE', ?, ?, ?, 'DRAFT', ?, 0, ?, ?)
            """, (new_id, parent_id, f"Sliced Scene {idx}", new_sort, clean_block, wc, now, now))
            new_scene_ids.append(new_id)

    # Count TK markers in the main block
    tk_count = len(re.findall(r'\[TK[^\]]*\]', first_block, re.IGNORECASE))

    # Trigger async auto-titler if new scenes were created
    if new_scene_ids:
        c.execute("SELECT id FROM binder_nodes WHERE node_type = 'BOOK' LIMIT 1")
        b_row = c.fetchone()
        if b_row:
            asyncio.create_task(auto_title_scenes(AutoTitleRequest(book_id=b_row["id"])))

    conn.close()

    return {
        "status": "success", 
        "formatted_text": first_block,
        "new_scenes": len(new_scene_ids),
        "tk_count": tk_count
    }
'''

# We remove the old /format-scene and /slice-scene routes and replace with the master route
code = re.sub(r'@router\.post\("/api/binder/format-scene.*?return \{"status": "success", "new_scenes_created": len\(new_scene_ids\)\}', master_triage_route, code, flags=re.DOTALL)

# In case the regex missed due to exact matching, just append if it's not there
if "master_triage_scene" not in code:
    code = code.replace('@router.post("/api/binder/auto-title-scenes")', master_triage_route + '\n@router.post("/api/binder/auto-title-scenes")')

with open("backend/routers/binder.py", "w") as f:
    f.write(code)
print("✅ backend/routers/binder.py updated with 1-Click Master Triage.")
