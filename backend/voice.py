import re
import math
import sqlite3
from backend.database import get_db
from backend.config import COMMON_ANACHRONISMS

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
    c = conn.cursor()
    c.execute("SELECT * FROM voice_profiles WHERE entity_id = ?", (pov_entity_id,))
    profile = c.fetchone()
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
