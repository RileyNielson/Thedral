import re
import math
from collections import Counter
from backend.config import FILTER_VERBS, CRUTCH_WORDS, TENSION_KEYWORDS
from backend.text_utils import html_to_text
from backend.spectrometer import SIGNAL_LEXICONS, analyze_text_signals

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

COMMON_PROSE_STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "have", "were", "been", "there", "their", "they",
    "what", "when", "where", "which", "would", "could", "should", "about", "into", "then", "them",
    "more", "some", "like", "just", "over", "only", "other", "after", "before", "while", "said",
    "asked", "replied", "look", "looked", "looking", "back", "down", "went", "come", "came", "make",
    "made", "away", "well", "even", "much", "must", "might", "also", "very", "your", "know", "knew"
}

STRAINED_DIALOGUE_TAGS = {
    "hissed", "gasped", "groaned", "sneered", "snarled", "barked", "growled", "sighed", "wheezed",
    "whined", "croaked", "bellowed", "sputtered", "roared", "stammered", "quavered", "snapped"
}

PASSIVE_VOICE_PATTERN = re.compile(
    r"\b(?:was|were|is|are|been|being|had\s+been)\s+([a-z]+ed|[a-z]+en)\s+(?:by\s+([a-z]+)|to|in|at)\b",
    re.IGNORECASE
)

DIALOGUE_ADVERB_PATTERN = re.compile(
    r'["”]\s*,?\s*(?:I|[A-Z][a-z]+)\s+(?:said|asked|replied|says|whispered)\s+([a-z]{3,15}ly)\b',
    re.IGNORECASE
)


def scrub_idioms(text: str) -> str:
    scrubbed = text
    for pattern in COMPOUND_IDIOM_PATTERNS:
        scrubbed = re.sub(pattern, " ", scrubbed, flags=re.IGNORECASE)
    return scrubbed


def detect_word_echoes(paragraphs: list[str], window_size: int = 3) -> dict[str, list[dict]]:
    """Detects unusual words repeated within close proximity (2-3 paragraphs)."""
    echoes = {}
    total_paras = len(paragraphs)
    
    for i in range(total_paras):
        window_end = min(total_paras, i + window_size)
        window_text = " ".join(paragraphs[i:window_end]).lower()
        words = [w for w in re.findall(r"[a-z]{4,}", window_text) if w not in COMMON_PROSE_STOPWORDS]
        counts = Counter(words)
        
        for word, count in counts.items():
            if count >= 3:
                if word not in echoes:
                    echoes[word] = {"count": count, "first_para": i + 1, "paragraphs": [i + 1]}
                elif (i + 1) not in echoes[word]["paragraphs"]:
                    echoes[word]["paragraphs"].append(i + 1)
                    echoes[word]["count"] = max(echoes[word]["count"], count)
                    
    return dict(sorted(echoes.items(), key=lambda x: -x[1]["count"])[:8])


def calculate_text_telemetry(text: str, prev_tension: float | None = None) -> dict:
    text = html_to_text(text)
    if not text or not text.strip():
        return {
            "words": 0, "avg_sentence": 0.0, "cadence_stdev": 0.0,
            "dialogue_ratio": 0.0, "tension_elevation": 0.35,
            "pacing_velocity": 0.0, "pacing_momentum": 0.0,
            "pacing_slope": 0.0, "slope_diagnosis": "NO_PREVIOUS_SCENE",
            "filters": {}, "crutches": {}, "echoes": {},
            "dialogue_adverbs": [], "strained_tags_count": 0,
            "passive_count": 0,
            "text_signals": analyze_text_signals("")
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

    # Word Echoes
    echoes = detect_word_echoes(paragraphs)

    # Passive voice count
    passive_matches = PASSIVE_VOICE_PATTERN.findall(text)
    passive_count = len(passive_matches)

    # Dialogue tags and adverbs
    adverb_matches = DIALOGUE_ADVERB_PATTERN.findall(text)
    strained_tags = sum(len(re.findall(r"\b" + tag + r"\b", text_lower)) for tag in STRAINED_DIALOGUE_TAGS)

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
    slope_diagnosis = "NO_PREVIOUS_SCENE"
    pacing_momentum = stdev

    if prev_tension is not None:
        delta_z = round(tension_elevation - prev_tension, 2)
        pacing_slope = delta_z
        pacing_momentum = round(stdev * (1.0 + delta_z), 1)

        if abs(delta_z) < 0.03 and words > 700:
            slope_diagnosis = "NEARLY_UNCHANGED_ESTIMATE"
        elif delta_z > 0.45:
            slope_diagnosis = "LARGE_ESTIMATE_INCREASE"
        elif delta_z > 0.12:
            slope_diagnosis = "ESTIMATE_INCREASE"
        elif delta_z < -0.15:
            slope_diagnosis = "ESTIMATE_DECREASE"

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
        "echoes": echoes,
        "dialogue_adverbs": list(set(adverb_matches))[:5],
        "strained_tags_count": strained_tags,
        "passive_count": passive_count,
        "text_signals": analyze_text_signals(text)
    }


def highlight_clutter_words(sentence_text: str) -> tuple[str, list, list]:
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


def highlight_tags_and_passive(sentence_text: str) -> tuple[str, list, bool]:
    tags_hit = []
    html = sentence_text

    # Highlight strained tags (hissed, groaned, etc.)
    for tag in STRAINED_DIALOGUE_TAGS:
        pat = re.compile(r"\b(" + re.escape(tag) + r")\b", re.IGNORECASE)
        if pat.search(sentence_text):
            tags_hit.append(tag)
            html = pat.sub(r'<span class="xray-strained-tag">\1</span>', html)

    # Highlight dialogue adverbs (e.g. said daintily)
    adv_match = DIALOGUE_ADVERB_PATTERN.search(sentence_text)
    if adv_match:
        adv = adv_match.group(1)
        tags_hit.append(adv)
        html = re.sub(r'\b(' + re.escape(adv) + r')\b', r'<span class="xray-dialogue-adverb">\1</span>', html)

    # Highlight passive voice
    is_passive = bool(PASSIVE_VOICE_PATTERN.search(sentence_text))
    if is_passive:
        html = PASSIVE_VOICE_PATTERN.sub(r'<span class="xray-passive">\g<0></span>', html)

    return html, tags_hit, is_passive


def classify_multi_lens_sentence(s: str, thresholds: dict | None = None) -> dict:
    options = {
        "staccato_threshold": 9,
        "expansive_threshold": 22,
        "clutter_sensitivity": 2,
    }
    if thresholds:
        options.update({k: v for k, v in thresholds.items() if v is not None})

    words = len(s.split())
    s_lower = s.lower()
    scrubbed_s = scrub_idioms(s).lower()
    staccato_limit = max(4, int(options["staccato_threshold"]))
    expansive_limit = max(staccato_limit + 5, int(options["expansive_threshold"]))
    clutter_cutoff = max(1, int(options["clutter_sensitivity"]))

    # 1. Energetics
    has_tension_kw = any(k in scrubbed_s for k in TENSION_KEYWORDS)
    has_somatic = any(v in s_lower for v in [
        "locked", "struck", "skid", "dragged", "snapped", 
        "blood", "frost", "cold", "grip", "teeth", "muscle", "bone"
    ])
    is_staccato = 0 < words <= staccato_limit
    is_long = words >= expansive_limit
    has_resolver_kw = any(k in s_lower for k in [
        "waited", "quiet", "exhaled", "breathed", "paused", 
        "realized", "sat", "rested", "fade", "stillness"
    ])
    is_pivot = bool(re.match(r'^(?:but|yet|the runner rug|suddenly|and then|instead|except|then)\b', s_lower)) or "gave out" in s_lower or "gave way" in s_lower

    filters_in_s = [v for v in FILTER_VERBS if re.search(r'\b' + v + r'\b', s_lower)]
    crutches_in_s = [w for w in CRUTCH_WORDS if re.search(r'\b' + w + r'\b', s_lower)]

    if is_pivot:
        energetics_type = "PIVOT"
        energetics_reason = "Transition hinge: shifts narrative trajectory or mood."
    elif (has_tension_kw or has_somatic) and (is_staccato or has_tension_kw):
        energetics_type = "ESCALATOR"
        energetics_reason = f"Kinetic escalator: action cues and punchy syntax ({words} words)."
    elif (has_resolver_kw or is_long) and not has_tension_kw:
        energetics_type = "RESOLVER"
        energetics_reason = f"Lyrical resolver: contemplative pause allowing the reader to breathe ({words} words)."
    elif len(filters_in_s) >= clutter_cutoff or len(crutches_in_s) >= clutter_cutoff:
        energetics_type = "SLACK"
        energetics_reason = f"Semantic clutter: filter verbs ({', '.join(filters_in_s)}) or crutches ({', '.join(crutches_in_s)})."
    else:
        energetics_type = "NEUTRAL"
        energetics_reason = f"Clean narrative baseline ({words} words)."

    # 2. Cadence
    if is_staccato:
        cadence_type = "STACCATO"
        cadence_reason = f"Staccato rhythm ({words} words)."
    elif is_long:
        cadence_type = "EXPANSIVE"
        cadence_reason = f"Expansive cadence ({words} words)."
    else:
        cadence_type = "BASELINE"
        cadence_reason = f"Standard rhythmic cadence ({words} words)."

    # 3. Clutter
    clutter_html, f_hits, c_hits = highlight_clutter_words(s)
    has_clutter = len(f_hits) > 0 or len(c_hits) > 0
    clutter_reason = f"Matched: {', '.join(f_hits + c_hits)}" if has_clutter else "No filter verbs or crutch clutter."

    # 4. Tags & Passive
    tags_html, tags_hit, is_passive = highlight_tags_and_passive(s)
    tags_reason = f"Dialogue cue: {', '.join(tags_hit)}" if tags_hit else ("Passive voice construction" if is_passive else "Clean active voice.")

    return {
        "text": s,
        "words": words,
        "type": energetics_type,
        "reason": energetics_reason,
        "energetics_type": energetics_type,
        "energetics_reason": energetics_reason,
        "cadence_type": cadence_type,
        "cadence_reason": cadence_reason,
        "has_clutter": has_clutter,
        "clutter_html": clutter_html,
        "clutter_reason": clutter_reason,
        "has_tags_or_passive": len(tags_hit) > 0 or is_passive,
        "tags_html": tags_html,
        "tags_reason": tags_reason
    }


def classify_sentence_energetics(text: str, thresholds: dict | None = None) -> list[dict]:
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
    return [classify_multi_lens_sentence(s, thresholds) for s in sentences]


def classify_paragraph_energetics(text: str, thresholds: dict | None = None) -> list[list[dict]]:
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
        classified = [classify_multi_lens_sentence(s, thresholds) for s in sentences]
        if classified:
            structured_blocks.append(classified)
    return structured_blocks
