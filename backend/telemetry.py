import re
import math
from backend.config import FILTER_VERBS, CRUTCH_WORDS, TENSION_KEYWORDS
from backend.spectrometer import (
    analyze_neuro_spectrum, OXYTOCIN_KEYWORDS, 
    DOPAMINE_KEYWORDS, SEROTONIN_KEYWORDS
)

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
    scrubbed = text
    for pattern in COMPOUND_IDIOM_PATTERNS:
        scrubbed = re.sub(pattern, " ", scrubbed, flags=re.IGNORECASE)
    return scrubbed

def calculate_text_telemetry(text: str, prev_tension: float | None = None) -> dict:
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
    
    filters_found = {
        v: len(re.findall(r"\b" + v + r"\b", text_lower)) 
        for v in FILTER_VERBS if v in text_lower
    }
    crutches_found = {
        w: len(re.findall(r"\b" + w + r"\b", text_lower)) 
        for w in CRUTCH_WORDS if w in text_lower
    }

    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    sentence_lengths = [len(s.split()) for s in sentences if len(s.split()) > 0]

    if sentence_lengths:
        avg_len = round(sum(sentence_lengths) / len(sentence_lengths), 1)
        variance = round(sum((x - avg_len) ** 2 for x in sentence_lengths) / len(sentence_lengths), 1)
        stdev = round(math.sqrt(variance), 1)
    else:
        avg_len, stdev = 0.0, 0.0

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    dialogue_paras = sum([1 for p in paragraphs if '"' in p or '“' in p])
    dialogue_ratio = round((dialogue_paras / max(1, len(paragraphs))) * 100, 1)

    scrubbed_text_lower = scrub_idioms(text).lower()
    tension_hits = sum(len(re.findall(r"\b" + re.escape(k) + r"\b", scrubbed_text_lower)) for k in TENSION_KEYWORDS)
    tension_density = (tension_hits / max(1, words)) * 1000

    elev = 0.35 + (0.35 * (dialogue_ratio / 100.0)) + min(0.25, tension_density * 0.02)
    if 0 < avg_len < 12: 
        elev += 0.10
    elif avg_len > 22: 
        elev -= 0.10
    tension_elevation = round(max(0.05, min(0.95, elev)), 2)

    pacing_slope = 0.0
    slope_diagnosis = "STABLE_FLOW"
    pacing_momentum = stdev

    if prev_tension is not None:
        delta_z = round(tension_elevation - prev_tension, 2)
        pacing_slope = delta_z
        pacing_momentum = round(stdev * (1.0 + delta_z), 1)

        if abs(delta_z) < 0.03 and words > 700:
            slope_diagnosis = "SUSTAINED_BASELINE"
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

# =============================================================================
# MULTI-LENS SENTENCE ENERGETICS & TELEMETRY CLASSIFIER
# =============================================================================

def highlight_clutter_words(sentence_text: str) -> tuple[str, list, list]:
    """Wraps exact filter verbs and crutch words in HTML span tags."""
    filters_hit = []
    crutches_hit = []
    html = sentence_text

    for v in FILTER_VERBS:
        pat = re.compile(r"\b(" + re.escape(v) + r")\b", re.IGNORECASE)
        if pat.search(sentence_text):
            filters_hit.append(v)
            html = pat.sub(r'<span class="clutter-filter">\1</span>', html)

    for w in CRUTCH_WORDS:
        pat = re.compile(r"\b(" + re.escape(w) + r")\b", re.IGNORECASE)
        if pat.search(sentence_text):
            crutches_hit.append(w)
            html = pat.sub(r'<span class="clutter-crutch">\1</span>', html)

    return html, filters_hit, crutches_hit

def classify_multi_lens_sentence(s: str) -> dict:
    words = len(s.split())
    s_lower = s.lower()
    scrubbed_s = scrub_idioms(s).lower()

    # 1. LENS: ENERGETICS (Pacing Physics)
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
    has_mystery_kw = any(k in s_lower for k in DOPAMINE_KEYWORDS)
    is_pivot = bool(re.match(r'^(?:but|yet|the runner rug|suddenly|and then|instead|except|then)\b', s_lower)) or "gave out" in s_lower or "gave way" in s_lower

    filters_in_s = [v for v in FILTER_VERBS if re.search(r'\b' + v + r'\b', s_lower)]
    crutches_in_s = [w for w in CRUTCH_WORDS if re.search(r'\b' + w + r'\b', s_lower)]

    if is_pivot:
        energetics_type = "PIVOT"
        energetics_reason = "🟡 Turning Hinge: Shifts dramatic direction or complicates the scene"
    elif (has_tension_kw or has_somatic) and (is_staccato or has_tension_kw):
        energetics_type = "ESCALATOR"
        energetics_reason = f"🔴 Staccato Impact ({words}w): Tightens physical pressure and heart rate"
    elif (has_resolver_kw or is_long) and not has_tension_kw:
        energetics_type = "RESOLVER"
        intrigue_note = " • Carries narrative intrigue ('secret')" if has_mystery_kw else ""
        energetics_reason = f"🟢 Lyrical Flow ({words}w): Dilation / Breathing room for reflection{intrigue_note}"
    elif len(filters_in_s) >= 2 or len(crutches_in_s) >= 2:
        energetics_type = "SLACK"
        energetics_reason = f"⚪ Clutter / Slack: Multiple filter verbs ({', '.join(filters_in_s)}) weaken psychic distance"
    else:
        energetics_type = "NEUTRAL"
        energetics_reason = f"Grounded Baseline ({words}w): Clean narrative backbone (60-70% of healthy prose)"

    # 2. LENS: NEURO-SPECTRUM (Emotional Fuel)
    has_oxytocin = any(k in s_lower for k in OXYTOCIN_KEYWORDS) or ('"' in s or '“' in s)
    has_dopamine = any(k in s_lower for k in DOPAMINE_KEYWORDS) or '?' in s or '...' in s or '…' in s
    has_serotonin = any(k in s_lower for k in SEROTONIN_KEYWORDS) or is_long

    if has_tension_kw or (is_staccato and not has_oxytocin):
        neuro_type = "ADRENALINE"
        neuro_reason = "🔴 Adrenaline: Kinetic survival, staccato urgency, physical consequence"
    elif has_oxytocin and not has_tension_kw:
        neuro_type = "OXYTOCIN"
        neuro_reason = "🟣 Oxytocin: Interpersonal intimacy, dialogue friction, somatic vulnerability"
    elif has_dopamine:
        neuro_type = "DOPAMINE"
        neuro_reason = "🔵 Dopamine: Epistemic question, secret planted, puzzle/clue revelation"
    elif has_serotonin:
        neuro_type = "SEROTONIN"
        neuro_reason = "🟢 Serotonin: Atmospheric sensory grounding, aesthetic immersion, mythic weight"
    else:
        neuro_type = "NEUTRAL"
        neuro_reason = "Balanced Flow: Narrative transitional beat"

    # 3. LENS: CADENCE RHYTHM (Sentence Length)
    if is_staccato:
        cadence_type = "STACCATO"
        cadence_reason = f"Staccato Burst ({words}w): High velocity / rapid impact"
    elif is_long:
        cadence_type = "EXPANSIVE"
        cadence_reason = f"Expansive Flow ({words}w): Atmospheric breath and contemplative room"
    else:
        cadence_type = "BASELINE"
        cadence_reason = f"Grounded Baseline ({words}w): Steady narrative tempo"

    # 4. LENS: CLUTTER & FILTERS (Cleanse)
    clutter_html, f_hits, c_hits = highlight_clutter_words(s)
    has_clutter = len(f_hits) > 0 or len(c_hits) > 0
    clutter_reason = f"Flagged: {', '.join(f_hits + c_hits)}" if has_clutter else "Clean sentence: Zero filter verbs or crutch words"

    return {
        "text": s,
        "words": words,
        "type": energetics_type,          # Backwards-compatible
        "reason": energetics_reason,      # Backwards-compatible
        "energetics_type": energetics_type,
        "energetics_reason": energetics_reason,
        "neuro_type": neuro_type,
        "neuro_reason": neuro_reason,
        "cadence_type": cadence_type,
        "cadence_reason": cadence_reason,
        "has_clutter": has_clutter,
        "clutter_html": clutter_html,
        "clutter_reason": clutter_reason
    }

def classify_sentence_energetics(text: str) -> list[dict]:
    """Single-pass flat list parser (backwards compatible for test suite)."""
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
    return [classify_multi_lens_sentence(s) for s in sentences]

def classify_paragraph_energetics(text: str) -> list[list[dict]]:
    """Native paragraph-by-paragraph multi-lens parser."""
    if not text or not text.strip():
        return []
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    structured_blocks = []
    for para in raw_paragraphs:
        raw_chunks = re.split(r'([.!?]+(?:\s+|\Z))', para)
        sentences = []
        for i in range(0, len(raw_chunks)-1, 2):
            s = raw_chunks[i] + raw_chunks[i+1]
            if s.strip():
                sentences.append(s.strip())
        if len(raw_chunks) % 2 == 1 and raw_chunks[-1].strip():
            sentences.append(raw_chunks[-1].strip())
        classified = [classify_multi_lens_sentence(s) for s in sentences]
        if classified:
            structured_blocks.append(classified)
    return structured_blocks