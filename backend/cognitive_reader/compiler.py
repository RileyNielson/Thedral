import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

try:
    from .wiktionary_ingestor import WiktionaryFullIngestor, compute_phonetic_texture
except (ImportError, ValueError):
    from cognitive_reader.wiktionary_ingestor import WiktionaryFullIngestor, compute_phonetic_texture

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "cognitive_lexicon.db"
TOKEN_RE = re.compile(r"[a-z]{2,}")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS lexicon_senses (
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    sense_id INTEGER NOT NULL,
    ontological_domain TEXT NOT NULL,
    context_cues TEXT DEFAULT '',
    register_tier TEXT DEFAULT 'NEUTRAL',
    valence REAL DEFAULT 0.0,
    arousal REAL DEFAULT 0.0,
    dominance REAL DEFAULT 0.0,
    concreteness REAL DEFAULT 0.5,
    mass_weight REAL DEFAULT 0.0,
    temperature REAL DEFAULT 0.0,
    sharpness REAL DEFAULT 0.0,
    velocity REAL DEFAULT 0.0,
    corrosion_decay REAL DEFAULT 0.0,
    luminance REAL DEFAULT 0.0,
    sensory_visual REAL DEFAULT 0.0,
    sensory_auditory REAL DEFAULT 0.0,
    sensory_haptic REAL DEFAULT 0.0,
    sensory_olfactory REAL DEFAULT 0.0,
    sensory_gustatory REAL DEFAULT 0.0,
    sensory_interoceptive REAL DEFAULT 0.0,
    plosive_impact REAL DEFAULT 0.0,
    sonorant_flow REAL DEFAULT 0.0,
    PRIMARY KEY (lemma, pos, sense_id)
);

CREATE TABLE IF NOT EXISTS inflected_forms (
    surface_form TEXT PRIMARY KEY,
    canonical_lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    morph_tags TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS mwe_lexicon (
    phrase TEXT PRIMARY KEY,
    mwe_type TEXT NOT NULL,
    canonical_lemma TEXT NOT NULL,
    ontological_domain TEXT NOT NULL,
    non_literal_override BOOLEAN DEFAULT 1,
    valence REAL DEFAULT 0.0,
    arousal REAL DEFAULT 0.0,
    dominance REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS verb_frames (
    verb_lemma TEXT PRIMARY KEY,
    required_subj_domains TEXT NOT NULL,
    required_obj_domains TEXT NOT NULL,
    state_mutation TEXT NOT NULL,
    precondition TEXT DEFAULT 'NONE',
    imposed_physics_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS somatic_markers (
    phrase_pattern TEXT PRIMARY KEY,
    body_channel TEXT NOT NULL,
    control_type TEXT NOT NULL,
    surface_valence REAL NOT NULL,
    internal_stress REAL NOT NULL,
    subtext_diagnosis TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pragmatic_constructions (
    construction_id TEXT PRIMARY KEY,
    regex_pattern TEXT NOT NULL,
    required_surface_polarity INTEGER NOT NULL,
    irony_multiplier REAL NOT NULL,
    pragmatic_label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concept_edges (
    source_lemma TEXT NOT NULL,
    relation TEXT NOT NULL,
    target_lemma TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    PRIMARY KEY (source_lemma, relation, target_lemma)
);

CREATE INDEX IF NOT EXISTS idx_senses_lemma ON lexicon_senses(lemma);
CREATE INDEX IF NOT EXISTS idx_forms_surface ON inflected_forms(surface_form);
CREATE INDEX IF NOT EXISTS idx_edges_source ON concept_edges(source_lemma);
"""

# Universal Natural Semantic Metalanguage (NSM) Calibration Anchors
# Pure dimensional poles used to ground physical scales mathematically
PRIMITIVE_POLES: Dict[str, Dict[str, float]] = {
    # Mass & Inertia
    "heavy": {"mass_weight": 0.95, "velocity": -0.40},
    "massive": {"mass_weight": 1.00, "dominance": 0.60},
    "dense": {"mass_weight": 0.85},
    "weightless": {"mass_weight": -0.95, "velocity": 0.30},
    "hollow": {"mass_weight": -0.80, "valence": -0.40},
    # Thermal Physics
    "hot": {"temperature": 0.90, "arousal": 0.50},
    "fire": {"temperature": 1.00, "luminance": 0.90, "arousal": 0.85},
    "flame": {"temperature": 0.90, "luminance": 0.85},
    "burn": {"temperature": 0.95, "corrosion_decay": 0.70, "valence": -0.60},
    "cold": {"temperature": -0.90, "velocity": -0.40},
    "ice": {"temperature": -1.00, "velocity": -0.85, "concreteness": 0.95},
    "freezing": {"temperature": -1.00, "velocity": -0.90},
    # Tactile Sharpness
    "sharp": {"sharpness": 1.00, "arousal": 0.50},
    "blade": {"sharpness": 1.00, "concreteness": 0.95},
    "razor": {"sharpness": 1.00, "concreteness": 0.95},
    "soft": {"sharpness": -0.90, "valence": 0.40},
    "blunt": {"sharpness": -0.85},
    # Velocity & Motion
    "fast": {"velocity": 0.90, "arousal": 0.60},
    "rapid": {"velocity": 0.90, "arousal": 0.60},
    "sudden": {"velocity": 0.95, "arousal": 0.75},
    "slow": {"velocity": -0.85, "arousal": -0.30},
    "stagnant": {"velocity": -0.95, "corrosion_decay": 0.60},
    "still": {"velocity": -0.90},
    # Luminance & Optical Physics
    "bright": {"luminance": 0.90, "valence": 0.40},
    "light": {"luminance": 0.85},
    "radiant": {"luminance": 0.95, "valence": 0.50},
    "dark": {"luminance": -0.90, "valence": -0.35},
    "shadow": {"luminance": -0.80},
    "black": {"luminance": -0.95},
    # Corrosion & Material Decay
    "rot": {"corrosion_decay": 1.00, "valence": -0.80},
    "decay": {"corrosion_decay": 0.95, "valence": -0.70},
    "rust": {"corrosion_decay": 0.90, "velocity": -0.50},
    "pure": {"corrosion_decay": -0.90, "valence": 0.60},
    # Affective Extremes (VAD Calibration)
    "joy": {"valence": 0.95, "arousal": 0.65, "dominance": 0.55},
    "peace": {"valence": 0.85, "arousal": -0.75, "dominance": 0.50},
    "pain": {"valence": -0.95, "arousal": 0.85, "dominance": -0.75},
    "terror": {"valence": -0.95, "arousal": 0.95, "dominance": -0.90},
    "rage": {"valence": -0.90, "arousal": 0.95, "dominance": 0.70},
}

# Standard Genus Proximum Definition Patterns
# Matches standard lexicographical definition frames across any English dictionary
GENUS_DOMAIN_RULES: List[Tuple[str, float, Tuple[str, ...]]] = [
    ("ABSTRACT_STATE", 0.15, (
        "feeling of", "emotion of", "state of", "quality of", "condition of",
        "attitude of", "mental state", "belief that", "desire to", "sensation of",
    )),
    ("SOCIAL_CONSTRUCT", 0.30, (
        "system of", "organization of", "body of", "form of government", "law of",
        "custom of", "obligation to", "title of", "rank of", "status of", "office of",
    )),
    ("SOUND", 0.30, (
        "sound of", "noise of", "voice of", "cry of", "sound produced by", "acoustic",
        "musical instrument", "auditory", "vocalization",
    )),
    ("LIGHT", 0.90, (
        "source of light", "device that produces light", "radiation of", "optical",
        "illumination", "emitting light",
    )),
    ("THERMAL", 0.85, (
        "combustion of", "heat produced", "burning of", "low temperature", "high temperature",
    )),
    ("SUBSTANCE_LIQUID", 0.90, (
        "liquid that", "fluid that", "solution of", "beverage made", "water that",
    )),
    ("SPACE_CONTAINER", 0.92, (
        "enclosed space", "room in", "building used", "structure built", "chamber in",
        "place where", "area used for", "fortification", "settlement", "compartment",
    )),
    ("ANIMATE_BEING", 0.95, (
        "person who", "human being", "animal of", "mammal of", "bird of", "creature that",
        "individual who", "organ of", "body part of",
    )),
    ("ARTIFACT_SOLID", 0.94, (
        "tool used", "weapon used", "instrument used", "device designed", "object made",
        "vessel used", "piece of", "mineral consisting", "alloy of", "metal used",
    )),
]

# Universal Semantic Verb Classes (FrameNet / VerbNet aligned)
VERB_CLASS_RULES: List[Tuple[str, List[str], List[str], str, Dict[str, float], Tuple[str, ...]]] = [
    (
        "SHATTER_DESTROY",
        ["ANIMATE_BEING", "ARTIFACT_SOLID"],
        ["ARTIFACT_SOLID"],
        "NONE",
        {"sharpness": 0.90, "velocity": 0.85, "arousal": 0.80, "valence": -0.75, "corrosion_decay": 0.80},
        ("break into pieces", "cause to fracture", "smash violently", "destroy by breaking", "cause to shatter"),
    ),
    (
        "INGEST",
        ["ANIMATE_BEING"],
        ["SUBSTANCE_LIQUID", "ARTIFACT_SOLID"],
        "NONE",
        {"corrosion_decay": 0.75, "velocity": -0.50, "dominance": -0.70, "valence": -0.40},
        ("take into the stomach", "swallow food", "drink liquid", "consume food", "absorb liquid"),
    ),
    (
        "CONSTRICT_SUFFOCATE",
        ["ANIMATE_BEING"],
        ["ANIMATE_BEING"],
        "NONE",
        {"arousal": 0.85, "valence": -0.85, "dominance": -0.90, "mass_weight": 0.75, "velocity": -0.60},
        ("cut off the breath", "compress the throat", "prevent breathing", "kill by suffocating"),
    ),
    (
        "LIGHT_ACTIVATION",
        ["ANIMATE_BEING", "THERMAL"],
        ["LIGHT", "THERMAL", "ARTIFACT_SOLID"],
        "NONE",
        {"luminance": 0.90, "temperature": 0.85, "arousal": 0.50},
        ("cause to burn", "set on fire", "produce light", "ignite fuel"),
    ),
    (
        "LIGHT_TERMINATION",
        ["ANIMATE_BEING", "SUBSTANCE_LIQUID"],
        ["LIGHT", "THERMAL"],
        "NONE",
        {"luminance": -0.95, "temperature": -0.50, "valence": -0.30},
        ("put out a fire", "cause to cease burning", "smother a flame", "extinguish light"),
    ),
    (
        "VISUAL_PERCEPTION",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "ANIMATE_BEING", "SPACE_CONTAINER"],
        "REQUIRES_LIGHT",
        {"arousal": 0.15},
        ("look at visually", "perceive with the eyes", "inspect visually", "examine visually"),
    ),
    (
        "ACQUIRE_OBJECT",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "LIGHT"],
        "NONE",
        {"dominance": 0.35},
        ("take hold of with the hand", "seize with the hands", "grasp firmly", "unsheathe a weapon"),
    ),
    (
        "RELEASE_OBJECT",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "LIGHT"],
        "REQUIRES_HOLDING",
        {"velocity": 0.50},
        ("let go of from the hand", "allow to fall", "release hold of"),
    ),
]

# Minimal Starter Calibration Set for unit testing when offline
CORE_CALIBRATION_GLOSSES: List[Tuple[str, str, str]] = [
    ("anvil", "noun", "A massive block of iron used as an instrument for hammering metal."),
    ("blade", "noun", "The sharp cutting edge of an instrument, weapon, or knife."),
    ("sword", "noun", "A weapon with a long metal blade used for cutting and thrusting."),
    ("fire", "noun", "The thermal combustion of a substance producing heat and light."),
    ("ice", "noun", "Frozen water in a solid state at a very low temperature."),
    ("lantern", "noun", "A portable transparent device that produces light."),
    ("melancholy", "noun", "A state of deep sadness, gloom, and sorrow."),
    ("grief", "noun", "A feeling of deep emotional sorrow and suffering."),
    ("strangle", "verb", "To compress the throat so as to prevent breathing."),
    ("digest", "verb", "To dissolve and take into the stomach food or beverage."),
    ("shatter", "verb", "To break into pieces violently."),
    ("extinguish", "verb", "To put out a fire or light source."),
    ("ignite", "verb", "To set on fire or cause to burn."),
    ("read", "verb", "To look at visually and interpret written letters."),
    ("drop", "verb", "To allow to fall from the hand."),
    ("take", "verb", "To take hold of with the hand."),
]


def _generate_combinatorial_somatic_markers() -> List[Tuple[str, str, str, float, float, str]]:
    markers = []
    mask_verbs = ["smiled", "laughed", "nodded", "chuckled", "answered", "replied", "spoke", "said"]
    mask_adverbs = [
        ("politely", 0.55, 0.65, "Polite social masking suppressing true affect"),
        ("thinly", 0.20, 0.78, "Thin-lipped restraint masking hostility or discomfort"),
        ("lightly", 0.60, 0.55, "Deflective levity minimizing emotional gravity"),
        ("brightly", 0.70, 0.60, "Forced affective brightness concealing inner tension"),
        ("stiffly", 0.10, 0.75, "Rigid muscular containment during social exchange"),
        ("sweetly", 0.65, 0.70, "Performative sweetness masking interpersonal friction"),
        ("smoothly", 0.45, 0.60, "Calculated vocal/facial control"),
    ]
    for v in mask_verbs:
        for adv, val, stress, desc in mask_adverbs:
            markers.append((f"{v} {adv}", "FACE_VOICE", "PERFORMATIVE_MASK", val, stress, desc))

    noun_masks = [
        "polite smile", "thin smile", "tight smile", "practiced smile",
        "put on a smile", "smile plastered", "smiled with his lips together",
        "with an even tone", "even voice", "forced laugh",
    ]
    for nm in noun_masks:
        markers.append((nm, "FACE_VOICE", "PERFORMATIVE_MASK", 0.35, 0.75, f"Performative social mask ('{nm}')"))

    for p in ["jaw tightened", "jaw clenched", "clenched his jaw", "clenched her jaw", "teeth ground"]:
        markers.append((p, "JAW_THROAT", "AUTONOMIC_LEAK", -0.70, 0.86, "Involuntary masseter tension"))

    for p in ["white knuckles", "knuckles whitened", "hands trembled", "hands shook", "fist clenched", "fists clenched", "balled his fists"]:
        markers.append((p, "HANDS_GRIP", "AUTONOMIC_LEAK", -0.75, 0.90, "Autonomic peripheral tension spike"))

    for p in ["swallowed hard", "throat bobbed", "breath caught", "breath hitched", "stomach dropped", "stomach sank", "heart raced", "clenched his gut"]:
        markers.append((p, "AUTONOMIC_VISCERA", "AUTONOMIC_LEAK", -0.65, 0.85, "Visceral autonomic betrayal"))

    return markers


PRAGMATIC_CONSTRUCTIONS = [
    (
        "hyperbolic_affirmation",
        r"\b(oh|well|yeah|ah)[,\s]+.*?\b(just|totally|absolutely|simply|sure\s+he'd\s+be|sure\s+she'd\s+be)\s+(love|adore|thrilled|delighted|wonderful|fantastic|perfect|happy)\b",
        1,
        0.75,
        "HYPERBOLIC_SARCASM",
    ),
    (
        "mock_enthusiasm_nothing_like",
        r"\b(nothing\s+says|nothing\s+like|what\s+a\s+joy|how\s+delightful|always\s+a\s+pleasure|my\s+pleasure\s+to\s+serve)\b",
        1,
        0.85,
        "IRONIC_ENTHUSIASM",
    ),
    (
        "temporal_exaggeration_snark",
        r"\b(hopefully|maybe)\b.*?\b(only\s+take\s+half\s+a\s+day|rather\s+than\s+a\s+full\s+one|take\s+all\s+year|before\s+winter)\b",
        0,
        0.85,
        "TEMPORAL_HYPERBOLE_SARCASM",
    ),
    (
        "clipped_dismissal",
        r"^(fine|whatever|lovely|charming|great|wonderful|brilliant)[\.\!]$",
        1,
        0.65,
        "CLIPPED_IRONY",
    ),
    (
        "over_polite_shield",
        r"\b(how\s+very\s+kind|so\s+generous\s+of\s+you|i'm\s+sure\s+you\s+tried|bless\s+your\s+heart)\b",
        1,
        0.80,
        "WEAPONIZED_POLITENESS",
    ),
]


def score_gloss_from_primitives(
    lemma: str,
    pos: str,
    gloss: str,
    known_vectors: Optional[Dict[str, Dict[str, float]]] = None,
) -> Tuple[str, Dict[str, float], List[str], str]:
    """Scores any English definition against universal physical calibration primitives."""
    g_low = gloss.lower()
    tokens = TOKEN_RE.findall(g_low)

    domain = "ABSTRACT_STATE" if pos in ("adj", "adv") else "ARTIFACT_SOLID"
    concreteness = 0.50
    for cand_domain, cand_conc, definition_frames in GENUS_DOMAIN_RULES:
        if any(frame in g_low for frame in definition_frames):
            domain = cand_domain
            concreteness = cand_conc
            break

    dims = [
        "valence", "arousal", "dominance", "mass_weight", "temperature",
        "sharpness", "velocity", "corrosion_decay", "luminance",
    ]
    accum = {d: 0.0 for d in dims}
    weights = {d: 0.0 for d in dims}
    linked_targets: List[str] = []

    if lemma in PRIMITIVE_POLES:
        for d, val in PRIMITIVE_POLES[lemma].items():
            if d == "concreteness":
                concreteness = val
            elif d in accum:
                accum[d] += val * 1.5
                weights[d] += 1.5

    for idx, tok in enumerate(tokens[:35]):
        positional_weight = 1.0 if idx < 10 else 0.55
        for prim_key, prim_vec in PRIMITIVE_POLES.items():
            if tok == prim_key or (len(prim_key) >= 4 and tok.startswith(prim_key)):
                linked_targets.append(prim_key)
                for d, val in prim_vec.items():
                    if d == "concreteness":
                        concreteness = (concreteness + val) / 2.0
                    elif d in accum:
                        accum[d] += val * positional_weight
                        weights[d] += positional_weight

        if known_vectors and tok in known_vectors and tok != lemma:
            parent_vec = known_vectors[tok]
            for d in dims:
                val = parent_vec.get(d, 0.0)
                if abs(val) >= 0.35:
                    accum[d] += val * (positional_weight * 0.65)
                    weights[d] += positional_weight * 0.65

    final_phys = {"concreteness": round(concreteness, 3)}
    for d in dims:
        if weights[d] > 0:
            raw_avg = accum[d] / max(1.0, weights[d] * 0.75)
            final_phys[d] = round(max(-1.0, min(1.0, raw_avg)), 3)
        else:
            final_phys[d] = 0.0

    stopwords = {"the", "and", "for", "with", "that", "from", "into", "used", "made", "having", "state"}
    cues = " ".join([t for t in tokens if len(t) >= 3 and t not in stopwords][:15])
    return domain, final_phys, linked_targets, cues


def _infer_mwe_canonical(phrase: str, gloss: str) -> Tuple[str, str, float, float, float]:
    g = gloss.lower()
    mwe_type = "IDIOM" if "idiomatic" in g or len(phrase.split()) >= 3 else "PHRASAL_VERB"
    if "extinguish" in g or "put out" in g:
        return mwe_type, "extinguish", -0.30, 0.20, 0.20
    if "die" in g or "pass away" in g:
        return mwe_type, "die", -0.90, 0.75, -0.90
    if "surrender" in g or "cease effort" in g:
        return mwe_type, "surrender", -0.75, -0.40, -0.85
    if "reveal" in g and "secret" in g:
        return mwe_type, "reveal_secret", -0.20, 0.65, 0.10
    return mwe_type, phrase.replace(" ", "_"), -0.20, 0.30, 0.0


def infer_sensory_profile(domain: str, gloss: str, phys: Dict[str, float]) -> Dict[str, float]:
    """Maps ontological domain and physical dimensions to Lancaster sensorimotor modalities."""
    g = gloss.lower()
    vis = 0.75 if domain in ("ARTIFACT_SOLID", "LIGHT", "SPACE_CONTAINER", "ANIMATE_BEING") else 0.25
    aud = 0.90 if domain == "SOUND" or any(k in g for k in ("sound", "cry", "noise", "voice", "loud", "quiet", "auditory")) else 0.10
    hap = 0.85 if abs(phys.get("sharpness", 0)) >= 0.5 or abs(phys.get("temperature", 0)) >= 0.5 or abs(phys.get("mass_weight", 0)) >= 0.5 else 0.15
    olf = 0.85 if any(k in g for k in ("smell", "odor", "scent", "stench", "aroma", "fragrant", "reek")) else 0.05
    gus = 0.85 if any(k in g for k in ("taste", "sweet", "sour", "bitter", "salty", "flavor", "beverage", "food", "drink", "edible")) else 0.05
    intero = 0.85 if domain == "ABSTRACT_STATE" or abs(phys.get("valence", 0)) >= 0.65 else 0.10
    return {
        "sensory_visual": round(vis, 3),
        "sensory_auditory": round(aud, 3),
        "sensory_haptic": round(hap, 3),
        "sensory_olfactory": round(olf, 3),
        "sensory_gustatory": round(gus, 3),
        "sensory_interoceptive": round(intero, 3),
    }


def build_cognitive_database(
    output_db_path: Path = DEFAULT_DB_PATH,
    wiktionary_sqlite_path: Optional[str] = None,
) -> Dict[str, int | str]:
    output_db_path = Path(output_db_path)
    output_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(output_db_path))
    cur = conn.cursor()
    cur.executescript(SCHEMA_SQL)

    gloss_rows: List[Tuple[str, str, str]] = list(CORE_CALIBRATION_GLOSSES)
    if wiktionary_sqlite_path and os.path.exists(wiktionary_sqlite_path):
        ingestor = WiktionaryFullIngestor(wiktionary_sqlite_path)
        for rec in ingestor.iter_rich_entries():
            gloss_rows.append((str(rec["lemma"]), str(rec["pos"]), str(rec["gloss"])))

    known_vectors: Dict[str, Dict[str, float]] = {}
    sense_counters: Dict[Tuple[str, str], int] = {}
    verb_frame_rows = []
    concept_edge_rows = []
    mwe_rows = []

    for lemma, pos, gloss in gloss_rows:
        w = lemma.strip().lower()
        p = (pos or "noun").strip().lower()
        if " " in w:
            mwe_type, canon, val, aro, dom = _infer_mwe_canonical(w, gloss)
            mwe_rows.append((w, mwe_type, canon, "ABSTRACT_STATE", 1, val, aro, dom))
            continue

        domain, phys, edges, _ = score_gloss_from_primitives(w, p, gloss, known_vectors=None)
        if w not in known_vectors:
            known_vectors[w] = {"domain": domain, "pos": p, **phys}

        for target_prim in set(edges):
            if target_prim != w:
                concept_edge_rows.append((w, "GroundedInPrimitive", target_prim, 0.85))

        if p.startswith("v"):
            g_low = gloss.lower()
            for mutation, req_s, req_o, precond, imp_phys, definition_frames in VERB_CLASS_RULES:
                if any(frame in g_low for frame in definition_frames) or w in definition_frames:
                    verb_frame_rows.append((
                        w, json.dumps(req_s), json.dumps(req_o), mutation, precond, json.dumps(imp_phys)
                    ))
                    break

    sense_rows = []
    for lemma, pos, gloss in gloss_rows:
        w = lemma.strip().lower()
        if " " in w or not w:
            continue
        p = (pos or "noun").strip().lower()
        key = (w, p)
        sense_id = sense_counters.get(key, 0) + 1
        sense_counters[key] = sense_id

        domain, phys, _, cues = score_gloss_from_primitives(w, p, gloss, known_vectors=known_vectors)
        sensory = infer_sensory_profile(domain, gloss, phys)
        phonetics = compute_phonetic_texture(w)

        sense_rows.append((
            w, p, sense_id, domain, cues, "NEUTRAL",
            phys["valence"], phys["arousal"], phys["dominance"],
            phys["concreteness"], phys["mass_weight"], phys["temperature"],
            phys["sharpness"], phys["velocity"], phys["corrosion_decay"], phys["luminance"],
            sensory["sensory_visual"], sensory["sensory_auditory"], sensory["sensory_haptic"],
            sensory["sensory_olfactory"], sensory["sensory_gustatory"], sensory["sensory_interoceptive"],
            phonetics["plosive_impact"], phonetics["sonorant_flow"],
        ))

    cur.executemany(
        """
        INSERT OR REPLACE INTO lexicon_senses VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """,
        sense_rows,
    )
    cur.executemany("INSERT OR REPLACE INTO mwe_lexicon VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mwe_rows)
    cur.executemany("INSERT OR REPLACE INTO verb_frames VALUES (?, ?, ?, ?, ?, ?)", verb_frame_rows)
    cur.executemany("INSERT OR IGNORE INTO concept_edges VALUES (?, ?, ?, ?)", concept_edge_rows)
    cur.executemany("INSERT OR REPLACE INTO somatic_markers VALUES (?, ?, ?, ?, ?, ?)", _generate_combinatorial_somatic_markers())
    cur.executemany("INSERT OR REPLACE INTO pragmatic_constructions VALUES (?, ?, ?, ?, ?)", PRAGMATIC_CONSTRUCTIONS)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM lexicon_senses")
    total_senses = cur.fetchone()[0]
    conn.close()

    return {
        "db_path": str(output_db_path),
        "total_senses": total_senses,
        "total_mwes": len(mwe_rows),
        "auto_classified_verb_frames": len(verb_frame_rows),
    }
