import sqlite3
import json
import time
import uuid
from pathlib import Path
from backend.database import get_db

def init_db(custom_path: str | Path | None = None) -> None:
    """
    Initializes the authoritative Thedral SQLite Vault.
    Enforces foreign keys, builds FTS5 triggers, runs self-healing schema migrations,
    and seeds initial starter structures if the database is clean.
    """
    conn = get_db(custom_path)
    with conn:
        c = conn.cursor()

        # =====================================================================
        # 1. HIERARCHICAL BINDER TREE
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS binder_nodes (
            id TEXT PRIMARY KEY,
            parent_id TEXT,
            project_id TEXT DEFAULT 'default',
            node_type TEXT NOT NULL, -- 'BOOK', 'CHAPTER', 'SCENE', 'NOTE'
            title TEXT NOT NULL,
            sort_order REAL DEFAULT 10.0,
            synopsis TEXT DEFAULT '',
            content TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            status TEXT DEFAULT 'DRAFT', -- 'TODO', 'DRAFT', 'REVISED', 'FINAL'
            word_count INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            epigraph TEXT DEFAULT '',
            card_data TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(parent_id) REFERENCES binder_nodes(id) ON DELETE CASCADE
        )""")

        # Self-healing migration for binder_nodes
        c.execute("PRAGMA table_info(binder_nodes)")
        existing_node_cols = [r[1] for r in c.fetchall()]
        for col, ctype in [
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
            ("word_count", "INTEGER DEFAULT 0"),
            ("status", "TEXT DEFAULT 'DRAFT'"),
            ("is_archived", "INTEGER DEFAULT 0"),
            ("epigraph", "TEXT DEFAULT ''"),
            ("card_data", "TEXT DEFAULT '{}'")
        ]:
            if col not in existing_node_cols:
                c.execute(f"ALTER TABLE binder_nodes ADD COLUMN {col} {ctype};")

        # =====================================================================
        # 2. SQLITE FTS5 FULL-TEXT SEARCH (Instant Search)
        # =====================================================================
        c.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS binder_fts USING fts5(
            node_id UNINDEXED,
            title,
            content,
            synopsis,
            notes,
            tokenize='porter unicode61'
        )""")

        # Automatic synchronization triggers
        c.execute("""
        CREATE TRIGGER IF NOT EXISTS fts_after_insert AFTER INSERT ON binder_nodes BEGIN
            INSERT INTO binder_fts (node_id, title, content, synopsis, notes)
            VALUES (new.id, new.title, new.content, new.synopsis, new.notes);
        END;""")

        c.execute("""
        CREATE TRIGGER IF NOT EXISTS fts_after_update AFTER UPDATE ON binder_nodes BEGIN
            DELETE FROM binder_fts WHERE node_id = old.id;
            INSERT INTO binder_fts (node_id, title, content, synopsis, notes)
            VALUES (new.id, new.title, new.content, new.synopsis, new.notes);
        END;""")

        c.execute("""
        CREATE TRIGGER IF NOT EXISTS fts_after_delete AFTER DELETE ON binder_nodes BEGIN
            DELETE FROM binder_fts WHERE node_id = old.id;
        END;""")

        # =====================================================================
        # 3. CANONICAL ENTITY DOSSIERS
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS canonical_entities (
            entity_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL, -- 'CHARACTER', 'ITEM', 'LOCATION', 'FACTION'
            role TEXT DEFAULT 'SUPPORTING', -- 'PROTAGONIST', 'ANTAGONIST', 'SUPPORTING', 'MINOR'
            aliases TEXT DEFAULT '', -- Comma-separated: 'Captain, Vance, The Old Crow'
            sensory_profile TEXT DEFAULT '', -- 'Smells of scorched sulfur; clipped vocal rasp'
            status TEXT DEFAULT 'ALIVE', -- 'ALIVE', 'WOUNDED', 'DECEASED', 'UNKNOWN'
            parent_location_id TEXT, -- Geographic hierarchy
            axioms TEXT DEFAULT '{}', -- JSON immutable constraints
            created_at TEXT
        )""")

        # Self-healing migration for canonical_entities
        c.execute("PRAGMA table_info(canonical_entities)")
        existing_ent_cols = [r[1] for r in c.fetchall()]
        for col, ctype in [
            ("role", "TEXT DEFAULT 'SUPPORTING'"),
            ("aliases", "TEXT DEFAULT ''"),
            ("sensory_profile", "TEXT DEFAULT ''"),
            ("status", "TEXT DEFAULT 'ALIVE'"),
            ("parent_location_id", "TEXT"),
            ("created_at", "TEXT")
        ]:
            if col not in existing_ent_cols:
                c.execute(f"ALTER TABLE canonical_entities ADD COLUMN {col} {ctype};")

        # =====================================================================
        # 4. ENTITY RELATIONSHIP GRAPH
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS entity_relationships (
            rel_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            rel_type TEXT NOT NULL, -- 'ALLIED', 'HOSTILE', 'KNOWS_SECRET', 'DEBT_TO', 'ANCESTOR_OF'
            description TEXT DEFAULT '',
            is_secret INTEGER DEFAULT 0,
            updated_at TEXT,
            FOREIGN KEY(source_id) REFERENCES canonical_entities(entity_id) ON DELETE CASCADE,
            FOREIGN KEY(target_id) REFERENCES canonical_entities(entity_id) ON DELETE CASCADE
        )""")

        # =====================================================================
        # 5. EVENT-SOURCED WORLDLINES LEDGER (Append-Only)
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS canonical_worldlines (
            event_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            timeline_tick REAL NOT NULL,
            scene_id TEXT NOT NULL,
            source_span_hash TEXT NOT NULL,
            state_delta TEXT NOT NULL,
            epistemic_tier TEXT NOT NULL, -- 'FACT', 'CLAIM', 'INFERENCE'
            carrier_id TEXT,
            created_at TEXT,
            FOREIGN KEY(entity_id) REFERENCES canonical_entities(entity_id) ON DELETE CASCADE
        )""")

        # =====================================================================
        # 6. STAGED INFERENCE BUFFER (Ghost Surveyor)
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS staged_proposals (
            proposal_id TEXT PRIMARY KEY,
            scene_id TEXT NOT NULL,
            timeline_tick REAL DEFAULT 1.0,
            detected_entity_name TEXT NOT NULL,
            matched_entity_id TEXT,
            proposed_delta TEXT NOT NULL,
            confidence REAL DEFAULT 0.8,
            epistemic_tier TEXT NOT NULL,
            attested_by TEXT,
            source_span_text TEXT NOT NULL,
            collision_warning TEXT,
            status TEXT DEFAULT 'PENDING'
        )""")

        # =====================================================================
        # 7. READER EPISTEMIC HORIZON
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS reader_disclosures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id TEXT,
            chapter_num INTEGER,
            scene_id TEXT,
            disclosure_type TEXT NOT NULL, -- 'DIRECT', 'INFERRED', 'DELAYED'
            narrative_claim TEXT NOT NULL,
            clue_evidence TEXT DEFAULT '',
            target_reveal_ch INTEGER,
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )""")

        # =====================================================================
        # 8. CHEKHOV FORESHADOWING GRAVITY WELLS
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS promises_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT DEFAULT 'default',
            book_id TEXT,
            planted_scene_id TEXT NOT NULL,
            target_volume INTEGER NOT NULL,
            target_tick REAL NOT NULL,
            target_location TEXT DEFAULT '',
            promise_desc TEXT NOT NULL,
            status TEXT DEFAULT 'SEEDED',
            created_at TEXT
        )""")

        # =====================================================================
        # 9. LIVING STYLE SHEET & SERIES LEXICON
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS style_sheet (
            term TEXT PRIMARY KEY,
            category TEXT DEFAULT 'LORE', -- 'CHARACTER_NAME', 'LOCATION', 'SPELLING', 'DIALECT'
            rule_definition TEXT NOT NULL,
            pronunciation TEXT DEFAULT '',
            created_at TEXT
        )""")

        c.execute("PRAGMA table_info(style_sheet)")
        existing_style_cols = [r[1] for r in c.fetchall()]
        for col, ctype in [
            ("rule_definition", "TEXT DEFAULT ''"),
            ("category", "TEXT DEFAULT 'LORE'"),
            ("pronunciation", "TEXT DEFAULT ''")
        ]:
            if col not in existing_style_cols:
                c.execute(f"ALTER TABLE style_sheet ADD COLUMN {col} {ctype};")

        # =====================================================================
        # 10. SUBPLOT THREADS MATRIX
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS story_threads (
            id TEXT PRIMARY KEY,
            project_id TEXT DEFAULT 'default',
            title TEXT NOT NULL,
            thread_type TEXT DEFAULT 'SUBPLOT', -- 'MAIN_PLOT', 'SUBPLOT', 'ROMANCE', 'MYSTERY'
            description TEXT DEFAULT '',
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )""")

        c.execute("""
        CREATE TABLE IF NOT EXISTS scene_threads (
            scene_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            contribution TEXT DEFAULT '',
            PRIMARY KEY(scene_id, thread_id),
            FOREIGN KEY(scene_id) REFERENCES binder_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY(thread_id) REFERENCES story_threads(id) ON DELETE CASCADE
        )""")

        # =====================================================================
        # 11. MOTIF & THEMATIC SYMBOL LEDGER
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS motifs_ledger (
            id TEXT PRIMARY KEY,
            symbol_name TEXT NOT NULL, -- 'Cracked Porcelain Moon', 'Leviathan Bile'
            target_theme TEXT NOT NULL, -- 'Fragility of Human Honor'
            first_planted_scene TEXT,
            notes TEXT DEFAULT '',
            created_at TEXT
        )""")

        # =====================================================================
        # 12. VOICE PROFILES (Aesthetic Registers)
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS voice_profiles (
            profile_id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL UNIQUE, -- 'ellie', 'vance', or 'GLOBAL_NARRATOR'
            pov_name TEXT NOT NULL,
            target_avg_sentence REAL DEFAULT 12.0,
            target_cadence_stdev REAL DEFAULT 5.5,
            allowed_metaphor_domains TEXT DEFAULT '',
            forbidden_lexicon TEXT DEFAULT '',
            signature_sensory_anchors TEXT DEFAULT '',
            canonical_quote_anchor TEXT DEFAULT '',
            updated_at TEXT
        )""")

        # =====================================================================
        # 13. NODE REVISIONS VAULT (Undo/Rollback Snapshots)
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS node_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL,
            version_num INTEGER NOT NULL,
            content TEXT NOT NULL,
            change_summary TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY(node_id) REFERENCES binder_nodes(id) ON DELETE CASCADE
        )""")

        # =====================================================================
        # 14. WRITING SPRINT & VELOCITY LOGS
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS writing_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            words_written INTEGER NOT NULL,
            target_words INTEGER DEFAULT 1000,
            minutes_logged INTEGER DEFAULT 0,
            created_at TEXT
        )""")

        # =====================================================================
        # 15. EDITORIAL CRITIQUE VAULT
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS editorial_critiques (
            id TEXT PRIMARY KEY,
            scene_id TEXT NOT NULL,
            passage_text TEXT NOT NULL,
            critique_text TEXT NOT NULL,
            status TEXT DEFAULT 'OPEN', -- 'OPEN', 'ADDRESSED', 'DISMISSED'
            created_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY(scene_id) REFERENCES binder_nodes(id) ON DELETE CASCADE
        )""")

        # =====================================================================
        # 16. STORY DEADLINES (Event Horizons)
        # =====================================================================
        c.execute("""
        CREATE TABLE IF NOT EXISTS story_deadlines (
            id TEXT PRIMARY KEY,
            book_id TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline_tick REAL NOT NULL,
            urgency_level TEXT DEFAULT 'CRITICAL',
            status TEXT DEFAULT 'ACTIVE',
            created_at TEXT
        )""")

        # =====================================================================
        # PERFORMANCE INDEXES
        # =====================================================================
        c.execute("CREATE INDEX IF NOT EXISTS idx_critique_scene ON editorial_critiques (scene_id, status);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_deadline_book ON story_deadlines (book_id, deadline_tick);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_binder_order ON binder_nodes (parent_id, sort_order);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_worldlines_flow ON canonical_worldlines (entity_id, timeline_tick);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON entity_relationships (source_id);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_revisions_lookup ON node_revisions (node_id, version_num);")

        # =====================================================================
        # INITIAL SEED DATA (If Database is Clean)
        # =====================================================================
        c.execute("SELECT COUNT(*) FROM binder_nodes")
        if c.fetchone()[0] == 0:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            b_id, ch_id, sc_id = "book_1", "ch_1", "scene_1"

            c.execute("""
                INSERT INTO binder_nodes 
                (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, NULL, 'default', 'BOOK', 'Book 1: The Sky Docks', 10.0, 'Volume 1 of Victorian Skies', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
            """, (b_id, ts, ts))

            c.execute("""
                INSERT INTO binder_nodes 
                (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'CHAPTER', 'Chapter 1: The Iron Balcony', 10.0, 'Admiralty Infiltration', '', '', 'DRAFT', 0, 0, '', '{}', ?, ?)
            """, (ch_id, b_id, ts, ts))

            sample_prose = (
                "The outer courtyard bells broke through the clerestory vents, carrying an icy draft "
                "that cut straight down the hall. The runner rug gave out. Bare marble met my soles like frozen iron.\n\n"
                "My lungs locked midway through an exhale. My heel dragged against the flagstones, catching the "
                "door before it swung free by a fraction of an inch."
            )
            sample_card = json.dumps({
                "pov_character": "Ellie",
                "setting": "The Grand Balustrade",
                "narrative_time": 1.0,
                "tension_target": 75
            })

            c.execute("""
                INSERT INTO binder_nodes 
                (id, parent_id, project_id, node_type, title, sort_order, synopsis, content, notes, status, word_count, is_archived, epigraph, card_data, created_at, updated_at)
                VALUES (?, ?, 'default', 'SCENE', 'Scene 1: The Dropped Latch', 10.0, 'Ellie evades the watchmen on the balustrade.', ?, '', 'DRAFT', 68, 0, '', ?, ?, ?)
            """, (sc_id, ch_id, sample_prose, sample_card, ts, ts))

            c.execute("""
                INSERT OR IGNORE INTO canonical_entities 
                (entity_id, name, entity_type, role, aliases, sensory_profile, status, parent_location_id, axioms, created_at)
                VALUES ('ellie', 'Ellie', 'CHARACTER', 'PROTAGONIST', 'The Ghost of Sinks', 'Frost on teeth, tallow smell', 'ALIVE', NULL, ?, ?)
            """, (json.dumps({"health_score": 1.0}), ts))

            c.execute("""
                INSERT OR IGNORE INTO canonical_entities 
                (entity_id, name, entity_type, role, aliases, sensory_profile, status, parent_location_id, axioms, created_at)
                VALUES ('vance', 'Captain Vance', 'CHARACTER', 'SUPPORTING', 'The Captain', 'Clipped naval rasp', 'ALIVE', NULL, ?, ?)
            """, (json.dumps({"health_score": 1.0}), ts))

            c.execute("""
                INSERT OR IGNORE INTO canonical_entities 
                (entity_id, name, entity_type, role, aliases, sensory_profile, status, parent_location_id, axioms, created_at)
                VALUES ('loc_balustrade', 'The Grand Balustrade', 'LOCATION', 'SUPPORTING', '', '', 'ALIVE', NULL, '{}', ?)
            """, (ts,))

            c.execute("""
                INSERT OR IGNORE INTO voice_profiles 
                (profile_id, entity_id, pov_name, target_avg_sentence, target_cadence_stdev, allowed_metaphor_domains, forbidden_lexicon, signature_sensory_anchors, canonical_quote_anchor, updated_at)
                VALUES (
                    'vp_ellie', 'ellie', 'Ellie (First Person / Deep POV)',
                    11.5, 6.2,
                    'Lockpicking, waterfront docks, debt, cold iron, tallow candles, survival mechanics',
                    'strategic options, process her feelings, toxic, evaluate, furthermore, ostensibly',
                    'Frozen marble, copper coins, frayed burlap, locked lungs',
                    'Bare marble met my soles like frozen iron. My lungs locked midway through an exhale.',
                    ?
                )
            """, (ts,))

        c.execute("SELECT COUNT(*) FROM binder_fts")
        if c.fetchone()[0] == 0:
            c.execute("""
                INSERT INTO binder_fts (node_id, title, content, synopsis, notes)
                SELECT id, title, content, synopsis, notes FROM binder_nodes
            """)

    conn.close()