import re
import math
from backend.config import TENSION_KEYWORDS, FILTER_VERBS

# =============================================================================
# 1. NEUROCHEMICAL LEXICONS & SYNTACTIC VECTORS
# =============================================================================

OXYTOCIN_KEYWORDS = [
    "gaze", "eyes", "breath", "pulse", "fingers", "touch", "hand", "skin",
    "whisper", "throat", "heart", "lips", "heat", "cold", "blush", "shiver",
    "closer", "together", "kiss", "embrace", "hesitated", "looked away", "softly"
]

DOPAMINE_KEYWORDS = [
    "why", "how", "secret", "truth", "lie", "lied", "hidden", "found",
    "discovered", "clue", "cipher", "puzzle", "lock", "key", "curious",
    "suspicious", "knew", "suspected", "strange", "shadow", "unseen", "behind"
]

SEROTONIN_KEYWORDS = [
    "scent", "smell", "sound", "light", "shadow", "ancient", "stone", "sky",
    "wind", "rain", "fog", "mist", "cold", "frozen", "silence", "echo",
    "vast", "distant", "memory", "years", "night", "stars", "water", "sea"
]

CANONICAL_COMPS = [
    {
        "author": "Robin Hobb",
        "description": "Character-first somatic fantasy with deep relational and physical stakes.",
        "vector": {"adrenaline": 0.22, "oxytocin": 0.44, "dopamine": 0.14, "serotonin": 0.20}
    },
    {
        "author": "Madeline Miller",
        "description": "Intimate mythic lyrical immersion with high emotional vulnerability.",
        "vector": {"adrenaline": 0.14, "oxytocin": 0.38, "dopamine": 0.10, "serotonin": 0.38}
    },
    {
        "author": "Brandon Sanderson",
        "description": "High-dopamine deductive magic systems with structured kinetic climaxes.",
        "vector": {"adrenaline": 0.36, "oxytocin": 0.14, "dopamine": 0.34, "serotonin": 0.16}
    },
    {
        "author": "Lee Child",
        "description": "Staccato kinetic survival with pure procedural momentum and zero sentiment.",
        "vector": {"adrenaline": 0.62, "oxytocin": 0.08, "dopamine": 0.22, "serotonin": 0.08}
    },
    {
        "author": "Agatha Christie",
        "description": "Deductive information puzzles driven by social manners and epistemic traps.",
        "vector": {"adrenaline": 0.12, "oxytocin": 0.20, "dopamine": 0.56, "serotonin": 0.12}
    },
    {
        "author": "Cormac McCarthy",
        "description": "Severe parataxis, visceral concrete nouns, and heavy existential weight.",
        "vector": {"adrenaline": 0.38, "oxytocin": 0.06, "dopamine": 0.12, "serotonin": 0.44}
    }
]

# =============================================================================
# 2. THE SPECTROMETRY ENGINE
# =============================================================================

def analyze_neuro_spectrum(text: str) -> dict:
    """
    Computes the 4-channel neurochemical fingerprint of any prose block:
    - Adrenaline (Kinetic Survival)
    - Oxytocin (Relational Vulnerability)
    - Dopamine (Deductive Curiosity)
    - Serotonin (Aesthetic Immersion)
    """
    if not text or not text.strip():
        return {
            "adrenaline": 25, "oxytocin": 25, "dopamine": 25, "serotonin": 25,
            "hunger_alert": "Prose empty. No neurochemical signal detected.",
            "hunger_severity": "NEUTRAL"
        }

    words = len(text.split())
    text_lower = text.lower()

    # Sentence boundary analysis
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]

    # Paragraphs for dialogue measurement
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    dialogue_paras = sum([1 for p in paragraphs if '"' in p or '“' in p])
    dialogue_ratio = dialogue_paras / max(1, len(paragraphs))

    # 1. Adrenaline (Kinetic Survival): Staccato clauses + Action keywords
    staccato_count = sum([1 for l in sentence_lengths if l <= 8])
    staccato_weight = (staccato_count / max(1, len(sentence_lengths))) * 40.0
    action_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", text_lower)) for k in TENSION_KEYWORDS)
    raw_adrenaline = staccato_weight + (action_hits * 5.0)

    # 2. Oxytocin (Relational Vulnerability): Dialogue velocity + Intimate somatic proximity
    dialogue_weight = dialogue_ratio * 40.0
    intimate_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", text_lower)) for k in OXYTOCIN_KEYWORDS)
    raw_oxytocin = dialogue_weight + (intimate_hits * 4.0)

    # 3. Dopamine (Deductive Mystery): Questions + Epistemic markers + Ellipses
    question_count = len(re.findall(r'\?', text)) * 6.0
    ellipsis_count = len(re.findall(r'\.{3}|…', text)) * 4.0
    mystery_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", text_lower)) for k in DOPAMINE_KEYWORDS)
    raw_dopamine = question_count + ellipsis_count + (mystery_hits * 4.5)

    # 4. Serotonin (Aesthetic Immersion): Expanded syntax + Atmospheric sensory grounding
    expanded_count = sum([1 for l in sentence_lengths if l >= 22])
    expanded_weight = (expanded_count / max(1, len(sentence_lengths))) * 35.0
    sensory_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", text_lower)) for k in SEROTONIN_KEYWORDS)
    raw_serotonin = expanded_weight + (sensory_hits * 3.5)

    # Normalize to 100%
    total_raw = max(1.0, raw_adrenaline + raw_oxytocin + raw_dopamine + raw_serotonin)
    adr = round((raw_adrenaline / total_raw) * 100)
    oxy = round((raw_oxytocin / total_raw) * 100)
    dop = round((raw_dopamine / total_raw) * 100)
    ser = max(0, 100 - (adr + oxy + dop))

    # Evaluate Reader Hunger & Fatigue Vectors
    alert = "Neurochemical Equilibrium: Balanced dramatic and sensory flow."
    severity = "NEUTRAL"

    if adr >= 55 and oxy <= 15:
        alert = "Adrenaline Saturation: Sustained combat/action pressure. Reader is craving an intimate relational or decompression beat."
        severity = "WARNING"
    elif oxy >= 60 and adr <= 12:
        alert = "Social Stagnation: Extended dialogue exchange. Prose is starving for physical stakes or an irreversible consequence."
        severity = "WARNING"
    elif ser >= 55 and (adr + oxy) <= 25:
        alert = "Sensory Overload: High aesthetic immersion, but forward kinetic threat has flatlined."
        severity = "WARNING"
    elif dop <= 8 and words > 500:
        alert = "Dopamine Starvation: Zero unresolved mysteries, clues, or dramatic irony gaps detected in this beat."
        severity = "CAUTION"

    return {
        "adrenaline": adr,
        "oxytocin": oxy,
        "dopamine": dop,
        "serotonin": ser,
        "hunger_alert": alert,
        "hunger_severity": severity
    }

def calculate_manuscript_comps(macro_spectrum: dict) -> list[dict]:
    """Computes cosine similarity between book's macro vector and canonical author benchmarks."""
    v_norm = {
        "adrenaline": macro_spectrum["adrenaline"] / 100.0,
        "oxytocin": macro_spectrum["oxytocin"] / 100.0,
        "dopamine": macro_spectrum["dopamine"] / 100.0,
        "serotonin": macro_spectrum["serotonin"] / 100.0
    }

    results = []
    for comp in CANONICAL_COMPS:
        cv = comp["vector"]
        dot = sum(v_norm[k] * cv[k] for k in v_norm)
        mag1 = math.sqrt(sum(v_norm[k]**2 for k in v_norm))
        mag2 = math.sqrt(sum(cv[k]**2 for k in cv))
        similarity = dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0.0
        match_pct = round(similarity * 100)
        results.append({
            "author": comp["author"],
            "description": comp["description"],
            "match_pct": min(98, max(40, match_pct))
        })

    results.sort(key=lambda x: x["match_pct"], reverse=True)
    return results[:3]