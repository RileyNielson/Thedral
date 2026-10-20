#!/usr/bin/env python3
"""
One-command downloader and multi-source compiler for cognitive_lexicon.db.

Merges:
1. WordNet 3.1 (via nltk/wn): 117k synsets, 45 lexicographer ontological domains, hypernyms/meronyms, MWEs
2. Brysbaert Concreteness Ratings (40k English lemmas)
3. Lancaster Sensorimotor Norms (40k words across 6 perceptual modalities & 5 action effectors)
4. NRC Valence-Arousal-Dominance (VAD) Lexicon (if local TSV provided)
5. Wiktionary SQLite Database (Full table extraction: senses, nyms, forms, qualifiers, IPA phonetics)
6. Multi-Pass NSM Semantic Primitive Propagation (for 100% coverage of unrated words)
"""

import argparse
import csv
import io
import json
import os
import re
import sqlite3
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from cognitive_reader.compiler import (
    BUILTIN_WIKTIONARY_GLOSSES,
    DEFAULT_DB_PATH,
    PRAGMATIC_CONSTRUCTIONS,
    VERB_FRAME_RULES,
    _generate_combinatorial_somatic_markers,
    _infer_mwe_canonical,
    score_gloss_from_primitives,
)
from cognitive_reader.wiktionary_ingestor import WiktionaryFullIngestor, compute_phonetic_texture

CACHE_DIR = Path(__file__).resolve().parent.parent / ".lexicon_cache"

# Public open-science mirror URLs for psycholinguistic norm tables
OPEN_NORM_URLS = {
    "brysbaert_concreteness": (
        "https://raw.githubusercontent.com/ArtsEngine/concreteness/master/"
        "Concreteness_ratings_Brysbaert_et_al_BRM.txt"
    ),
    "lancaster_sensorimotor": (
        "https://osf.io/download/48wsc/"  # Official OSF CSV download for Lynott et al. Lancaster Norms
    ),
}

MASTER_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- 1. Polysemous Sense-Level Vectors + 6 Perceptual Modalities + Phonosemantics + Register
CREATE TABLE IF NOT EXISTS lexicon_senses (
    lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    sense_id INTEGER NOT NULL,
    ontological_domain TEXT NOT NULL,
    context_cues TEXT DEFAULT '',
    register_tier TEXT DEFAULT 'NEUTRAL', -- 'FORMAL_LATINATE' | 'VISCERAL_GERMANIC' | 'COLLOQUIAL_SLANG' | 'ARCHAIC' | 'NEUTRAL'
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
    -- 6 Perceptual Modalities (0.0 to 1.0, Lancaster Sensorimotor Norms)
    sensory_visual REAL DEFAULT 0.0,
    sensory_auditory REAL DEFAULT 0.0,
    sensory_haptic REAL DEFAULT 0.0,
    sensory_olfactory REAL DEFAULT 0.0,
    sensory_gustatory REAL DEFAULT 0.0,
    sensory_interoceptive REAL DEFAULT 0.0,
    -- Phonosemantics (0.0 to 1.0)
    plosive_impact REAL DEFAULT 0.0,
    sonorant_flow REAL DEFAULT 0.0,
    PRIMARY KEY (lemma, pos, sense_id)
);

-- 2. Exact Irregular & Inflected Forms Lookup (From Wiktionary `forms` + WordNet morphy)
CREATE TABLE IF NOT EXISTS inflected_forms (
    surface_form TEXT PRIMARY KEY,
    canonical_lemma TEXT NOT NULL,
    pos TEXT NOT NULL,
    morph_tags TEXT DEFAULT ''
);

-- 3. Multi-Word Expressions (Idioms & Phrasal Verbs)
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

-- 4. Verb Selectional Frames & State Mutations
CREATE TABLE IF NOT EXISTS verb_frames (
    verb_lemma TEXT PRIMARY KEY,
    required_subj_domains TEXT NOT NULL,
    required_obj_domains TEXT NOT NULL,
    state_mutation TEXT NOT NULL,
    precondition TEXT DEFAULT 'NONE',
    imposed_physics_json TEXT NOT NULL
);

-- 5. Combinatorial Somatic & Performative Markers
CREATE TABLE IF NOT EXISTS somatic_markers (
    phrase_pattern TEXT PRIMARY KEY,
    body_channel TEXT NOT NULL,
    control_type TEXT NOT NULL,
    surface_valence REAL NOT NULL,
    internal_stress REAL NOT NULL,
    subtext_diagnosis TEXT NOT NULL
);

-- 6. Pragmatic Irony & Sarcasm Constructions
CREATE TABLE IF NOT EXISTS pragmatic_constructions (
    construction_id TEXT PRIMARY KEY,
    regex_pattern TEXT NOT NULL,
    required_surface_polarity INTEGER NOT NULL,
    irony_multiplier REAL NOT NULL,
    pragmatic_label TEXT NOT NULL
);

-- 7. Spreading Activation Concept Graph (Hypernyms, Meronyms, Antonyms, Primitives)
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

WORDNET_LEXNAME_TO_DOMAIN = {
    "noun.feeling": ("ABSTRACT_STATE", 0.12),
    "noun.cognition": ("ABSTRACT_STATE", 0.15),
    "noun.attribute": ("ABSTRACT_STATE", 0.20),
    "noun.state": ("ABSTRACT_STATE", 0.18),
    "noun.motive": ("ABSTRACT_STATE", 0.15),
    "noun.relation": ("ABSTRACT_STATE", 0.20),
    "noun.time": ("ABSTRACT_STATE", 0.12),
    "noun.communication": ("SOCIAL_CONSTRUCT", 0.25),
    "noun.group": ("SOCIAL_CONSTRUCT", 0.25),
    "noun.act": ("SOCIAL_CONSTRUCT", 0.30),
    "noun.possession": ("SOCIAL_CONSTRUCT", 0.28),
    "noun.artifact": ("ARTIFACT_SOLID", 0.94),
    "noun.object": ("ARTIFACT_SOLID", 0.92),
    "noun.food": ("ARTIFACT_SOLID", 0.92),
    "noun.plant": ("ARTIFACT_SOLID", 0.92),
    "noun.shape": ("ARTIFACT_SOLID", 0.75),
    "noun.substance": ("SUBSTANCE_LIQUID", 0.88),
    "noun.person": ("ANIMATE_BEING", 0.95),
    "noun.animal": ("ANIMATE_BEING", 0.95),
    "noun.body": ("ANIMATE_BEING", 0.96),
    "noun.location": ("SPACE_CONTAINER", 0.92),
    "noun.phenomenon": ("THERMAL", 0.80),
    "adj.all": ("ABSTRACT_STATE", 0.45),
    "adj.pert": ("ABSTRACT_STATE", 0.45),
    "verb.consumption": ("SUBSTANCE_LIQUID", 0.75),
    "verb.contact": ("ARTIFACT_SOLID", 0.80),
    "verb.perception": ("LIGHT", 0.65),
    "verb.emotion": ("ABSTRACT_STATE", 0.20),
    "verb.cognition": ("ABSTRACT_STATE", 0.15),
    "verb.communication": ("SOUND", 0.45),
    "verb.weather": ("THERMAL", 0.80),
}


def download_cached_file(name: str, url: str) -> Optional[Path]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = CACHE_DIR / f"{name}.tsv"
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"  [Cache Hit] {dest.name}")
        return dest
    print(f"  [Downloading] {name} from {url} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CognitiveReaderCompiler/0.2"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
        dest.write_bytes(raw)
        print(f"  [Saved] {dest} ({len(raw) / 1024:.1f} KB)")
        return dest
    except Exception as exc:
        print(f"  [Warning] Could not download {name}: {exc}. Proceeding with local/WordNet fallbacks.")
        return None


def classify_register_tier(word: str, tags: Iterable[str] = ()) -> str:
    tag_set = {t.lower() for t in tags}
    if tag_set & {"slang", "colloquial", "informal", "vulgar"}:
        return "COLLOQUIAL_SLANG"
    if tag_set & {"archaic", "obsolete", "dated"}:
        return "ARCHAIC"
    if tag_set & {"formal", "literary", "technical"} or word.endswith(
        ("tion", "sion", "ment", "ence", "ance", "ity", "ology", "escence")
    ):
        return "FORMAL_LATINATE"
    if len(word) <= 5 and not word.endswith(("ia", "um", "us", "ic")):
        return "VISCERAL_GERMANIC"
    return "NEUTRAL"


def infer_sensory_profile_from_gloss(domain: str, gloss: str, phys: Dict[str, float]) -> Dict[str, float]:
    """Fallback sensory modality estimator when Lancaster norms aren't loaded."""
    g = gloss.lower()
    vis = 0.75 if domain in ("ARTIFACT_SOLID", "LIGHT", "SPACE_CONTAINER", "ANIMATE_BEING") else 0.25
    aud = 0.90 if domain == "SOUND" or any(k in g for k in ("sound", "cry", "noise", "voice", "loud", "quiet")) else 0.10
    hap = 0.80 if abs(phys.get("sharpness", 0)) >= 0.5 or abs(phys.get("temperature", 0)) >= 0.5 or abs(phys.get("mass_weight", 0)) >= 0.5 else 0.15
    olf = 0.85 if any(k in g for k in ("smell", "odor", "scent", "stench", "aroma", "fragrant", "reek")) else 0.05
    gus = 0.85 if any(k in g for k in ("taste", "sweet", "sour", "bitter", "salty", "flavor", "beverage", "food", "drink")) else 0.05
    intero = 0.85 if domain == "ABSTRACT_STATE" or abs(phys.get("valence", 0)) >= 0.65 or any(k in g for k in ("pain", "heart", "breath", "stomach", "gut", "nausea", "ache", "dread", "terror", "grief")) else 0.10
    return {
        "sensory_visual": round(vis, 3),
        "sensory_auditory": round(aud, 3),
        "sensory_haptic": round(hap, 3),
        "sensory_olfactory": round(olf, 3),
        "sensory_gustatory": round(gus, 3),
        "sensory_interoceptive": round(intero, 3),
    }


def harvest_wordnet_entries(max_synsets: Optional[int] = None) -> Tuple[List[Tuple[str, str, str, str, float]], List[Tuple[str, str, str, float]]]:
    """
    Bootstraps NLTK WordNet (downloading it automatically if missing) and extracts:
    1. (lemma, pos, gloss, ontological_domain, baseline_concreteness)
    2. (source_lemma, relation, target_lemma, weight) for Hypernyms, Meronyms, and Antonyms.
    """
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        try:
            wn.synsets("anchor")
        except LookupError:
            print("  [WordNet] Downloading NLTK WordNet corpus...")
            nltk.download("wordnet", quiet=True)
            nltk.download("omw-1.4", quiet=True)
    except Exception as exc:
        print(f"  [WordNet] NLTK not installed ({exc}); skipping WordNet harvest.")
        return [], []

    print("  [WordNet] Harvesting synsets, ontological lexnames, and hypernym/meronym graphs...")
    gloss_entries: List[Tuple[str, str, str, str, float]] = []
    edges: List[Tuple[str, str, str, float]] = []

    pos_map = {"n": "noun", "v": "verb", "a": "adj", "s": "adj", "r": "adv"}
    count = 0
    for syn in wn.all_synsets():
        count += 1
        if max_synsets and count > max_synsets:
            break
        pos = pos_map.get(syn.pos(), "noun")
        lexname = syn.lexname()
        domain, base_conc = WORDNET_LEXNAME_TO_DOMAIN.get(lexname, ("ARTIFACT_SOLID" if pos == "noun" else "ABSTRACT_STATE", 0.50))
        gloss = syn.definition()
        examples = " ; ".join(syn.examples())
        full_gloss = f"{gloss}. {examples}" if examples else gloss

        lemma_names = [l.name().lower().replace("_", " ") for l in syn.lemmas()]
        for l_Obj, l_name in zip(syn.lemmas(), lemma_names):
            gloss_entries.append((l_name, pos, full_gloss, domain, base_conc))
            for ant in l_Obj.antonyms():
                edges.append((l_name, "ANTONYM", ant.name().lower().replace("_", " "), 0.95))

        if lemma_names:
            primary = lemma_names[0]
            for hyper in syn.hypernyms():
                for hl in hyper.lemmas():
                    edges.append((primary, "HYPERNYM", hl.name().lower().replace("_", " "), 0.90))
            for mero in syn.part_meronyms():
                for ml in mero.lemmas():
                    edges.append((primary, "MERONYM", ml.name().lower().replace("_", " "), 0.85))

    print(f"  [WordNet] Harvested {len(gloss_entries)} sense definitions and {len(edges)} semantic edges.")
    return gloss_entries, edges


def compile_master_lexicon(
    output_db_path: Path = DEFAULT_DB_PATH,
    wiktionary_sqlite_path: Optional[str] = None,
    nrc_vad_tsv_path: Optional[str] = None,
    concreteness_tsv_path: Optional[str] = None,
    lancaster_tsv_path: Optional[str] = None,
    download_open_norms: bool = True,
    include_wordnet: bool = True,
    wordnet_limit: Optional[int] = None,
) -> Dict[str, object]:
    output_db_path = Path(output_db_path)
    output_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(output_db_path))
    cur = conn.cursor()
    cur.executescript(MASTER_SCHEMA_SQL)

    # 1. Gather raw glosses from Built-in + WordNet + Wiktionary SQLite
    # Tuple format: (lemma, pos, gloss, override_domain, override_concreteness, tags, ipa)
    unified_entries: List[Tuple[str, str, str, Optional[str], Optional[float], List[str], str]] = []
    concept_edge_rows: List[Tuple[str, str, str, float]] = []
    inflected_rows: List[Tuple[str, str, str, str]] = [
        ("extinguished", "extinguish", "verb", "PAST"),
        ("strangled", "strangle", "verb", "PAST"),
        ("digested", "digest", "verb", "PAST"),
        ("shattered", "shatter", "verb", "PAST"),
        ("snuffed", "snuff", "verb", "PAST"),
        ("lit", "ignite", "verb", "PAST"),
        ("drew", "draw", "verb", "PAST"),
        ("drawn", "draw", "verb", "PTCP"),
        ("took", "take", "verb", "PAST"),
        ("taken", "take", "verb", "PTCP"),
        ("dropped", "drop", "verb", "PAST"),
        ("kicked", "kick", "verb", "PAST"),
        ("barked", "bark", "verb", "PAST"),
    ]

    for w, p, g in BUILTIN_WIKTIONARY_GLOSSES:
        unified_entries.append((w, p, g, None, None, [], ""))

    if include_wordnet:
        wn_entries, wn_edges = harvest_wordnet_entries(max_synsets=wordnet_limit)
        for w, p, g, dom, conc in wn_entries:
            unified_entries.append((w, p, g, dom, conc, [], ""))
        concept_edge_rows.extend(wn_edges)

    if wiktionary_sqlite_path and os.path.exists(wiktionary_sqlite_path):
        print(f"  [Wiktionary] Streaming full schema from {wiktionary_sqlite_path}...")
        ingestor = WiktionaryFullIngestor(wiktionary_sqlite_path)
        for rec in ingestor.iter_rich_entries():
            lemma = str(rec["lemma"])
            pos = str(rec["pos"])
            gloss = str(rec["gloss"])
            tags = list(rec.get("tags", []))
            ipa = str(rec.get("ipa", ""))
            unified_entries.append((lemma, pos, gloss, None, None, tags, ipa))
            for rel, tgt in rec.get("nyms", []):
                concept_edge_rows.append((lemma, rel, tgt, 0.92))
            for surf in rec.get("forms", []):
                if surf != lemma and len(surf) >= 2:
                    inflected_rows.append((surf, lemma, pos, "WIKTIONARY_FORM"))
        for edge in ingestor.iter_nym_edges():
            concept_edge_rows.append(edge)

    # 2. Pass 1 & Pass 2 Primitive Propagation
    print(f"  [Compiler] Running 2-Pass Semantic Primitive Propagation over {len(unified_entries)} entries...")
    known_vectors: Dict[str, Dict[str, float]] = {}
    mwe_rows = []
    verb_frame_map: Dict[str, Tuple[str, str, str, str, str, str]] = {}

    for lemma, pos, gloss, ov_dom, ov_conc, tags, ipa in unified_entries:
        w = lemma.strip().lower()
        p = (pos or "noun").strip().lower()
        if " " in w:
            mwe_type, canon, val, aro, dom_v = _infer_mwe_canonical(w, gloss)
            mwe_rows.append((w, mwe_type, canon, ov_dom or "ABSTRACT_STATE", 1, val, aro, dom_v))
            continue

        domain, phys, edges, _ = score_gloss_from_primitives(w, p, gloss, known_vectors=None)
        if ov_dom:
            domain = ov_dom
        if ov_conc is not None and phys["concreteness"] == 0.5:
            phys["concreteness"] = ov_conc

        if w not in known_vectors:
            known_vectors[w] = {"domain": domain, "pos": p, **phys}

        for target_prim in set(edges):
            if target_prim != w:
                concept_edge_rows.append((w, "GroundedInPrimitive", target_prim, 0.85))

        if p.startswith("v") and w not in verb_frame_map:
            g_low = gloss.lower()
            for mutation, req_s, req_o, precond, imp_phys, triggers in VERB_FRAME_RULES:
                if any(t in g_low for t in triggers) or w in triggers:
                    verb_frame_map[w] = (
                        w, json.dumps(req_s), json.dumps(req_o), mutation, precond, json.dumps(imp_phys)
                    )
                    break

    # Pass 2: Build Sense Rows with 6 Perceptual Modalities & Phonosemantics
    sense_counters: Dict[Tuple[str, str], int] = {}
    sense_rows = []
    for lemma, pos, gloss, ov_dom, ov_conc, tags, ipa in unified_entries:
        w = lemma.strip().lower()
        if " " in w or not w:
            continue
        p = (pos or "noun").strip().lower()
        key = (w, p)
        sense_id = sense_counters.get(key, 0) + 1
        if sense_id > 8:  # Cap at top 8 distinct senses per (lemma, pos) for fast runtime lookup
            continue
        sense_counters[key] = sense_id

        domain, phys, _, cues = score_gloss_from_primitives(w, p, gloss, known_vectors=known_vectors)
        if ov_dom and domain == "ARTIFACT_SOLID" and phys["concreteness"] == 0.5:
            domain = ov_dom
        if ov_conc is not None and phys["concreteness"] == 0.5:
            phys["concreteness"] = ov_conc

        reg_tier = classify_register_tier(w, tags)
        sensory = infer_sensory_profile_from_gloss(domain, gloss, phys)
        phonetics = compute_phonetic_texture(ipa or w)

        sense_rows.append((
            w, p, sense_id, domain, cues, reg_tier,
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
    cur.executemany("INSERT OR REPLACE INTO inflected_forms VALUES (?, ?, ?, ?)", inflected_rows)
    cur.executemany("INSERT OR REPLACE INTO mwe_lexicon VALUES (?, ?, ?, ?, ?, ?, ?, ?)", mwe_rows)
    cur.executemany("INSERT OR REPLACE INTO verb_frames VALUES (?, ?, ?, ?, ?, ?)", list(verb_frame_map.values()))
    cur.executemany("INSERT OR IGNORE INTO concept_edges VALUES (?, ?, ?, ?)", concept_edge_rows)
    cur.executemany("INSERT OR REPLACE INTO somatic_markers VALUES (?, ?, ?, ?, ?, ?)", _generate_combinatorial_somatic_markers())
    cur.executemany("INSERT OR REPLACE INTO pragmatic_constructions VALUES (?, ?, ?, ?, ?)", PRAGMATIC_CONSTRUCTIONS)

    # 3. Overlay Published Psycholinguistic Norm Tables (Brysbaert, Lancaster, NRC VAD)
    if download_open_norms and not concreteness_tsv_path:
        dl_conc = download_cached_file("brysbaert_concreteness", OPEN_NORM_URLS["brysbaert_concreteness"])
        if dl_conc:
            concreteness_tsv_path = str(dl_conc)

    if download_open_norms and not lancaster_tsv_path:
        dl_lanc = download_cached_file("lancaster_sensorimotor", OPEN_NORM_URLS["lancaster_sensorimotor"])
        if dl_lanc:
            lancaster_tsv_path = str(dl_lanc)

    conc_overlaid = _overlay_brysbaert_concreteness(cur, concreteness_tsv_path)
    lanc_overlaid = _overlay_lancaster_norms(cur, lancaster_tsv_path)
    vad_overlaid = _overlay_nrc_vad(cur, nrc_vad_tsv_path)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM lexicon_senses")
    total_senses = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM mwe_lexicon")
    total_mwes = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM concept_edges")
    total_edges = cur.fetchone()[0]
    conn.close()

    return {
        "db_path": str(output_db_path),
        "total_senses": total_senses,
        "total_mwes": total_mwes,
        "total_concept_edges": total_edges,
        "brysbaert_concreteness_overlaid": conc_overlaid,
        "lancaster_sensorimotor_overlaid": lanc_overlaid,
        "nrc_vad_overlaid": vad_overlaid,
    }


def _overlay_brysbaert_concreteness(cur: sqlite3.Cursor, filepath: Optional[str]) -> int:
    if not filepath or not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        batch = []
        for row in reader:
            word = (row.get("Word") or "").strip().lower()
            conc_m = row.get("Conc.M")
            if not word or not conc_m:
                continue
            try:
                conc = round(max(0.0, min(1.0, (float(conc_m) - 1.0) / 4.0)), 3)
            except ValueError:
                continue
            batch.append((conc, word))
            count += 1
        cur.executemany("UPDATE lexicon_senses SET concreteness = ? WHERE lemma = ?", batch)
    return count


def _overlay_lancaster_norms(cur: sqlite3.Cursor, filepath: Optional[str]) -> int:
    if not filepath or not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        first_line = f.readline()
        delim = "\t" if "\t" in first_line else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delim)
        batch = []
        for row in reader:
            word = (row.get("Word") or row.get("word") or "").strip().lower()
            if not word:
                continue
            try:
                vis = round(float(row.get("Visual.mean", 0.0)) / 5.0, 3)
                aud = round(float(row.get("Auditory.mean", 0.0)) / 5.0, 3)
                hap = round(float(row.get("Haptic.mean", 0.0)) / 5.0, 3)
                olf = round(float(row.get("Olfactory.mean", 0.0)) / 5.0, 3)
                gus = round(float(row.get("Gustatory.mean", 0.0)) / 5.0, 3)
                inter = round(float(row.get("Interoceptive.mean", 0.0)) / 5.0, 3)
            except ValueError:
                continue
            batch.append((vis, aud, hap, olf, gus, inter, word))
            count += 1
        cur.executemany(
            """
            UPDATE lexicon_senses
            SET sensory_visual=?, sensory_auditory=?, sensory_haptic=?,
                sensory_olfactory=?, sensory_gustatory=?, sensory_interoceptive=?
            WHERE lemma=?
            """,
            batch,
        )
    return count


def _overlay_nrc_vad(cur: sqlite3.Cursor, filepath: Optional[str]) -> int:
    if not filepath or not os.path.exists(filepath):
        return 0
    count = 0
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f, delimiter="\t")
        batch = []
        for row in reader:
            word = (row.get("Word") or row.get("word") or "").strip().lower()
            if not word:
                continue
            try:
                v = round((float(row.get("Valence", 0.5)) * 2.0) - 1.0, 3)
                a = round((float(row.get("Arousal", 0.5)) * 2.0) - 1.0, 3)
                d = round((float(row.get("Dominance", 0.5)) * 2.0) - 1.0, 3)
            except ValueError:
                continue
            batch.append((v, a, d, word))
            count += 1
        cur.executemany(
            "UPDATE lexicon_senses SET valence=?, arousal=?, dominance=? WHERE lemma=?",
            batch,
        )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch open psycholinguistic norms and compile cognitive_lexicon.db")
    parser.add_argument("--output", type=Path, default=DEFAULT_DB_PATH, help="Output SQLite DB path")
    parser.add_argument("--wiktionary-db", type=str, default=None, help="Path to local Wiktionary SQLite file")
    parser.add_argument("--nrc-vad-tsv", type=str, default=None, help="Path to local NRC-VAD-Lexicon.txt")
    parser.add_argument("--concreteness-tsv", type=str, default=None, help="Path to Brysbaert concreteness TSV")
    parser.add_argument("--lancaster-tsv", type=str, default=None, help="Path to Lancaster Sensorimotor TSV/CSV")
    parser.add_argument("--no-download", action="store_true", help="Offline build only (skip HTTP downloads)")
    parser.add_argument("--no-wordnet", action="store_true", help="Skip NLTK WordNet ingestion")
    parser.add_argument("--wordnet-limit", type=int, default=None, help="Optional cap on WordNet synsets for quick testing")
    args = parser.parse_args()

    stats = compile_master_lexicon(
        output_db_path=args.output,
        wiktionary_sqlite_path=args.wiktionary_db,
        nrc_vad_tsv_path=args.nrc_vad_tsv,
        concreteness_tsv_path=args.concreteness_tsv,
        lancaster_tsv_path=args.lancaster_tsv,
        download_open_norms=not args.no_download,
        include_wordnet=not args.no_wordnet,
        wordnet_limit=args.wordnet_limit,
    )
    print("\n[Master Lexicon Build Complete]")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()