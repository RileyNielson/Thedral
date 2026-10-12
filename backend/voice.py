import re
import math
import sqlite3
from backend.database import get_db
from backend.config import COMMON_ANACHRONISMS


def _ensure_voice_profile(conn: sqlite3.Connection, pov_entity_id: str) -> sqlite3.Row | None:
    """Ensure the voice profile table exists and seed a default entry for a missing POV."""
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='voice_profiles'")
    if c.fetchone() is None:
        c.execute("""
            CREATE TABLE IF NOT EXISTS voice_profiles (
                profile_id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL UNIQUE,
                pov_name TEXT NOT NULL,
                target_avg_sentence REAL DEFAULT 12.0,
                target_cadence_stdev REAL DEFAULT 5.5,
                allowed_metaphor_domains TEXT DEFAULT '',
                forbidden_lexicon TEXT DEFAULT '',
                signature_sensory_anchors TEXT DEFAULT '',
                canonical_quote_anchor TEXT DEFAULT '',
                updated_at TEXT
            )
        """)

    c.execute("SELECT * FROM voice_profiles WHERE entity_id = ?", (pov_entity_id,))
    profile = c.fetchone()
    if profile is None:
        default_profile = {
            "profile_id": f"vp_{pov_entity_id}",
            "entity_id": pov_entity_id,
            "pov_name": pov_entity_id.title(),
            "target_avg_sentence": 11.5,
            "target_cadence_stdev": 6.2,
            "allowed_metaphor_domains": "Lockpicking, waterfront docks, debt, cold iron, tallow candles, survival mechanics",
            "forbidden_lexicon": "strategic options, process her feelings, toxic, evaluate, furthermore, ostensibly",
            "signature_sensory_anchors": "Frozen marble, copper coins, frayed burlap, locked lungs",
            "canonical_quote_anchor": "Bare marble met my soles like frozen iron.",
            "updated_at": None,
        }
        c.execute(
            """
            INSERT INTO voice_profiles (
                profile_id, entity_id, pov_name, target_avg_sentence, target_cadence_stdev,
                allowed_metaphor_domains, forbidden_lexicon, signature_sensory_anchors,
                canonical_quote_anchor, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                default_profile["profile_id"],
                default_profile["entity_id"],
                default_profile["pov_name"],
                default_profile["target_avg_sentence"],
                default_profile["target_cadence_stdev"],
                default_profile["allowed_metaphor_domains"],
                default_profile["forbidden_lexicon"],
                default_profile["signature_sensory_anchors"],
                default_profile["canonical_quote_anchor"],
                default_profile["updated_at"],
            ),
        )
        conn.commit()
        c.execute("SELECT * FROM voice_profiles WHERE entity_id = ?", (pov_entity_id,))
        profile = c.fetchone()
    return profile


def audit_voice_continuity(
    text: str, 
    pov_entity_id: str = "ellie", 
    custom_conn: sqlite3.Connection | None = None
) -> dict:
    """
    Audits scene prose against the character's canonical voice profile:
    - Scans for modern colloquialisms, corporate idioms, and therapy-speak.
    - Flags out-of-register vocabulary from the forbidden lexicon.
    - Measures sentence cadence drift against target sentence length.
    - Computes an overall Voice Continuity Match score (0 to 100%).
    """
    if not text or not text.strip():
        return {
            "voice_match": 100,
            "anachronisms": [],
            "cadence_drift": 0.0,
            "allowed_domains": "",
            "voice_name": "Standard Narrator",
            "feedback": []
        }

    conn = custom_conn if custom_conn else get_db()
    profile = _ensure_voice_profile(conn, pov_entity_id)
    if not custom_conn:
        conn.close()

    # Fallback if no specific profile exists for this entity
    if not profile:
        return {
            "voice_match": 100,
            "anachronisms": [],
            "cadence_drift": 0.0,
            "allowed_domains": "General Fiction",
            "voice_name": pov_entity_id.title(),
            "feedback": []
        }

    text_lower = text.lower()
    feedback = []
    penalty = 0

    # 1. Modern Anachronism & Slang Scan
    detected_anachronisms = []
    for phrase in COMMON_ANACHRONISMS:
        if phrase in text_lower:
            detected_anachronisms.append(phrase)
            penalty += 15
            feedback.append(f"Modern Anachronism: '{phrase}' violates historical/fantasy immersion.")

    # 2. Forbidden Character Lexicon Scan
    forbidden_words = [w.strip() for w in profile["forbidden_lexicon"].split(",") if w.strip()]
    for word in forbidden_words:
        if re.search(r'\b' + re.escape(word.lower()) + r'\b', text_lower):
            penalty += 10
            feedback.append(f"Out-of-Voice Diction: '{word}' contradicts {profile['pov_name']}'s established register.")

    # 3. Sentence Cadence Drift
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]
    
    if lengths:
        avg_len = sum(lengths) / len(lengths)
        variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
        stdev = math.sqrt(variance)
        
        target_avg = float(profile["target_avg_sentence"])
        drift = round(avg_len - target_avg, 1)

        # Flag significant cadence drift (> 5 words off benchmark)
        if abs(drift) > 5.0:
            penalty += 15
            direction = "too long and sluggish" if drift > 0 else "too abrupt and clipped"
            feedback.append(
                f"Rhythm Drift: Sentence average is {avg_len:.1f}w (Target: {target_avg}w). "
                f"The prose has drifted {direction} for this character's voice."
            )
    else:
        drift = 0.0

    voice_match = max(10, 100 - penalty)
    
    return {
        "voice_match": voice_match,
        "anachronisms": detected_anachronisms,
        "cadence_drift": drift,
        "allowed_domains": profile["allowed_metaphor_domains"],
        "voice_name": profile["pov_name"],
        "feedback": feedback
    }
