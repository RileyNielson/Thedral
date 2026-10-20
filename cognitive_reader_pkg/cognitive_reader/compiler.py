import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

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

PRIMITIVE_POLES: Dict[str, Dict[str, float]] = {
    "heavy": {"mass_weight": 0.90, "velocity": -0.40},
    "massive": {"mass_weight": 0.95, "dominance": 0.60},
    "dense": {"mass_weight": 0.80},
    "weight": {"mass_weight": 0.70},
    "crushing": {"mass_weight": 0.95, "valence": -0.80, "dominance": -0.80},
    "iron": {"mass_weight": 0.85, "dominance": 0.70, "concreteness": 0.95},
    "steel": {"mass_weight": 0.85, "dominance": 0.85, "concreteness": 0.96},
    "metal": {"mass_weight": 0.80, "dominance": 0.75, "concreteness": 0.95},
    "armor": {"mass_weight": 0.80, "dominance": 0.85, "concreteness": 0.95},
    "stone": {"mass_weight": 0.85, "concreteness": 0.95},
    "mountain": {"mass_weight": 0.98, "dominance": 0.85, "concreteness": 0.96},
    "weightless": {"mass_weight": -0.90, "velocity": 0.30},
    "hollow": {"mass_weight": -0.75, "valence": -0.45},
    "hot": {"temperature": 0.85, "arousal": 0.40},
    "fire": {"temperature": 0.95, "arousal": 0.80, "luminance": 0.85},
    "flame": {"temperature": 0.90, "luminance": 0.80},
    "burn": {"temperature": 0.90, "corrosion_decay": 0.70, "valence": -0.60},
    "warm": {"temperature": 0.60, "valence": 0.70, "arousal": -0.30},
    "cold": {"temperature": -0.85, "velocity": -0.40},
    "ice": {"temperature": -0.95, "velocity": -0.85, "concreteness": 0.92},
    "freeze": {"temperature": -0.95, "velocity": -0.95},
    "sharp": {"sharpness": 0.95, "arousal": 0.50},
    "blade": {"sharpness": 0.95, "valence": -0.50, "concreteness": 0.95},
    "razor": {"sharpness": 0.98, "valence": -0.55},
    "cut": {"sharpness": 0.85, "valence": -0.50},
    "jagged": {"sharpness": 0.92, "valence": -0.55},
    "splinter": {"sharpness": 0.85, "valence": -0.55, "concreteness": 0.92},
    "shatter": {"sharpness": 0.88, "corrosion_decay": 0.80, "velocity": 0.75, "valence": -0.70},
    "glass": {"sharpness": 0.80, "concreteness": 0.94},
    "soft": {"sharpness": -0.85, "valence": 0.45},
    "gentle": {"sharpness": -0.80, "valence": 0.75, "arousal": -0.60},
    "fast": {"velocity": 0.85, "arousal": 0.60},
    "rapid": {"velocity": 0.85, "arousal": 0.55},
    "sudden": {"velocity": 0.90, "arousal": 0.75},
    "strike": {"velocity": 0.85, "arousal": 0.85, "valence": -0.70},
    "explode": {"velocity": 0.98, "arousal": 0.98, "temperature": 0.85, "valence": -0.80},
    "slow": {"velocity": -0.80, "arousal": -0.40},
    "stagnant": {"velocity": -0.92, "corrosion_decay": 0.60, "valence": -0.50},
    "immobile": {"velocity": -0.95, "dominance": -0.60},
    "moor": {"velocity": -0.90, "mass_weight": 0.80},
    "anchor": {"velocity": -0.95, "mass_weight": 0.95, "concreteness": 0.96},
    "rust": {"corrosion_decay": 0.92, "velocity": -0.60, "valence": -0.45},
    "corrode": {"corrosion_decay": 0.95, "valence": -0.60},
    "rot": {"corrosion_decay": 0.95, "valence": -0.80},
    "decay": {"corrosion_decay": 0.90, "valence": -0.70},
    "sour": {"corrosion_decay": 0.70, "valence": -0.65},
    "ash": {"corrosion_decay": 0.88, "mass_weight": -0.70, "valence": -0.50},
    "acid": {"corrosion_decay": 0.95, "sharpness": 0.75, "valence": -0.75},
    "poison": {"corrosion_decay": 0.90, "valence": -0.92, "arousal": 0.65},
    "toxic": {"corrosion_decay": 0.90, "valence": -0.90},
    "pure": {"corrosion_decay": -0.85, "valence": 0.65},
    "bright": {"luminance": 0.85, "valence": 0.40},
    "sunset": {"luminance": 0.75, "temperature": 0.50, "concreteness": 0.85},
    "light": {"luminance": 0.85},
    "dark": {"luminance": -0.88, "valence": -0.35},
    "gloom": {"luminance": -0.80, "valence": -0.60},
    "joy": {"valence": 0.92, "arousal": 0.65, "dominance": 0.55},
    "love": {"valence": 0.92, "arousal": 0.65, "dominance": 0.50},
    "happy": {"valence": 0.88, "arousal": 0.55, "dominance": 0.45},
    "delight": {"valence": 0.88, "arousal": 0.60, "dominance": 0.50},
    "pleasure": {"valence": 0.88, "arousal": 0.50, "dominance": 0.45},
    "wonderful": {"valence": 0.90, "arousal": 0.55, "dominance": 0.55},
    "peace": {"valence": 0.85, "arousal": -0.75, "dominance": 0.45},
    "calm": {"valence": 0.72, "arousal": -0.80, "dominance": 0.45},
    "safe": {"valence": 0.80, "arousal": -0.70, "dominance": 0.55},
    "sadness": {"valence": -0.85, "arousal": -0.30, "dominance": -0.70},
    "sorrow": {"valence": -0.85, "arousal": 0.15, "dominance": -0.75},
    "grief": {"valence": -0.88, "arousal": 0.25, "dominance": -0.78},
    "pain": {"valence": -0.90, "arousal": 0.80, "dominance": -0.75},
    "fear": {"valence": -0.88, "arousal": 0.88, "dominance": -0.82},
    "terror": {"valence": -0.96, "arousal": 0.96, "dominance": -0.92},
    "dread": {"valence": -0.88, "arousal": 0.75, "dominance": -0.78},
    "anger": {"valence": -0.80, "arousal": 0.90, "dominance": 0.55},
    "rage": {"valence": -0.90, "arousal": 0.96, "dominance": 0.65},
    "hate": {"valence": -0.92, "arousal": 0.85, "dominance": 0.30},
    "insult": {"valence": -0.80, "arousal": 0.65, "sharpness": 0.60},
    "sneer": {"valence": -0.75, "arousal": 0.55, "dominance": 0.30},
    "snarl": {"valence": -0.80, "arousal": 0.75, "dominance": 0.40},
    "frown": {"valence": -0.60, "arousal": 0.30},
    "slaughter": {"valence": -0.98, "arousal": 0.98, "dominance": 0.70, "sharpness": 0.90},
    "scream": {"valence": -0.85, "arousal": 0.95, "dominance": -0.55},
    "bleed": {"valence": -0.85, "arousal": 0.85, "dominance": -0.65},
}

GENUS_DOMAIN_RULES: List[Tuple[str, float, Tuple[str, ...]]] = [
    ("ABSTRACT_STATE", 0.14, (
        "feeling", "emotion", "state of", "quality of", "condition of", "mental",
        "belief", "idea", "concept", "attitude", "sadness", "sorrow", "fear", "anger", "joy", "unfriendly", "unemotional",
    )),
    ("SOCIAL_CONSTRUCT", 0.22, (
        "system", "organization", "government", "administration", "law", "custom",
        "institution", "obligation", "debt", "policy", "contract", "authority",
    )),
    ("SOUND", 0.28, (
        "sound", "noise", "voice", "cry", "shout", "whisper", "silence", "music", "tone", "utterance", "loud cry made by a dog",
    )),
    ("LIGHT", 0.92, (
        "lamp", "lantern", "torch", "candle", "light source", "beacon", "chandelier", "bulb", "sunset",
    )),
    ("THERMAL", 0.86, (
        "fire", "flame", "heat", "conflagration", "wildfire", "ember", "blaze", "inferno", "low temperature",
    )),
    ("SUBSTANCE_LIQUID", 0.90, (
        "liquid", "fluid", "water", "beverage", "drink", "solution", "acid", "venom", "poison", "blood", "tea", "wine", "ale", "seawater",
    )),
    ("SPACE_CONTAINER", 0.92, (
        "room", "building", "chamber", "hall", "house", "tavern", "cellar", "prison", "cage", "enclosure", "corridor", "place where", "bailey", "keep",
    )),
    ("ANIMATE_BEING", 0.92, (
        "person", "human", "man", "woman", "child", "animal", "creature", "bird", "dog", "hound", "organ", "body part", "thief", "guard", "knight", "executioner",
    )),
    ("ARTIFACT_SOLID", 0.94, (
        "tool", "weapon", "instrument", "device", "object", "vessel", "block", "metal", "iron", "steel", "stone", "wood", "tree", "trunk", "exterior covering", "document", "inscription", "letter", "sword", "knife", "dagger", "anchor", "glass", "feather", "armor", "bread", "raisin", "sand",
    )),
]

VERB_FRAME_RULES: List[Tuple[str, List[str], List[str], str, Dict[str, float], Tuple[str, ...]]] = [
    (
        "CONSTRICT_SUFFOCATE",
        ["ANIMATE_BEING"],
        ["ANIMATE_BEING"],
        "NONE",
        {"arousal": 0.85, "valence": -0.85, "dominance": -0.90, "mass_weight": 0.75, "velocity": -0.60},
        ("strangle", "suffocate", "choke", "throttle", "asphyxiate", "constrict", "smother", "squeeze the throat"),
    ),
    (
        "INGEST",
        ["ANIMATE_BEING"],
        ["SUBSTANCE_LIQUID", "ARTIFACT_SOLID"],
        "NONE",
        {"corrosion_decay": 0.75, "velocity": -0.60, "dominance": -0.70, "valence": -0.50},
        ("digest", "swallow", "ingest", "devour", "consume", "drink", "absorb", "take into the stomach"),
    ),
    (
        "SHATTER_DESTROY",
        ["ANIMATE_BEING", "ARTIFACT_SOLID"],
        ["ARTIFACT_SOLID"],
        "NONE",
        {"sharpness": 0.90, "velocity": 0.85, "arousal": 0.80, "valence": -0.75, "corrosion_decay": 0.80},
        ("shatter", "smash", "splinter", "fracture", "break into pieces", "pulverize", "crush"),
    ),
    (
        "LIGHT_TERMINATION",
        ["ANIMATE_BEING", "SUBSTANCE_LIQUID"],
        ["LIGHT", "THERMAL"],
        "NONE",
        {"luminance": -0.95, "temperature": -0.50, "valence": -0.30},
        ("extinguish", "put out a fire", "put out a light", "snuff", "quench", "douse"),
    ),
    (
        "LIGHT_ACTIVATION",
        ["ANIMATE_BEING", "THERMAL"],
        ["LIGHT", "THERMAL", "ARTIFACT_SOLID"],
        "NONE",
        {"luminance": 0.90, "temperature": 0.85, "arousal": 0.50},
        ("ignite", "set fire", "light a", "kindle", "illuminate"),
    ),
    (
        "VISUAL_PERCEPTION",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "ANIMATE_BEING", "SPACE_CONTAINER"],
        "REQUIRES_LIGHT",
        {"arousal": 0.15},
        ("read", "look at and interpret", "examine visually", "inspect closely", "decipher", "peruse", "watch"),
    ),
    (
        "ACQUIRE_OBJECT",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "LIGHT"],
        "NONE",
        {"dominance": 0.35},
        ("take hold", "grasp", "pick up", "unsheathe", "draw a weapon", "seize"),
    ),
    (
        "RELEASE_OBJECT",
        ["ANIMATE_BEING"],
        ["ARTIFACT_SOLID", "LIGHT"],
        "REQUIRES_HOLDING",
        {"velocity": 0.50},
        ("drop", "let fall", "release from the hand", "relinquish"),
    ),
]

BUILTIN_WIKTIONARY_GLOSSES: List[Tuple[str, str, str]] = [
    ("bark", "noun", "The tough exterior covering of the woody trunk and branches of a tree, oak, or timber."),
    ("bark", "noun", "The short, loud, sharp cry or sound made by a dog, hound, or wolf."),
    ("cold", "adj", "Having a low temperature; freezing, icy, or glacial to the touch."),
    ("cold", "adj", "Unfriendly, emotionless, distant, and lacking warm affection or joy."),
    ("grief", "noun", "A feeling of deep sadness, sorrow, pain, and heavy loss."),
    ("melancholy", "noun", "A feeling of deep sadness, gloom, and slow sorrow."),
    ("silence", "noun", "The state of complete quiet and absence of sound or voice."),
    ("hope", "noun", "A feeling of bright expectation, joy, and warm desire."),
    ("fear", "noun", "A strong, cold emotion of terror, dread, and panic caused by danger."),
    ("anger", "noun", "A strong feeling of hot rage, hostility, and desire to strike."),
    ("bureaucracy", "noun", "An administrative system of government officials characterized by slow, stagnant, heavy rules."),
    ("debt", "noun", "An obligation or heavy burden owed to another person under contract."),
    ("secret", "noun", "Knowledge kept dark and hidden from other people."),
    ("peace", "noun", "A state of calm, quiet, safe tranquility and gentle rest."),
    ("calm", "adj", "Free from anger or sudden motion; quiet, gentle, and peaceful."),
    ("quiet", "adj", "With little or no sound; calm and gentle."),
    ("warm", "adj", "Having a moderate, pleasant heat; friendly and safe."),
    ("safe", "adj", "Protected from danger, harm, or fear; calm and secure."),
    ("gentle", "adj", "Soft, mild, calm, and free from sharp or sudden force."),
    ("breeze", "noun", "A light, gentle, weightless current of air."),
    ("tea", "noun", "A warm, calm beverage made by infusing leaves in water."),
    ("anchor", "noun", "A heavy iron instrument used to moor a vessel to the bottom so it remains immobile."),
    ("anvil", "noun", "A massive, heavy iron block on which metal is hammered."),
    ("steel", "noun", "A hard, strong, heavy metal alloy of iron used for armor and weapons."),
    ("armor", "noun", "A heavy protective metal covering worn in battle."),
    ("glacier", "noun", "A massive, slow, freezing body of ice moving down a slope."),
    ("sunset", "noun", "The bright, warm, glowing light in the sky as the sun goes down."),
    ("executioner", "noun", "A terrifying person who carries out a death sentence with an axe or blade."),
    ("glass", "noun", "A hard, brittle, sharp transparent solid vessel or material that can shatter."),
    ("blade", "noun", "The sharp cutting edge of a metal weapon, knife, or sword."),
    ("dagger", "noun", "A short, sharp pointed knife or blade used as a weapon for piercing."),
    ("razor", "noun", "A keen, ultra-sharp metal instrument used for cutting."),
    ("ash", "noun", "The weightless, dark, decayed powdery residue left after the burning of a substance by fire."),
    ("wildfire", "noun", "A rapid, explosive, scorching conflagration of fire that burns out of control."),
    ("acid", "noun", "A sour, sharp, corrosive liquid solution that dissolves and corrodes metal."),
    ("poison", "noun", "A toxic liquid or substance that causes pain, decay, or death when swallowed."),
    ("lantern", "noun", "A portable transparent case or lamp for holding a bright light or flame."),
    ("inscription", "noun", "Words or letters carved into a solid stone or metal monument."),
    ("letter", "noun", "A written document or message on paper."),
    ("room", "noun", "A chamber or enclosed space within a building."),
    ("tavern", "noun", "A public house or building where ale and wine are served at tables."),
    ("oak", "noun", "A massive forest tree bearing acorns and rough timber bark."),
    ("hound", "noun", "A domestic dog bred for hunting."),
    ("rusted", "adj", "Corroded, decayed, and covered with slow iron rust."),
    ("corroded", "adj", "Eaten away by acid or rust; decayed and weakened."),
    ("shattered", "adj", "Broken suddenly into sharp, jagged fragments and ruined."),
    ("explosive", "adj", "Tending to explode suddenly with violent fire and heat."),
    ("screaming", "adj", "Uttering a sudden, sharp, terrified scream of pain or rage."),
    ("bleeding", "adj", "Losing blood from a cut or painful wound."),
    ("love", "verb", "To feel deep warm affection, joy, and delight toward someone."),
    ("happy", "adj", "Feeling joy, pleasure, and warm delight."),
    ("pleasure", "noun", "A state of joy, delight, and warm satisfaction."),
    ("wonderful", "adj", "Tending to excite delight, pleasure, and joy; admirable."),
    ("thrilled", "adj", "Suddenly filled with pleasure, joy, and delight."),
    ("fine", "adj", "Acceptable, pure, or satisfactory."),
    ("frown", "verb", "To wrinkle the brow in anger, displeasure, or gloom."),
    ("snarl", "verb", "To growl with sharp teeth bared in anger and rage."),
    ("sneer", "verb", "To smile or speak with cold contempt, insult, and hatred."),
    ("insult", "verb", "To speak to with sharp disrespect, pain, and hostility."),
    ("strangle", "verb", "To squeeze the throat so as to choke, suffocate, and kill."),
    ("digest", "verb", "To swallow and dissolve food in the stomach."),
    ("extinguish", "verb", "To put out a light, lamp, or fire; to quench or snuff."),
    ("read", "verb", "To look at and interpret letters or an inscription visually."),
    ("drop", "verb", "To let fall or release from the hand."),
    ("take", "verb", "To grasp or pick up an object with the hand."),
    ("slaughter", "verb", "To butcher or kill violently in a bloody massacre."),
    ("burn", "verb", "To destroy or consume with hot fire and flame."),
    ("kick the bucket", "verb", "(idiomatic) To die; to pass away."),
    ("kicked the bucket", "verb", "(idiomatic) To die; to pass away."),
    ("bite the dust", "verb", "(idiomatic) To die or fail completely in battle."),
    ("bit the dust", "verb", "(idiomatic) To die or fail completely in battle."),
    ("spill the beans", "verb", "(idiomatic) To reveal a secret prematurely."),
    ("put out", "verb", "To extinguish a light, lamp, candle, or fire."),
    ("give up", "verb", "To surrender, despair, and cease effort."),
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
    g_low = gloss.lower()
    tokens = TOKEN_RE.findall(g_low)

    domain = "ABSTRACT_STATE" if pos in ("adj", "adv") else "ARTIFACT_SOLID"
    concreteness = 0.50
    for cand_domain, cand_conc, keywords in GENUS_DOMAIN_RULES:
        if any(k in g_low for k in keywords):
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
    g = gloss.lower()
    vis = 0.75 if domain in ("ARTIFACT_SOLID", "LIGHT", "SPACE_CONTAINER", "ANIMATE_BEING") else 0.25
    aud = 0.90 if domain == "SOUND" or any(k in g for k in ("sound", "cry", "noise", "voice", "loud", "quiet")) else 0.10
    hap = 0.80 if abs(phys.get("sharpness", 0)) >= 0.5 or abs(phys.get("temperature", 0)) >= 0.5 or abs(phys.get("mass_weight", 0)) >= 0.5 else 0.15
    olf = 0.85 if any(k in g for k in ("smell", "odor", "scent", "stench", "aroma", "fragrant", "reek")) else 0.05
    gus = 0.85 if any(k in g for k in ("taste", "sweet", "sour", "bitter", "salty", "flavor", "beverage", "food", "drink")) else 0.05
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

    gloss_rows: List[Tuple[str, str, str]] = list(BUILTIN_WIKTIONARY_GLOSSES)
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

        for cue_tok in TOKEN_RE.findall(gloss.lower())[:12]:
            if len(cue_tok) >= 3 and cue_tok not in ("the", "and", "with", "from", "made"):
                concept_edge_rows.append((w, "SenseContext", cue_tok, 0.70))

        if p.startswith("v"):
            g_low = gloss.lower()
            for mutation, req_s, req_o, precond, imp_phys, triggers in VERB_FRAME_RULES:
                if any(t in g_low for t in triggers) or w in triggers:
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