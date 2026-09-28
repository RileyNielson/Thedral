import re
import json
import sqlite3
from backend.reducer import get_entity_state_at_tick

def compile_scene_dossier(conn: sqlite3.Connection, scene_id: str) -> dict:
    """
    Compiles an ultra-dense, token-optimized context briefing for local Llama:
    - Active cast, biological health vectors, wounds, inventory, and location anchors
    - Reader Epistemic Horizon (Direct Facts, Inferred Breadcrumbs, Delayed Mysteries)
    - Active Chekhov Gravity Wells in orbit
    - Pertinent Living Style Sheet rules
    - Character Voice & Metaphorical Provenance benchmarks
    """
    c = conn.cursor()

    # 1. Fetch Scene, Parent Chapter, and Book Metadata
    c.execute("""
        SELECT s.id, s.title, s.content, s.synopsis, s.word_count,
               ch.title as chapter_title, b.id as book_id, b.title as book_title
        FROM binder_nodes s
        JOIN binder_nodes ch ON s.parent_id = ch.id
        JOIN binder_nodes b ON ch.parent_id = b.id
        WHERE s.id = ?
    """, (scene_id,))
    scene = c.fetchone()
    if not scene:
        return {}

    content = scene["content"] or ""
    content_lower = content.lower()

    # 2. Detect Active Characters, Nicknames, and Somatic States
    c.execute("""
        SELECT entity_id, name, aliases, sensory_profile, axioms 
        FROM canonical_entities 
        WHERE entity_type = 'CHARACTER'
    """)
    all_chars = c.fetchall()

    active_cast = []
    active_char_entities = []
    for char in all_chars:
        # Build search list of primary name + all registered aliases/nicknames
        names_to_check = [char["name"].lower()]
        if char["aliases"]:
            names_to_check.extend([a.strip().lower() for a in char["aliases"].split(",") if a.strip()])

        matched = any(re.search(r'\b' + re.escape(n) + r'\b', content_lower) for n in names_to_check)
        if matched:
            active_char_entities.append(char["entity_id"])
            state = get_entity_state_at_tick(conn, char["entity_id"], 100.0)
            health = float(state.get("health_score", 1.0))
            held_items = [k.replace("item_", "").title() for k, v in state.items() if "item_" in k and v]
            wounds = [f"{k}: {v}" for k, v in state.items() if "wound" in k or "fracture" in str(v).lower()]

            active_cast.append({
                "name": char["name"],
                "health": f"{int(health * 100)}%",
                "wounds": wounds,
                "items": held_items,
                "sensory_tell": char["sensory_profile"]
            })

    # 3. Pull Applicable Style Sheet Rules
    c.execute("SELECT term, category, rule_definition, pronunciation FROM style_sheet")
    all_rules = c.fetchall()
    matched_rules = []
    for r in all_rules:
        if re.search(r'\b' + re.escape(r["term"].lower()) + r'\b', content_lower):
            phonetic = f" [{r['pronunciation']}]" if r["pronunciation"] else ""
            matched_rules.append(f"{r['term']}{phonetic}: {r['rule_definition']}")

    # 4. Pull Reader Epistemic Horizon for this Scene
    c.execute("""
        SELECT disclosure_type, narrative_claim, clue_evidence 
        FROM reader_disclosures 
        WHERE scene_id = ?
    """, (scene_id,))
    disclosures = c.fetchall()

    direct_facts = [d["narrative_claim"] for d in disclosures if d["disclosure_type"] == "DIRECT"]
    inferred_clues = [d["narrative_claim"] for d in disclosures if d["disclosure_type"] == "INFERRED"]
    delayed_mysteries = [d["narrative_claim"] for d in disclosures if d["disclosure_type"] == "DELAYED"]

    # 5. Pull Active Chekhov Gravity Wells (Foreshadowing)
    c.execute("""
        SELECT promise_desc, target_volume, status 
        FROM promises_ledger 
        WHERE book_id = ? AND status IN ('SEEDED', 'ORBITING')
    """, (scene["book_id"],))
    chekhov_wells = [f"{p['promise_desc']} (Target: Book {p['target_volume']})" for p in c.fetchall()]

    # 6. Pull POV Voice & Metaphorical Provenance Benchmark
    voice_briefing = ""
    primary_eid = active_char_entities[0] if active_char_entities else None
    vp = None
    if primary_eid:
        c.execute("SELECT * FROM voice_profiles WHERE entity_id = ? LIMIT 1", (primary_eid,))
        vp = c.fetchone()
    if not vp:
        # Fallback to the first registered voice profile in this book/project
        c.execute("SELECT * FROM voice_profiles LIMIT 1")
        vp = c.fetchone()

    if vp:
        voice_briefing = f"""POV VOICE CONTINUITY BENCHMARK ({vp['pov_name']}):
• Target Sentence Average: {vp['target_avg_sentence']} words (Cadence StDev: {vp['target_cadence_stdev']})
• Permitted Metaphor Fields: {vp['allowed_metaphor_domains']}
• Signature Sensory Anchors: {vp['signature_sensory_anchors']}
• Gold-Standard Quote Anchor: "{vp['canonical_quote_anchor']}"
• STRICT RULE: Flag any modern idioms or metaphors drawn outside their lived experience."""

    # Assemble into a clean, token-dense briefing text
    cast_briefing = "\n".join([
        f"• {ch['name']} [Vitality: {ch['health']} | Wounds: {', '.join(ch['wounds']) or 'None'} | Carrying: {', '.join(ch['items']) or 'None'} | Vocal Tell: {ch['sensory_tell'] or 'Standard'}]"
        for ch in active_cast
    ]) or "• No registered entities explicitly detected in scene text."

    briefing_text = f"""=== OMNISCIENT CONTEXT DOSSIER ===
CANONICAL LOCATION: {scene['chapter_title']}
ACTIVE CAST & SOMATIC STATES:
{cast_briefing}

ACTIVE STYLE SHEET RULES:
{chr(10).join(['• ' + r for r in matched_rules]) or '• None triggered.'}

READER EPISTEMIC HORIZON (WHAT THE READER CURRENTLY KNOWS):
• Direct Ground Truths: {', '.join(direct_facts) or 'None explicitly established.'}
• Inferred Subtext/Clues: {', '.join(inferred_clues) or 'None planted.'}
• Active Unresolved Mysteries: {', '.join(delayed_mysteries) or 'None active.'}

CHEKHOV GRAVITY WELLS (FORESHADOWING IN ORBIT):
{chr(10).join(['• ' + w for w in chekhov_wells]) or '• None orbiting.'}

{voice_briefing}
=================================="""

    return {
        "briefing_text": briefing_text,
        "active_cast": active_cast,
        "matched_rules": matched_rules,
        "scene_meta": {
            "title": scene["title"],
            "chapter": scene["chapter_title"],
            "book": scene["book_title"],
            "words": scene["word_count"]
        }
    }
