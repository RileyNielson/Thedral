import re
import math
from backend.config import FILTER_VERBS, CRUTCH_WORDS, TENSION_KEYWORDS
from backend.spectrometer import analyze_neuro_spectrum

# =============================================================================
# ANTI-GIGO COMPOUND IDIOM SHIELD
# Prevents colloquial phrases like "blood-orange" or "fire in his eyes"
# from faking a high-tension crisis.
# =============================================================================

COMPOUND_IDIOM_PATTERNS = [
    r"\bblood[- ]orange\b", r"\bbad blood\b", r"\bblood is thicker\b",
    r"\bflesh and blood\b", r"\bin cold blood\b",
    r"\bfire in (?:his|her|their|my|your) eyes\b", r"\bunder fire\b",
    r"\bspit fire\b", r"\bfireplace\b", r"\bfirewood\b",
    r"\bbored to death\b", r"\bscared to death\b", r"\bdeathly quiet\b",
    r"\bcatch (?:my|his|her) death\b", r"\bdead tired\b", r"\bdead on (?:my|his|her) feet\b",
    r"\bkill time\b", r"\bkill the lights\b", r"\bdressed to kill\b",
    r"\bcold shoulder\b", r"\bcold feet\b", r"\bstone cold\b"
]

def scrub_idioms(text: str) -> str:
    """Masks non-literal idioms so keyword scanners only capture authentic diegetic stakes."""
    scrubbed = text
    for pattern in COMPOUND_IDIOM_PATTERNS:
        scrubbed = re.sub(pattern, " ", scrubbed, flags=re.IGNORECASE)
    return scrubbed

# =============================================================================
# PACING & TELEMETRY ENGINE
# =============================================================================

def calculate_text_telemetry(text: str, prev_tension: float | None = None) -> dict:
    """
    Evaluates Law 1 Pacing Physics, Prose Craft Metrics, and the Neuro-Spectrometer:
    - Tension Elevation Z (Stakes Height: 0.05 to 0.95 with Anti-GIGO Idiom Shield)
    - Cadence Velocity V (Sentence Length Standard Deviation)
    - Pacing Momentum M = V * (1 + delta_Z)
    - Micro Neuro-Narrative Spectrometer (Adrenaline/Oxytocin/Dopamine/Serotonin)
    - Filter Verb and Crutch Word density scans
    """
    if not text or not text.strip():
        return {
            "words": 0, "avg_sentence": 0.0, "cadence_stdev": 0.0,
            "dialogue_ratio": 0.0, "tension_elevation": 0.35,
            "pacing_velocity": 0.0, "pacing_momentum": 0.0,
            "pacing_slope": 0.0, "slope_diagnosis": "STABLE_FLOW",
            "filters": {}, "crutches": {},
            "spectrometer": analyze_neuro_spectrum("")
        }

    words = len(text.split())
    text_lower = text.lower()
    
    # 1. Lexical Scans using centralized config lexicons
    filters_found = {
        v: len(re.findall(r"\b" + v + r"\b", text_lower)) 
        for v in FILTER_VERBS if v in text_lower
    }
    crutches_found = {
        w: len(re.findall(r"\b" + w + r"\b", text_lower)) 
        for w in CRUTCH_WORDS if w in text_lower
    }

    # 2. Cadence Velocity V (Sentence Length Burstiness)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]

    if sentence_lengths:
        avg_len = round(sum(sentence_lengths) / len(sentence_lengths), 1)
        variance = round(sum((x - avg_len) ** 2 for x in sentence_lengths) / len(sentence_lengths), 1)
        stdev = round(math.sqrt(variance), 1)
    else:
        avg_len, stdev = 0.0, 0.0

    # 3. Dialogue Ratio
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    dialogue_paras = sum([1 for p in paragraphs if '"' in p or '“' in p])
    dialogue_ratio = round((dialogue_paras / max(1, len(paragraphs))) * 100, 1)

    # 4. Stakes Elevation Z (0.05 to 0.95) with Idiom Masking
    scrubbed_text_lower = scrub_idioms(text).lower()
    tension_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", scrubbed_text_lower)) for k in TENSION_KEYWORDS)
    tension_density = (tension_hits / max(1, words)) * 1000

    elev = 0.35 + (0.35 * (dialogue_ratio / 100.0)) + min(0.25, tension_density * 0.02)
    if 0 < avg_len < 12: 
        elev += 0.10
    elif avg_len > 22: 
        elev -= 0.10
    tension_elevation = round(max(0.05, min(0.95, elev)), 2)

    # 5. Pacing Momentum & Slope Calculus (Non-prescriptive)
    pacing_slope = 0.0
    slope_diagnosis = "STABLE_FLOW"
    pacing_momentum = stdev

    if prev_tension is not None:
        delta_z = round(tension_elevation - prev_tension, 2)
        pacing_slope = delta_z
        pacing_momentum = round(stdev * (1.0 + delta_z), 1)

        if abs(delta_z) < 0.03 and words > 700:
            slope_diagnosis = "LATERAL_STALL"
        elif delta_z > 0.45:
            slope_diagnosis = "MELODRAMATIC_WHIPLASH"
        elif delta_z > 0.12:
            slope_diagnosis = "RISING_MOMENTUM"
        elif delta_z < -0.15:
            slope_diagnosis = "CATHARTIC_VALLEY"

    return {
        "words": words,
        "avg_sentence": avg_len,
        "cadence_stdev": stdev,
        "dialogue_ratio": dialogue_ratio,
        "tension_elevation": tension_elevation,
        "pacing_velocity": stdev,
        "pacing_momentum": pacing_momentum,
        "pacing_slope": pacing_slope,
        "slope_diagnosis": slope_diagnosis,
        "filters": dict(sorted(filters_found.items(), key=lambda i: i[1], reverse=True)[:5]),
        "crutches": dict(sorted(crutches_found.items(), key=lambda i: i[1], reverse=True)[:5]),
        "spectrometer": analyze_neuro_spectrum(text)
    }

def classify_sentence_energetics(text: str) -> list[dict]:
    """
    Classifies every sentence into an authoritative narrative energy state for the Craft X-Ray:
    - ESCALATOR (Rose): Somatic friction, staccato cadence (<9 words), crisis keywords.
    - RESOLVER (Emerald): Falling cadences (>=22 words), contemplative aftermath, breathing space.
    - PIVOT (Amber): Hinge clauses shifting dramatic direction or complication.
    - SLACK (Dotted): Filter verbs, throat-clearing crutch words, ungrounded drift.
    - NEUTRAL: Grounded expository or narrative baseline.
    """
    if not text or not text.strip():
        return []

    raw_chunks = re.split(r'([.!?]+(?:\s+|\Z))', text)
    sentences = []
    for i in range(0, len(raw_chunks)-1, 2):
        s = raw_chunks[i] + raw_chunks[i+1]
        if s.strip():
            sentences.append(s.strip())
    if len(raw_chunks) % 2 == 1 and raw_chunks[-1].strip():
        sentences.append(raw_chunks[-1].strip())

    classified = []
    for s in sentences:
        words = len(s.split())
        s_lower = s.lower()
        scrubbed_s = scrub_idioms(s).lower()

        has_tension_kw = any(k in scrubbed_s for k in TENSION_KEYWORDS)
        has_somatic = any(v in s_lower for v in [
            "locked", "struck", "skid", "dragged", "snapped", 
            "blood", "frost", "cold", "grip", "teeth", "muscle", "bone"
        ])
        is_staccato = 0 < words <= 8
        is_long = words >= 22
        has_resolver_kw = any(k in s_lower for k in [
            "waited", "quiet", "exhaled", "breathed", "paused", 
            "realized", "sat", "rested", "fade", "stillness"
        ])
        
        is_pivot = bool(re.match(r'^(?:but|yet|the runner rug|suddenly|and then|instead|except|then)\b', s_lower)) or "gave out" in s_lower or "gave way" in s_lower

        filters = [v for v in FILTER_VERBS if re.search(r'\b' + v + r'\b', s_lower)]
        crutches = [w for w in CRUTCH_WORDS if re.search(r'\b' + w + r'\b', s_lower)]

        if is_pivot:
            c_type = "PIVOT"
            reason = "Pivot: Shifts the direction or complication of the beat"
        elif (has_tension_kw or has_somatic) and (is_staccato or has_tension_kw):
            c_type = "ESCALATOR"
            reason = f"Escalator: {'Staccato cadence ' if is_staccato else ''}{'Somatic friction ' if has_somatic else ''}{'Stakes keyword' if has_tension_kw else ''}".strip()
        elif (has_resolver_kw or is_long) and not has_tension_kw:
            c_type = "RESOLVER"
            reason = f"Resolver: {'Falling cadence ' if is_long else ''}{'Contemplative aftermath' if has_resolver_kw else ''}".strip()
        elif len(filters) >= 2 or len(crutches) >= 2:
            c_type = "SLACK"
            reason = f"Narrative Slack: Multiple filter verbs ({', '.join(filters)}) or crutch words"
        else:
            c_type = "NEUTRAL"
            reason = "Grounded exposition / transition"

        classified.append({
            "text": s,
            "type": c_type,
            "reason": reason,
            "words": words
        })

    return classified