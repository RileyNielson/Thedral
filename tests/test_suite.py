"""
Thedral Sovereign Studio — Master Architecture Verification Suite
Executes end-to-end integration tests across:
1. SQLite WAL & FTS5 Synchronization Triggers
2. Span-Linked Semantic Hashing & Severed Thread Detection
3. Law 1 Pacing Physics & Sentence Energetics (Craft X-Ray)
4. Clutter Shield & Entity Taxonomy Guardrails
5. 8-Layer 3D Cosmograph & Chapter Beat Micro-Lens
6. Scrivener & Word Importer Paragraph Normalization
7. Voice Profile & Modern Anachronism Detection
8. FastAPI Router Endpoints & Cryptographic Authorship Proof
"""

import sys
import os
import re
import json
import sqlite3
import tempfile
from pathlib import Path

# Add project root and current directory to Python sys.path
current_dir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
for p in [project_root, current_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Terminal formatting
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
HEADER = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

tests_run = 0
tests_passed = 0

def record_test(name: str, passed: bool, detail: str = ""):
    global tests_run, tests_passed
    tests_run += 1
    if passed:
        tests_passed += 1
        print(f" {PASS} {name}")
    else:
        print(f" {FAIL} {name} — {detail}")

print(f"\n{BOLD}{HEADER}==============================================================================={RESET}")
print(f"{BOLD}{HEADER}       THEDRAL MASTER ARCHITECTURE VERIFICATION MEGA-SUITE                      {RESET}")
print(f"{BOLD}{HEADER}==============================================================================={RESET}\n")

# =============================================================================
# 1. DATABASE & FTS5 INTEGRATION
# =============================================================================
print(f"{BOLD}1. Database Engine, Migrations, & FTS5 Instant Search{RESET}")

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
    test_db_path = tmp.name

try:
    from backend.models import init_db
    from backend.database import get_db

    init_db(test_db_path)
    conn = get_db(test_db_path)
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]
    required_tables = [
        "binder_nodes", "binder_fts", "canonical_entities", "canonical_worldlines",
        "entity_relationships", "style_sheet", "node_revisions", "promises_ledger"
    ]
    all_tables_present = all(t in tables for t in required_tables)
    record_test("Database Schema & Self-Healing Migrations", all_tables_present)

    c.execute("""
        INSERT INTO binder_nodes (id, parent_id, node_type, title, content, sort_order)
        VALUES ('test_scene_1', NULL, 'SCENE', 'The Iron Balcony', 'Vance checked the bronze pressure gauge.', 10.0)
    """)
    conn.commit()

    c.execute("SELECT node_id FROM binder_fts WHERE binder_fts MATCH 'gauge'")
    fts_match = c.fetchone()
    record_test("SQLite FTS5 Automated Insertion Trigger", fts_match is not None and fts_match[0] == 'test_scene_1')

    c.execute("UPDATE binder_nodes SET content = 'The clockwork automaton whirred.' WHERE id = 'test_scene_1'")
    conn.commit()
    c.execute("SELECT node_id FROM binder_fts WHERE binder_fts MATCH 'automaton'")
    fts_update_match = c.fetchone()
    c.execute("SELECT node_id FROM binder_fts WHERE binder_fts MATCH 'gauge'")
    old_gauge_match = c.fetchone()
    record_test("SQLite FTS5 Automated Update Trigger (Old Term Purged)", fts_update_match is not None and old_gauge_match is None)

    conn.close()
finally:
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

# =============================================================================
# 2. SPAN-LINKED CAUSALITY & SEVERED THREADS
# =============================================================================
print(f"\n{BOLD}2. Span-Linked Semantic Hashing & Severed Thread Detection{RESET}")

from backend.hashing import compute_block_hash, get_scene_block_hashes, find_severed_threads

p1 = "Bare marble met my soles like frozen iron. My lungs locked midway through an exhale."
p2 = "Captain Vance dropped the brass cylinder onto the desk."

h1 = compute_block_hash(p1)
h2 = compute_block_hash(p2)

p1_typo = "bare marble met my soles like frozen iron! my lungs locked midway through an exhale"
h1_typo = compute_block_hash(p1_typo)

record_test("Semantic Block Hashing Generates 16-Char Hex", len(h1) == 16 and len(h2) == 16)
record_test("Punctuation & Case Normalized Invariance", h1 == h1_typo)

test_conn = sqlite3.connect(":memory:")
test_conn.row_factory = sqlite3.Row
test_conn.execute("""
    CREATE TABLE canonical_worldlines (
        event_id TEXT PRIMARY KEY,
        entity_id TEXT,
        timeline_tick REAL,
        scene_id TEXT,
        source_span_hash TEXT,
        state_delta TEXT,
        epistemic_tier TEXT
    )
""")
test_conn.execute("""
    INSERT INTO canonical_worldlines VALUES ('ev_1', 'vance', 1.0, 'sc_1', ?, '{"health": 0.5}', 'FACT')
""", (h2,))

severed_before = find_severed_threads(test_conn, 'sc_1', f"{p1}\n\n{p2}")
record_test("Intact Paragraph Generates Zero Severed Threads", len(severed_before) == 0)

severed_after = find_severed_threads(test_conn, 'sc_1', p1)
record_test("Excising Paragraph Detects Severed Causal Thread", len(severed_after) == 1 and severed_after[0]["entity_id"] == "vance")
test_conn.close()

# =============================================================================
# 3. CRAFT X-RAY & PACING TELEMETRY
# =============================================================================
print(f"\n{BOLD}3. Law 1 Pacing Physics & Craft X-Ray Sentence Energetics{RESET}")

from backend.telemetry import calculate_text_telemetry, classify_sentence_energetics

sample_prose = (
    "The outer courtyard bells broke through the clerestory vents. "
    "Bare marble met my soles like frozen iron. "
    "My lungs locked midway through an exhale! "
    "\"Where is the ledger?\" Vance whispered. "
    "I saw that he appeared to decide to watch the door slightly frowned."
)

telemetry = calculate_text_telemetry(sample_prose)
record_test("Cadence Velocity & Sentence Standard Deviation", telemetry["cadence_stdev"] > 0)
record_test("Dialogue Ratio Calculation", telemetry["dialogue_ratio"] > 0)
record_test("Filter Verbs & Crutch Words Scanning", len(telemetry["filters"]) >= 2 and len(telemetry["crutches"]) >= 1)

xray = classify_sentence_energetics(sample_prose)
types_found = {s["type"] for s in xray}
record_test("Craft X-Ray Classifies Energetics (Escalators/Slack/Pivots)", "ESCALATOR" in types_found and "SLACK" in types_found)

# =============================================================================
# 4. CLUTTER SHIELD & ENTITY TAXONOMY
# =============================================================================
print(f"\n{BOLD}4. Clutter Shield & Entity Verification{RESET}")

from backend.guardrails import is_valid_character_name, sanitize_entity_type

record_test("Valid Character Allowed (Ellie)", is_valid_character_name("Ellie"))
record_test("Valid Character Allowed (Lord Malakor)", is_valid_character_name("Lord Malakor"))
record_test("Clutter Shield Blocks Common Nouns (Meat Pie)", not is_valid_character_name("Meat Pie"))
record_test("Clutter Shield Blocks Furniture (Crutches)", not is_valid_character_name("Crutches"))
record_test("Clutter Shield Blocks Generic Mobs (Guards)", not is_valid_character_name("The Guards"))

record_test("Sanitize Demotes Clutter to CLUTTER", sanitize_entity_type("Lantern") == "CLUTTER")
record_test("Sanitize Preserves Legitimate Character", sanitize_entity_type("Captain Vance", "CHARACTER") == "CHARACTER")

# =============================================================================
# 5. 3D ASTROLABE (COSMOGRAPH & CHAPTER LENS)
# =============================================================================
print(f"\n{BOLD}5. 8-Layer Spacetime Cosmograph & Beat-Level Chapter Lens{RESET}")

from backend.astrolabe import build_astrolabe_manifest

astro_conn = sqlite3.connect(":memory:")
astro_conn.row_factory = sqlite3.Row
astro_conn.execute("""
    CREATE TABLE binder_nodes (
        id TEXT PRIMARY KEY, parent_id TEXT, project_id TEXT DEFAULT 'default',
        node_type TEXT, title TEXT, sort_order REAL, content TEXT, word_count INTEGER,
        is_archived INTEGER DEFAULT 0
    )
""")
astro_conn.execute("""
    CREATE TABLE entity_relationships (source_id TEXT, target_id TEXT, rel_type TEXT, description TEXT)
""")
astro_conn.execute("""
    CREATE TABLE canonical_worldlines (
        event_id TEXT PRIMARY KEY, entity_id TEXT, timeline_tick REAL, scene_id TEXT,
        source_span_hash TEXT, state_delta TEXT, epistemic_tier TEXT, carrier_id TEXT
    )
""")
astro_conn.execute("""
    CREATE TABLE canonical_entities (entity_id TEXT PRIMARY KEY, name TEXT, entity_type TEXT, aliases TEXT)
""")
astro_conn.execute("""
    CREATE TABLE promises_ledger (id INTEGER PRIMARY KEY, series_id TEXT, book_id TEXT, planted_scene_id TEXT, target_volume INTEGER, target_tick REAL, target_location TEXT, promise_desc TEXT, status TEXT)
""")

astro_conn.execute("INSERT INTO binder_nodes VALUES ('book_1', NULL, 'default', 'BOOK', 'Book One', 10.0, '', 0, 0)")
astro_conn.execute("INSERT INTO binder_nodes VALUES ('ch_1', 'book_1', 'default', 'CHAPTER', 'Chapter One', 10.0, '', 0, 0)")
three_beat_prose = (
    "She considered the silent docks and wondered what had happened to the light.\n\n"
    "\"Drop the weapon!\" the guard shouted, stepping forward.\n\n"
    "Cold steel cleaved through the night air. Blood hissed upon the flagstones."
)
astro_conn.execute("""
    INSERT INTO binder_nodes VALUES ('sc_1', 'ch_1', 'default', 'SCENE', 'The Confrontation', 10.0, ?, 36, 0)
""", (three_beat_prose,))
astro_conn.commit()

macro_manifest = build_astrolabe_manifest(astro_conn, book_id='book_1')
record_test("Macro Cosmograph Generates 3D Topography Traces", len(macro_manifest["data"]) >= 1)

micro_manifest = build_astrolabe_manifest(astro_conn, chapter_id='ch_1', focus_scene_id='sc_1')
beats_trace = micro_manifest["data"][0] if micro_manifest["data"] else {}
num_beats = len(beats_trace.get("x", []))
record_test("Chapter Lens Maps Paragraph Beats (Not 1 Dot)", num_beats == 3)
record_test("Chapter Lens Maps 3 Dramatic Channels (Interior/Dialogue/Action)", set(beats_trace.get("y", [])) == {0.0, 1.0, 2.0})

astro_conn.close()

# =============================================================================
# 6. SCRIVENER & TEXT IMPORTER NORMALIZATION
# =============================================================================
# =============================================================================
# 6. SCRIVENER & TEXT IMPORTER NORMALIZATION
# =============================================================================
print(f"\n{BOLD}6. Importer Paragraph Normalization & Scene Assembly{RESET}")

from backend.importer import normalize_paragraphs, build_binder_from_manifest

single_newline_rtf = "Line one of paragraph.\nLine two of paragraph that continues.\nAnother distinct paragraph entirely."
paras = normalize_paragraphs(single_newline_rtf)
record_test("Normalizes textutil Single-Newline Streams", len(paras) == 3)

mock_manifest = {
    "manuscript": [
        ("Chapter: Act I", True, "Act I", "", ""),
        ("### SCENE_TITLE: The Infiltration", False, "The Infiltration", "Ellie slips in.", "Keep pacing tight."),
        ("Beat one prose.", False, "The Infiltration", "", ""),
        ("Beat two prose.", False, "The Infiltration", "", "")
    ],
    "characters": [{"name": "Ellie", "bio": "Master of locks.", "synopsis": "Tallow smell"}],
    "locations": [{"name": "Aethelgard Docks", "desc": "Salt and cold iron."}],
    "lore": [{"term": "Aetherite", "definition": "Volatile blue crystal."}]
}

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_import:
    import_db_path = tmp_import.name

try:
    from backend.models import init_db
    init_db(import_db_path)

    import backend.importer
    backend.importer.get_db = lambda: sqlite3.connect(import_db_path)

    first_scene_id = build_binder_from_manifest(mock_manifest, "Test Import Project")

    # Re-open fresh connection to verify data was committed to disk
    verify_conn = sqlite3.connect(import_db_path)
    verify_conn.row_factory = sqlite3.Row
    c = verify_conn.cursor()

    c.execute("SELECT synopsis, notes, content FROM binder_nodes WHERE id = ?", (first_scene_id,))
    sc_row = c.fetchone()

    c.execute("SELECT name FROM canonical_entities WHERE entity_id = 'ellie'")
    ent_row = c.fetchone()

    c.execute("SELECT term FROM style_sheet WHERE term = 'Aetherite'")
    lore_row = c.fetchone()

    record_test("Importer Commits Scenes with Preserved Synopses & Notes", sc_row is not None and sc_row["synopsis"] == "Ellie slips in." and "Beat two prose." in sc_row["content"])
    record_test("Importer Extracts Character Sheets to Cast Directory", ent_row is not None and ent_row["name"] == "Ellie")
    record_test("Importer Extracts Worldbuilding to Living Style Sheet", lore_row is not None and lore_row["term"] == "Aetherite")

    verify_conn.close()
finally:
    if os.path.exists(import_db_path):
        os.remove(import_db_path)

# =============================================================================
# 7. VOICE PROFILE & ANACHRONISM AUDITOR
# =============================================================================
print(f"\n{BOLD}7. Voice Profile & Anachronism Detection{RESET}")

from backend.voice import audit_voice_continuity

modern_text = "Ellie realized this toxic relationship was a red flag and had no bandwidth to circle back."
voice_audit = audit_voice_continuity(modern_text, pov_entity_id="ellie")
record_test("Detects Modern Anachronisms (Red Flag, Bandwidth, Toxic)", len(voice_audit["anachronisms"]) >= 3)
record_test("Deducts Voice Match Score for Dialect Contamination", voice_audit["voice_match"] < 80)

# =============================================================================
# 8. FASTAPI REST API CONTRACTS
# =============================================================================
print(f"\n{BOLD}8. FastAPI Router API Contracts & Endpoints{RESET}")

from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

net_res = client.get("/api/network_info")
record_test("GET /api/network_info Returns Local LAN IP", net_res.status_code == 200 and "url" in net_res.json())

tree_res = client.get("/api/tree")
record_test("GET /api/tree Returns Hierarchical Binder", tree_res.status_code == 200 and isinstance(tree_res.json(), list))

entities_res = client.get("/api/entities")
record_test("GET /api/entities Returns Canonical Cast", entities_res.status_code == 200 and isinstance(entities_res.json(), list))

lore_res = client.get("/api/lore")
record_test("GET /api/lore Returns Living Lexicon", lore_res.status_code == 200 and isinstance(lore_res.json(), list))

authorship_res = client.get("/api/publishing/authorship-proof")
record_test("GET /api/publishing/authorship-proof Generates Cryptographic Hash", authorship_res.status_code == 200 and "verification_hash" in authorship_res.json())

# =============================================================================
# SUMMARY REPORT
# =============================================================================
print(f"\n{BOLD}{HEADER}==============================================================================={RESET}")
if tests_passed == tests_run:
    print(f"{BOLD}\033[92m✨ MASTER VERIFICATION COMPLETE: ALL {tests_run}/{tests_run} TESTS PASSED!{RESET}")
    print(f"{BOLD}Thedral sovereign core is stable, verified, and ready for Git.{RESET}")
else:
    print(f"{BOLD}\033[91m⚠️ VERIFICATION INCOMPLETE: {tests_passed}/{tests_run} passed.{RESET}")
print(f"{BOLD}{HEADER}==============================================================================={RESET}\n")