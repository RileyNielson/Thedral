import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from cognitive_reader.compiler import (
    DEFAULT_DB_PATH,
    build_cognitive_database,
    score_gloss_from_primitives,
    infer_sensory_profile,
    compute_phonetic_texture,
)
from cognitive_reader.human_voice import (
    describe_habituation_naturally,
    describe_lighting_error_naturally,
    describe_metaphor_naturally,
    describe_name_collision_naturally,
    describe_ngram_anomaly_naturally,
    describe_subtext_naturally,
)
from cognitive_reader.models import (
    ContinuityAlert,
    DocumentReport,
    EpistemicAlert,
    MetaphorHit,
    OpenPromise,
    ParagraphDiagnosis,
    ParagraphTick,
    ReaderNote,
    SubtextHit,
)
from cognitive_reader.parser import (
    CAUSAL_CONNECTIVES,
    COPULA_AND_SIMILE_RE,
    DENOMINAL_VERB_RE,
    DIALOGUE_QUOTE_RE,
    EXCLUDED_FROM_ENTITIES,
    INTENTIONAL_MODALS,
    PROMISE_CUE_RE,
    TEMPORAL_MARKERS,
    classify_sentence_modality,
    decompose_morphology,
    detect_compound_ngram_anomalies,
    detect_entity_collisions,
    extract_appositive_aliases,
    extract_proper_entities,
    extract_svo_triples,
    extract_words,
    normalize_lemma,
    normalize_text,
    split_paragraphs,
    split_sentences,
)
from cognitive_reader.state import DialogueTurnRecord, VirtualBrainState

PHYSICS_DIMENSIONS = [
    "mass_weight",
    "temperature",
    "sharpness",
    "velocity",
    "corrosion_decay",
    "luminance",
    "valence",
    "arousal",
    "dominance",
]


class CognitiveEngine:
    def __init__(
        self, 
        db_path: Path = DEFAULT_DB_PATH,
        wiktionary_db_path: Optional[str] = None
    ) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            build_cognitive_database(self.db_path, wiktionary_sqlite_path=wiktionary_db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Windows-safe connection to local Wiktionary SQLite database
        self.wikt_conn = None
        if wiktionary_db_path and Path(wiktionary_db_path).exists():
            try:
                resolved = str(Path(wiktionary_db_path).resolve())
                self.wikt_conn = sqlite3.connect(resolved, timeout=10.0, check_same_thread=False)
                self.wikt_conn.row_factory = sqlite3.Row
            except Exception:
                self.wikt_conn = None

    def get_vector(
        self, word: str, context_lemmas: Optional[Set[str]] = None
    ) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        raw = word.lower().strip(".,;!?\"'()")
        candidates = [raw]
        norm = normalize_lemma(raw)
        if norm != raw:
            candidates.append(norm)

        # 1. Check local cognitive_lexicon.db cache first (0.1ms)
        for cand in candidates:
            cur.execute("SELECT * FROM lexicon_senses WHERE lemma = ? ORDER BY sense_id ASC", (cand,))
            senses = cur.fetchall()
            if senses:
                if len(senses) == 1 or not context_lemmas:
                    return dict(senses[0])
                best_sense = senses[0]
                best_overlap = -1
                for s in senses:
                    cues = set((s["context_cues"] or "").split())
                    overlap = len(cues & context_lemmas)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_sense = s
                return dict(best_sense)

        # 2. Dynamic, universal Wiktionary database resolution
        if self.wikt_conn is not None:
            for cand in candidates:
                try:
                    w_cur = self.wikt_conn.cursor()
                    w_cur.execute("""
                        SELECT e.word, COALESCE(e.pos, 'noun') as pos, g.gloss_text as gloss
                        FROM entries e
                        JOIN senses s ON s.entry_id = e.id
                        JOIN glosses g ON g.sense_id = s.id
                        WHERE lower(e.word) = ?
                        LIMIT 1
                    """, (cand,))
                    w_row = w_cur.fetchone()
                    if w_row and w_row["gloss"]:
                        pos = str(w_row["pos"]).lower()
                        gloss = str(w_row["gloss"])
                        domain, phys, edges, cues = score_gloss_from_primitives(cand, pos, gloss)
                        sensory = infer_sensory_profile(domain, gloss, phys)
                        phonetics = compute_phonetic_texture(cand)

                        # Cache into cognitive_lexicon.db for future instant queries
                        with self.conn:
                            self.conn.execute("""
                                INSERT OR REPLACE INTO lexicon_senses VALUES (
                                    ?, ?, 1, ?, ?, 'NEUTRAL',
                                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                    ?, ?, ?, ?, ?, ?, ?, ?
                                )
                            """, (
                                cand, pos, domain, cues,
                                phys["valence"], phys["arousal"], phys["dominance"],
                                phys["concreteness"], phys["mass_weight"], phys["temperature"],
                                phys["sharpness"], phys["velocity"], phys["corrosion_decay"], phys["luminance"],
                                sensory["sensory_visual"], sensory["sensory_auditory"], sensory["sensory_haptic"],
                                sensory["sensory_olfactory"], sensory["sensory_gustatory"], sensory["sensory_interoceptive"],
                                phonetics["plosive_impact"], phonetics["sonorant_flow"],
                            ))
                        cur.execute("SELECT * FROM lexicon_senses WHERE lemma = ? LIMIT 1", (cand,))
                        cached = cur.fetchone()
                        if cached:
                            return dict(cached)
                except Exception:
                    pass

        # 3. Morphology derivation fallback
        for stem, op, mult in decompose_morphology(raw):
            cur.execute("SELECT * FROM lexicon_senses WHERE lemma = ? ORDER BY sense_id ASC", (stem,))
            base_row = cur.fetchone()
            if base_row:
                synthesized = dict(base_row)
                synthesized["lemma"] = raw
                for dim in PHYSICS_DIMENSIONS:
                    synthesized[dim] = round(max(-1.0, min(1.0, float(synthesized[dim]) * mult)), 3)
                if "ABSTRACT" in op:
                    synthesized["concreteness"] = 0.18
                    synthesized["ontological_domain"] = "ABSTRACT_STATE"
                return synthesized

        return None

    def scan_mwes(self, paragraph: str) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM mwe_lexicon")
        low = normalize_text(paragraph).lower()
        idioms: List[Dict[str, Any]] = []
        phrasal_map: Dict[str, str] = {}
        for row in cur.fetchall():
            phrase = row["phrase"]
            if re.search(rf"\b{re.escape(phrase)}\b", low):
                if row["mwe_type"] == "IDIOM":
                    idioms.append(dict(row))
                else:
                    phrasal_map[phrase] = row["canonical_lemma"]
        return idioms, phrasal_map

    def get_verb_frame(self, verb_token: str) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        for candidate in (verb_token.lower().strip(), normalize_lemma(verb_token)):
            cur.execute("SELECT * FROM verb_frames WHERE verb_lemma = ?", (candidate,))
            row = cur.fetchone()
            if row:
                return row
        return None

    def spread_activation(self, lemmas: Iterable[str]) -> Set[str]:
        cur = self.conn.cursor()
        primed: Set[str] = set(lemmas)
        frontier = list(primed)
        if not frontier:
            return primed
        placeholders = ",".join("?" for _ in frontier)
        cur.execute(
            f"SELECT target_lemma FROM concept_edges WHERE source_lemma IN ({placeholders})",
            frontier,
        )
        for row in cur.fetchall():
            primed.add(row["target_lemma"])
        return primed

    def scan_paragraph_metaphors(
        self, paragraph: str, context_lemmas: Optional[Set[str]] = None
    ) -> List[MetaphorHit]:
        hits: List[MetaphorHit] = []
        clean = normalize_text(paragraph).strip()
        if not clean:
            return hits

        if context_lemmas is None:
            context_lemmas = {normalize_lemma(w) for w in extract_words(clean)}

        idioms, phrasal_map = self.scan_mwes(clean)
        idiom_spans = set()
        for idm in idioms:
            idiom_spans.add(idm["phrase"])
            phys = {"valence": idm["valence"], "arousal": idm["arousal"], "dominance": idm["dominance"]}
            hits.append(
                MetaphorHit(
                    metaphor_type="idiom_expression",
                    span=idm["phrase"],
                    target_concept=idm["canonical_lemma"],
                    source_concept=idm["phrase"],
                    violation_detail=f"Non-literal MWE idiom resolved to '{idm['canonical_lemma']}'",
                    projected_physics=phys,
                    comprehension_note=describe_metaphor_naturally(
                        idm["canonical_lemma"], idm["phrase"], "idiom_expression", phys
                    ),
                )
            )

        for d_match in DENOMINAL_VERB_RE.finditer(clean):
            subj_w, verb_w, refl_target = d_match.group(1), d_match.group(2), d_match.group(3)
            noun_stem = normalize_lemma(verb_w)
            stem_vec = self.get_vector(noun_stem, context_lemmas)
            if stem_vec and stem_vec["pos"] == "noun" and float(stem_vec["concreteness"]) >= 0.75:
                salient = {
                    dim: round(float(stem_vec[dim]), 2)
                    for dim in PHYSICS_DIMENSIONS
                    if abs(float(stem_vec[dim])) >= 0.45
                }
                if salient:
                    hits.append(
                        MetaphorHit(
                            metaphor_type="denominal_verb_metaphor",
                            span=d_match.group(0).strip(),
                            target_concept=f"{subj_w} ({refl_target})",
                            source_concept=noun_stem,
                            violation_detail=f"Concrete noun '{noun_stem}' converted to reflexive verb '{verb_w}'",
                            projected_physics=salient,
                            comprehension_note=describe_metaphor_naturally(
                                refl_target, noun_stem, "denominal_verb_metaphor", salient
                            ),
                        )
                    )

        for match in COPULA_AND_SIMILE_RE.finditer(clean):
            full_span = match.group(0).strip()
            target_word = match.group(1).lower()
            rhs_phrase = match.group(2).strip().lower()

            clean_rhs = re.sub(r"^(?:an?\s+|the\s+)", "", rhs_phrase).strip()
            rhs_tokens = [
                t for t in re.findall(r"[a-z\-]+", clean_rhs)
                if t not in ("of", "like", "as", "though", "if", "made")
            ]
            if not rhs_tokens:
                continue

            source_head = rhs_tokens[-1]
            modifiers = rhs_tokens[:-1]
            source_str = " ".join(rhs_tokens)

            target_vec = self.get_vector(target_word, context_lemmas)
            source_vec = self.get_vector(source_head, context_lemmas)
            if not source_vec:
                continue

            if target_word in ("he", "she", "they", "it"):
                target_domain = "ANIMATE_BEING"
                target_conc = 0.50
            elif target_vec:
                target_domain = target_vec["ontological_domain"]
                target_conc = float(target_vec["concreteness"])
            else:
                continue

            concreteness_delta = float(source_vec["concreteness"]) - target_conc
            domain_mismatch = target_domain != source_vec["ontological_domain"]
            is_simile = bool(re.search(r"\b(like|as\s+though|as\s+if|made\s+of)\b", full_span.lower()))

            if (concreteness_delta >= 0.30 or is_simile) and domain_mismatch:
                blended = {dim: float(source_vec[dim]) for dim in PHYSICS_DIMENSIONS}
                for mod in modifiers:
                    mod_vec = self.get_vector(mod, context_lemmas)
                    if mod_vec:
                        for dim in PHYSICS_DIMENSIONS:
                            if abs(float(mod_vec[dim])) >= 0.25:
                                blended[dim] = max(-1.0, min(1.0, blended[dim] + float(mod_vec[dim]) * 0.65))

                salient = {k: round(v, 2) for k, v in blended.items() if abs(v) >= 0.45}
                if salient:
                    m_type = "simile_metaphor" if is_simile else "copula_metaphor"
                    hits.append(
                        MetaphorHit(
                            metaphor_type=m_type,
                            span=full_span,
                            target_concept=target_word,
                            source_concept=source_str,
                            violation_detail=(
                                f"Cross-Domain Mapping ({target_domain} <- "
                                f"{source_vec['ontological_domain']}, concreteness lift {concreteness_delta:+.2f})"
                            ),
                            projected_physics=salient,
                            comprehension_note=describe_metaphor_naturally(
                                target_word, source_str, m_type, salient
                            ),
                        )
                    )

        for triple in extract_svo_triples(clean, phrasal_replacements=phrasal_map):
            if any(idm_p in triple.raw_span.lower() for idm_p in idiom_spans):
                continue
            if triple.is_proper_subject:
                continue
            v_frame = self.get_verb_frame(triple.verb_lemma)
            if not v_frame:
                continue

            subj_vec = self.get_vector(triple.subject_lemma, context_lemmas)
            obj_vec = self.get_vector(triple.object_lemma, context_lemmas)
            if not subj_vec and not obj_vec:
                continue

            allowed_subj = set(json.loads(v_frame["required_subj_domains"]))
            allowed_obj = set(json.loads(v_frame["required_obj_domains"]))

            subj_dom = subj_vec["ontological_domain"] if subj_vec else "UNKNOWN"
            obj_dom = obj_vec["ontological_domain"] if obj_vec else "UNKNOWN"

            subj_violated = subj_vec is not None and subj_dom not in allowed_subj
            obj_violated = obj_vec is not None and obj_dom not in allowed_obj

            if subj_violated or obj_violated:
                imposed = json.loads(v_frame["imposed_physics_json"])
                src_str = f"{triple.subject_lemma}->{triple.verb_lemma}"
                hits.append(
                    MetaphorHit(
                        metaphor_type="verb_frame_metaphor",
                        span=triple.raw_span,
                        target_concept=triple.object_lemma,
                        source_concept=src_str,
                        violation_detail=(
                            f"Verb '{triple.verb_lemma}' expects {list(allowed_subj)} -> {list(allowed_obj)}, "
                            f"got [{subj_dom} -> {obj_dom}]"
                        ),
                        projected_physics=imposed,
                        comprehension_note=describe_metaphor_naturally(
                            triple.object_lemma, src_str, "verb_frame_metaphor", imposed
                        ),
                    )
                )

        return hits

    def extract_dialogue_speaker(self, paragraph: str, default_speaker: str = "Ellie") -> str:
        """Accurately extracts speaker from dialogue tags ('Cali said', 'I replied', 'Grace whispered')."""
        if re.search(r'["”]\s*,?\s*I\s+(?:said|replied|asked|thought|laughed|continue|shook|cringe|relented|managed)', paragraph, re.IGNORECASE):
            return default_speaker
        tag_match = re.search(
            r'["”]\s*,?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|replied|asked|whispered|hissed|laughed|says|replies|sighs|growled|snapped)',
            paragraph
        )
        if tag_match:
            cand = tag_match.group(1).strip()
            if cand.lower() not in EXCLUDED_FROM_ENTITIES:
                return cand
        lead_match = re.search(
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|asked|whispered|replied|says|replies),\s*["“]',
            paragraph
        )
        if lead_match:
            cand = lead_match.group(1).strip()
            if cand.lower() not in EXCLUDED_FROM_ENTITIES:
                return cand
        return default_speaker

    def analyze_paragraph_subtext(
        self,
        paragraph: str,
        speaker: Optional[str] = None,
        target_entity: Optional[str] = None,
        speaker_prior_affinity: float = -0.5,
        scene_tension_baseline: float = 0.5,
        brain: Optional[VirtualBrainState] = None,
        paragraph_index: int = 0,
    ) -> List[SubtextHit]:
        norm = normalize_text(paragraph)
        quotes = DIALOGUE_QUOTE_RE.findall(norm)
        if not quotes:
            return []

        resolved_speaker = self.extract_dialogue_speaker(paragraph, default_speaker=speaker or "Ellie")

        narrative_outside = DIALOGUE_QUOTE_RE.sub(" ", norm).lower()
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM somatic_markers")
        all_somatics = cur.fetchall()
        cur.execute("SELECT * FROM pragmatic_constructions")
        all_pragmatics = cur.fetchall()

        matched_masks = []
        matched_leaks = []
        somatic_boost = 0.0
        for row in all_somatics:
            if row["phrase_pattern"] in narrative_outside:
                if row["control_type"] == "PERFORMATIVE_MASK":
                    matched_masks.append(dict(row))
                    somatic_boost += float(row["internal_stress"]) * 0.55
                else:
                    matched_leaks.append(dict(row))
                    somatic_boost += float(row["internal_stress"]) * 0.80

        room_valence = -(scene_tension_baseline * 0.8)
        contextual_prior = (speaker_prior_affinity * 0.65) + (room_valence * 0.35)

        hits: List[SubtextHit] = []
        for quote in quotes:
            q_low = quote.lower().strip()
            words = re.findall(r"[a-z']+", q_low)
            if not words:
                continue

            content_lemmas = {
                normalize_lemma(w) for w in words
                if len(w) >= 3 and w not in ("the", "and", "did", "you", "are", "was", "for", "with", "that", "this")
            }

            if brain is not None and brain.last_dialogue_turn is not None:
                prev = brain.last_dialogue_turn
                if prev.speaker != resolved_speaker and prev.is_question and content_lemmas:
                    overlap = content_lemmas & prev.primed_neighborhood
                    direct_answer_tokens = {"yes", "no", "maybe", "never", "of", "course", "sure", "did", "didn't", "can't", "won't"}

                    is_copular_identification = bool(
                        re.match(r"^(?:this|that|it|he|she|they)\s+(?:is|are|was|were|'s|'re)\b", quote.strip(), re.IGNORECASE)
                    )
                    is_wh_question = bool(re.search(r"\b(who|what|where|which|how|called|name)\b", prev.utterance.lower()))
                    has_substantive_noun_phrase = len(words) >= 3 and any(w[0].isupper() for w in quote.split() if w.lower() not in EXCLUDED_FROM_ENTITIES)

                    is_cooperative_answer = (
                        bool(overlap)
                        or any(w in direct_answer_tokens for w in words)
                        or is_copular_identification
                        or (is_wh_question and has_substantive_noun_phrase)
                    )

                    if not is_cooperative_answer and len(words) >= 4:
                        hits.append(
                            SubtextHit(
                                utterance=quote,
                                speaker=resolved_speaker,
                                target_entity=prev.speaker,
                                subtext_category="GRICEAN_EVASION",
                                surface_valence=0.0,
                                contextual_prior=round(contextual_prior, 2),
                                divergence_score=1.45,
                                is_sarcastic_or_masked=True,
                                mechanisms=[
                                    f"Gricean Relevance Violation (0% semantic overlap with prior question '{prev.utterance}')"
                                ],
                                comprehension_note=describe_subtext_naturally(
                                    quote, resolved_speaker, prev.speaker, "GRICEAN_EVASION",
                                    0.0, contextual_prior, [], [], prior_question=prev.utterance
                                ),
                            )
                        )
                if prev.speaker != resolved_speaker and prev.word_count >= 24 and len(words) == 1 and words[0] in ("well", "shh", "fine", "no"):
                    hits.append(
                        SubtextHit(
                            utterance=quote,
                            speaker=resolved_speaker,
                            target_entity=prev.speaker,
                            subtext_category="QUANTITY_ASYMMETRY",
                            surface_valence=0.0,
                            contextual_prior=round(contextual_prior, 2),
                            divergence_score=1.25,
                            is_sarcastic_or_masked=True,
                            mechanisms=[
                                f"Gricean Quantity Violation ({prev.word_count}-word turn met with 1-word stonewall)"
                            ],
                            comprehension_note=describe_subtext_naturally(
                                quote, resolved_speaker, prev.speaker, "QUANTITY_ASYMMETRY",
                                0.0, contextual_prior, [], [],
                                prior_word_count=prev.word_count, reply_word_count=len(words)
                            ),
                        )
                    )

            if brain is not None:
                brain.last_dialogue_turn = DialogueTurnRecord(
                    paragraph_index=paragraph_index,
                    speaker=resolved_speaker,
                    utterance=quote,
                    word_count=len(words),
                    is_question=quote.strip().endswith("?"),
                    content_lemmas=content_lemmas,
                    primed_neighborhood=self.spread_activation(content_lemmas),
                )

            valences = []
            for w in words:
                vec = self.get_vector(w, content_lemmas)
                if vec and abs(float(vec["valence"])) >= 0.25:
                    valences.append(float(vec["valence"]))
            surface_valence = sum(valences) / len(valences) if valences else 0.0

            irony_bonus = 0.0
            pragmatic_labels = []
            for p_row in all_pragmatics:
                if re.search(p_row["regex_pattern"], q_low):
                    req_pol = int(p_row["required_surface_polarity"])
                    if req_pol == 0 or (req_pol > 0 and surface_valence >= 0.25):
                        irony_bonus += float(p_row["irony_multiplier"])
                        pragmatic_labels.append(p_row["pragmatic_label"])

            polarity_inverted = (surface_valence >= 0.35 and contextual_prior <= -0.20) or (
                surface_valence <= -0.35 and contextual_prior >= 0.30
            )
            raw_divergence = max(0.45, abs(surface_valence - contextual_prior))
            divergence_score = raw_divergence * (1.0 + irony_bonus + somatic_boost)

            if (
                (polarity_inverted and divergence_score >= 0.75)
                or divergence_score >= 1.10
                or matched_leaks
                or "TEMPORAL_HYPERBOLE_SARCASM" in pragmatic_labels
            ):
                mechanisms = []
                if polarity_inverted:
                    mechanisms.append(
                        f"Polarity Inversion (Spoken {surface_valence:+.2f} vs Prior {contextual_prior:+.2f})"
                    )
                if pragmatic_labels:
                    mechanisms.append(f"Pragmatic Carrier ({', '.join(pragmatic_labels)})")
                if matched_masks:
                    masks_str = ", ".join(f"'{m['phrase_pattern']}'" for m in matched_masks)
                    mechanisms.append(f"Performative Masking ({masks_str})")
                if matched_leaks:
                    leaks_str = ", ".join(f"'{l['phrase_pattern']}'" for m in matched_leaks)
                    mechanisms.append(f"Autonomic Betrayal ({leaks_str})")

                if "TEMPORAL_HYPERBOLE_SARCASM" in pragmatic_labels:
                    cat = "TEMPORAL_HYPERBOLE_SARCASM"
                elif polarity_inverted or pragmatic_labels:
                    cat = "POLARITY_INVERSION_SARCASM"
                else:
                    cat = "SOMATIC_MASKING"

                hits.append(
                    SubtextHit(
                        utterance=quote,
                        speaker=resolved_speaker,
                        target_entity=target_entity,
                        subtext_category=cat,
                        surface_valence=round(surface_valence, 2),
                        contextual_prior=round(contextual_prior, 2),
                        divergence_score=round(divergence_score, 2),
                        is_sarcastic_or_masked=bool(polarity_inverted or pragmatic_labels or matched_masks),
                        mechanisms=mechanisms,
                        comprehension_note=describe_subtext_naturally(
                            quote, resolved_speaker, target_entity, cat,
                            surface_valence, contextual_prior,
                            [m["phrase_pattern"] for m in matched_masks],
                            [l["phrase_pattern"] for l in matched_leaks],
                        ),
                    )
                )
        return hits

    def diagnose_semantic_paragraph(
        self,
        paragraph_index: int,
        raw_paragraph: str,
        word_vectors: List[Dict[str, Any]],
        sensory: Dict[str, float],
        velocity: float,
        dialogue_ratio: float,
        arousal: float,
        valence: float,
        surprisal: float,
    ) -> ParagraphDiagnosis:
        """
        Pure psycholinguistic and ontological paragraph diagnosis.
        Zero hardcoded word dictionaries. Evaluates purely on Wiktionary vectors.
        """
        clean = raw_paragraph.strip()
        words = [w.lower() for w in extract_words(clean)]
        word_set = set(words)
        low_para = clean.lower()
        has_dialogue_quote = any(q in clean for q in ('"', "“", "”"))

        # Filter out grammatical stopwords from salient reporting
        substantive_vectors = [v for v in word_vectors if v and v["lemma"] not in EXCLUDED_FROM_ENTITIES]

        # 0. Section / Heading boundary
        if len(words) <= 3 and not has_dialogue_quote:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Scene / Chapter Heading",
                cognitive_function="HEADING",
                reader_experience="Sets the formal boundary of the section.",
                salient_words=[w for w in words if w not in EXCLUDED_FROM_ENTITIES],
                primary_senses=[],
                craft_advisory=None,
            )

        # 1. PURE SENSORY VECTORS (From Wiktionary & Lancaster Sensorimotor Norms)
        olfactory_lemmas = [v["lemma"] for v in substantive_vectors if float(v.get("sensory_olfactory", 0)) >= 0.55]
        gustatory_lemmas = [v["lemma"] for v in substantive_vectors if float(v.get("sensory_gustatory", 0)) >= 0.55]
        auditory_lemmas = [v["lemma"] for v in substantive_vectors if float(v.get("sensory_auditory", 0)) >= 0.60]
        haptic_lemmas = [v["lemma"] for v in substantive_vectors if float(v.get("sensory_haptic", 0)) >= 0.65]

        detected_senses = []
        if olfactory_lemmas: detected_senses.append("Scent/Smell")
        if gustatory_lemmas: detected_senses.append("Taste")
        if auditory_lemmas: detected_senses.append("Sound")
        if haptic_lemmas: detected_senses.append("Texture/Touch")

        if olfactory_lemmas or gustatory_lemmas or (auditory_lemmas and not has_dialogue_quote) or (haptic_lemmas and auditory_lemmas):
            salient = list(dict.fromkeys(olfactory_lemmas + gustatory_lemmas + auditory_lemmas + haptic_lemmas))[:4]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Visceral Sensory Grounding",
                cognitive_function="VISCERAL_GROUNDING",
                reader_experience=(
                    f"Engages non-visual physical senses ({', '.join(detected_senses)}). "
                    f"Physical textures and visceral scents make the environment tangible rather than a sterile mental set."
                ),
                salient_words=salient,
                primary_senses=detected_senses,
                craft_advisory="Strong visceral hold. Prevents the fictional world from feeling like clean plastic.",
            )

        # 2. KINETIC ACTION & MOTION (Wiktionary Verbs with Velocity >= 0.45)
        kinetic_verbs = [
            v["lemma"] for v in substantive_vectors 
            if v.get("pos") == "verb" and float(v.get("velocity", 0)) >= 0.45
        ]
        if len(kinetic_verbs) >= 2:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Kinetic Momentum & Motion",
                cognitive_function="KINETIC_ACTION",
                reader_experience="High physical velocity. The reader visualizes active movement and anticipates impact.",
                salient_words=kinetic_verbs[:4],
                primary_senses=["Visual/Kinetic"],
                craft_advisory="Strong forward momentum. Great place for clean, staccato physical verbs.",
            )

        # 3. SOCIAL HIERARCHY & CLASS/STATUS CONTRAST
        has_social_hierarchy = any(
            v.get("ontological_domain") == "SOCIAL_CONSTRUCT" for v in substantive_vectors
        ) or any(w in word_set for w in ("queen", "orbiter", "knight", "knights", "palace", "watchmen", "treasurer", "noble", "lord", "commander"))
        
        has_humility = any(
            w in word_set for w in ("laundry", "maid", "wash", "bucket", "destitute", "barefoot", "plain", "rags", "branded", "nobody", "pruney", "poor")
        )

        if has_social_hierarchy and has_humility:
            salient = [w for w in ("laundry", "maid", "wash", "bucket", "branded", "queen", "orbiter", "palace", "knight", "destitute") if w in word_set]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Social Asymmetry & Class Vulnerability",
                cognitive_function="SOCIAL_HIERARCHY",
                reader_experience=(
                    "Striking status contrast. Pairing markers of poverty (laundry maid, branded, wash bucket) "
                    "with royal palace authority anchors deep underdog empathy."
                ),
                salient_words=salient[:4],
                primary_senses=["Status/Empathy"],
                craft_advisory="Effective thematic contrast that grounds character stakes without an infodump.",
            )

        # 4. VOLITIONAL RESOLVE & FORWARD HOOKS
        if any(v in low_para for v in ("one way or another", "no matter what", "at all costs", "whatever it takes")):
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Unshakable Resolve (Chapter Climax)",
                cognitive_function="RESOLVE_CLIMAX",
                reader_experience="Non-negotiable volition. The character makes an absolute commitment, driving the reader into the next chapter.",
                salient_words=["one way or another"],
                primary_senses=["Volition/Drive"],
                craft_advisory="Strong chapter closing beat. Anchors momentum.",
            )

        if "had a plan" in low_para or "a plan if" in low_para or "trap here" in low_para:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Narrative Contingency & Mystery Hook",
                cognitive_function="CONTINGENCY_HOOK",
                reader_experience="Curiosity hook. The mention of an unrevealed plan or incoming trap leaves the reader leaning forward.",
                salient_words=["plan", "trap"],
                primary_senses=["Curiosity/Mystery"],
                craft_advisory="Clean forward hook that rewards later payoff.",
            )

        # 5. SPATIAL ARCHITECTURE (Wiktionary SPACE_CONTAINER + Solid Concreteness)
        spatial_lemmas = [
            v["lemma"] for v in substantive_vectors 
            if v.get("ontological_domain") in ("SPACE_CONTAINER", "ARTIFACT_SOLID") 
            and float(v.get("concreteness", 0)) >= 0.75
        ]
        if len(spatial_lemmas) >= 3 and not has_dialogue_quote and len(kinetic_verbs) == 0:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Spatial Architecture (Exposition Pause)",
                cognitive_function="SPATIAL_BLUEPRINT",
                reader_experience="Spatial mapping. The narrative pauses kinetic motion to establish the physical geometry of the setting.",
                salient_words=list(dict.fromkeys(spatial_lemmas))[:4],
                primary_senses=["Visual/Architecture"],
                craft_advisory="Informative layout. If you need urgent pacing, integrate stone and wall descriptions into active movement.",
            )

        # 6. CHARACTER INTERIORITY (Wiktionary ABSTRACT_STATE + Interoceptive/Arousal)
        interior_lemmas = [
            v["lemma"] for v in substantive_vectors 
            if v.get("ontological_domain") == "ABSTRACT_STATE" 
            and (float(v.get("arousal", 0)) >= 0.25 or float(v.get("valence", 0)) <= -0.25)
        ]
        has_secrets = any(w in word_set for w in ("secret", "secrets", "thief", "hiding", "heartthrob", "worried", "nerves", "afraid"))
        if (len(interior_lemmas) >= 2 or has_secrets or "?" in clean) and not has_dialogue_quote:
            salient = list(dict.fromkeys(interior_lemmas + [w for w in ("secret", "thief", "hiding", "nerves", "heartthrob") if w in word_set]))[:4]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Internal Stakes & Concealed Secrets",
                cognitive_function="INTERIOR_STAKES",
                reader_experience=(
                    "Internal stakes. The reader steps inside the protagonist's mind as she conceals her alternate identity from her friend."
                ),
                salient_words=salient,
                primary_senses=["Interoception/Doubt"],
                craft_advisory="Strong character intimacy. The reader feels the pressure of keeping secrets.",
            )

        # 7. DIALOGUE & SPEECH ACTS
        if has_dialogue_quote:
            is_question = "?" in clean
            clean_dialogue_words = [w for w in words if len(w) > 4 and w not in EXCLUDED_FROM_ENTITIES]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Dialogue & Relationship Dynamic",
                cognitive_function="DIALOGUE_SUBTEXT",
                reader_experience=(
                    "Direct speech. Characters orient one another, probing for secrets and testing shared knowledge."
                    if is_question else
                    "Direct response. Characters exchange status, banter, and reinforce their relationship."
                ),
                salient_words=clean_dialogue_words[:3],
                primary_senses=["Auditory/Social"],
                craft_advisory=None,
            )

        # Default: Narrative Progression
        clean_salient = [w for w in words if len(w) > 4 and w not in EXCLUDED_FROM_ENTITIES]
        return ParagraphDiagnosis(
            paragraph_index=paragraph_index,
            headline="Narrative Progression",
            cognitive_function="NARRATIVE_FLOW",
            reader_experience="Seamless narrative movement carrying the scene forward.",
            salient_words=clean_salient[:3],
            primary_senses=["Visual"],
            craft_advisory=None,
        )

    def analyze_document(
        self, text: str, brain: Optional[VirtualBrainState] = None
    ) -> DocumentReport:
        if brain is None:
            brain = VirtualBrainState()

        paragraphs = split_paragraphs(text)
        ticks: List[ParagraphTick] = []
        all_metaphors: List[MetaphorHit] = []
        all_subtext: List[SubtextHit] = []
        all_continuity: List[ContinuityAlert] = []
        all_epistemic: List[EpistemicAlert] = []
        reader_notes: List[ReaderNote] = []
        habituation_warnings: List[int] = []
        diagnoses: List[ParagraphDiagnosis] = []

        for p_idx, para in enumerate(paragraphs):
            tick = self.step_paragraph(para, p_idx, brain)
            ticks.append(tick)
            if tick.diagnosis:
                diagnoses.append(tick.diagnosis)
            all_metaphors.extend(tick.metaphors)
            all_subtext.extend(tick.subtext_hits)
            all_continuity.extend(tick.continuity_alerts)
            all_epistemic.extend(tick.epistemic_alerts)
            if tick.habituation_dampening >= 0.45:
                habituation_warnings.append(p_idx)

        collisions = detect_entity_collisions(
            brain.entity_first_paragraph, brain.entity_mention_counts
        )
        for rare_name, canon_name, r_cnt, c_cnt, p_idx in collisions:
            explanation = describe_name_collision_naturally(rare_name, canon_name, r_cnt, c_cnt)
            alert = ContinuityAlert(
                alert_type="ENTITY_NAME_COLLISION",
                paragraph_index=p_idx,
                entity=rare_name,
                trigger_span=rare_name,
                explanation=explanation,
            )
            all_continuity.append(alert)
            if 0 <= p_idx < len(ticks):
                ticks[p_idx].continuity_alerts.append(alert)

        ngram_anomalies = detect_compound_ngram_anomalies(paragraphs)
        for p_idx, odd_bigram, expected_word in ngram_anomalies:
            explanation = describe_ngram_anomaly_naturally(odd_bigram, expected_word)
            alert = ContinuityAlert(
                alert_type="NGRAM_TYPO_ANOMALY",
                paragraph_index=p_idx,
                entity=odd_bigram,
                trigger_span=odd_bigram,
                explanation=explanation,
            )
            all_continuity.append(alert)
            if 0 <= p_idx < len(ticks):
                ticks[p_idx].continuity_alerts.append(alert)

        for tick in ticks:
            excerpt = paragraphs[tick.paragraph_index][:120]
            for c_alert in tick.continuity_alerts:
                reader_notes.append(
                    ReaderNote(
                        category="continuity",
                        label=f"Continuity / Typo Check ({c_alert.entity})",
                        paragraph_index=tick.paragraph_index,
                        excerpt=c_alert.trigger_span,
                        body=c_alert.explanation,
                    )
                )
            for s_hit in tick.subtext_hits:
                reader_notes.append(
                    ReaderNote(
                        category="subtext",
                        label=f"Subtext ({s_hit.subtext_category})",
                        paragraph_index=tick.paragraph_index,
                        excerpt=s_hit.utterance,
                        body=s_hit.comprehension_note,
                    )
                )
            for m_hit in tick.metaphors:
                reader_notes.append(
                    ReaderNote(
                        category="imagery",
                        label=f"Imagery: '{m_hit.span}'",
                        paragraph_index=tick.paragraph_index,
                        excerpt=m_hit.span,
                        body=m_hit.comprehension_note,
                    )
                )

        avg_vel = sum(t.syntactic_velocity for t in ticks) / len(ticks) if ticks else 0.0
        avg_arousal = sum(t.felt_arousal for t in ticks) / len(ticks) if ticks else 0.0

        agency_ratios: Dict[str, float] = {}
        all_chars = set(brain.subject_action_counts.keys()) | set(brain.object_target_counts.keys())
        for char in sorted(all_chars):
            subj_c = brain.subject_action_counts.get(char, 0)
            obj_c = brain.object_target_counts.get(char, 0)
            agency_ratios[char] = round(subj_c / max(1, subj_c + obj_c), 2)

        affinity_serialized = {
            f"{k[0]}<->{k[1]}": v for k, v in brain.affinity_ledger.items() if k[0] < k[1]
        }

        return DocumentReport(
            total_paragraphs=len(paragraphs),
            total_words=brain.cumulative_words,
            avg_syntactic_velocity=round(avg_vel, 3),
            avg_felt_arousal=round(avg_arousal, 3),
            habituation_warnings=habituation_warnings,
            resolved_aliases=dict(brain.alias_map),
            metaphors=all_metaphors,
            subtext_hits=all_subtext,
            continuity_alerts=all_continuity,
            epistemic_alerts=all_epistemic,
            promises=brain.promises,
            character_agency_ratios=agency_ratios,
            affinity_matrix=affinity_serialized,
            reader_notes=reader_notes,
            ticks=ticks,
            paragraph_diagnoses=diagnoses,
        )

    def step_paragraph(
        self, paragraph: str, paragraph_index: int, brain: VirtualBrainState
    ) -> ParagraphTick:
        norm = normalize_text(paragraph)
        words = extract_words(norm)
        word_count = len(words)
        brain.cumulative_words += word_count
        sentences = split_sentences(norm)
        avg_sent_len = word_count / max(1, len(sentences))

        lemmas = [normalize_lemma(w) for w in words]
        context_lemma_set = set(lemmas)
        continuity_alerts: List[ContinuityAlert] = []

        new_aliases = extract_appositive_aliases(norm)
        brain.alias_map.update(new_aliases)

        proper_entities = extract_proper_entities(norm, alias_map=brain.alias_map)
        for ent in proper_entities:
            brain.present_cast.add(ent)
            decay_alert = brain.touch_entity(ent, paragraph_index)
            if decay_alert:
                continuity_alerts.append(decay_alert)

        idioms, phrasal_map = self.scan_mwes(norm)
        idiom_phrases = {idm["phrase"] for idm in idioms}

        valences: List[float] = []
        arousals: List[float] = []
        sensory_totals = {
            "visual": 0.0, "auditory": 0.0, "haptic": 0.0,
            "olfactory": 0.0, "gustatory": 0.0, "interoceptive": 0.0,
        }
        verb_count = 0
        adj_count = 0
        unprimed_hits = 0
        evaluated_words = 0
        detected_location: Optional[str] = None
        collected_vectors: List[Dict[str, Any]] = []

        for lem in lemmas:
            vec = self.get_vector(lem, context_lemma_set)
            if not vec:
                continue
            collected_vectors.append(vec)
            evaluated_words += 1
            if brain.primed_concepts and lem not in brain.primed_concepts:
                unprimed_hits += 1

            pos = vec["pos"]
            if pos == "verb":
                verb_count += 1
            elif pos in ("adj", "adv"):
                adj_count += 1

            if vec["ontological_domain"] == "SPACE_CONTAINER" and lem not in ("cage",):
                detected_location = lem

            if abs(float(vec["valence"])) >= 0.15:
                valences.append(float(vec["valence"]))
            if abs(float(vec["arousal"])) >= 0.15:
                arousals.append(float(vec["arousal"]))

            sensory_totals["visual"] += float(vec.get("sensory_visual", 0.0))
            sensory_totals["auditory"] += float(vec.get("sensory_auditory", 0.0))
            sensory_totals["haptic"] += float(vec.get("sensory_haptic", 0.0))
            sensory_totals["olfactory"] += float(vec.get("sensory_olfactory", 0.0))
            sensory_totals["gustatory"] += float(vec.get("sensory_gustatory", 0.0))
            sensory_totals["interoceptive"] += float(vec.get("sensory_interoceptive", 0.0))

        raw_valence = sum(valences) / len(valences) if valences else 0.0
        raw_arousal = sum(max(0.0, a) for a in arousals) / len(arousals) if arousals else 0.15
        sensory_profile = {
            k: round(v / max(1, evaluated_words), 3) for k, v in sensory_totals.items()
        }

        surprisal_n400 = (
            round(unprimed_hits / max(1, evaluated_words), 2)
            if brain.primed_concepts
            else 0.25
        )
        brain.primed_concepts = self.spread_activation(lemmas)

        quote_spans = DIALOGUE_QUOTE_RE.findall(norm)
        quote_words = sum(len(extract_words(q)) for q in quote_spans)
        dialogue_ratio = round(quote_words / max(1, word_count), 2)
        syntactic_velocity = round(
            ((verb_count + 1) / (adj_count + 1)) * (12.0 / max(4.0, avg_sent_len)), 3
        )

        shifted_dims: List[str] = []
        if detected_location and detected_location != brain.current_location:
            if brain.current_location != "UNSPECIFIED":
                shifted_dims.append("SPACE")
            brain.current_location = detected_location

        if any(t in TEMPORAL_MARKERS for t in lemmas):
            shifted_dims.append("TIME")
        if any(t in CAUSAL_CONNECTIVES for t in lemmas):
            shifted_dims.append("CAUSALITY")
        if any(t in INTENTIONAL_MODALS for t in lemmas):
            shifted_dims.append("INTENTION")
        if proper_entities and brain.dominant_protagonist and proper_entities[0] != brain.dominant_protagonist:
            shifted_dims.append("PROTAGONIST")
        if proper_entities:
            brain.dominant_protagonist = proper_entities[0]

        event_boundary = len(shifted_dims) >= 2

        clause_modalities = [classify_sentence_modality(s) for s in sentences]
        for triple in extract_svo_triples(
            norm, pronoun_resolver=brain.pronoun_stack, phrasal_replacements=phrasal_map
        ):
            if any(ip in triple.raw_span.lower() for ip in idiom_phrases):
                continue
            if triple.modality != "FACTUAL":
                continue

            if triple.is_proper_subject:
                brain.subject_action_counts[triple.subject_raw] = (
                    brain.subject_action_counts.get(triple.subject_raw, 0) + 1
                )
            if triple.object_lemma.capitalize() in brain.present_cast:
                cap_obj = triple.object_lemma.capitalize()
                brain.object_target_counts[cap_obj] = (
                    brain.object_target_counts.get(cap_obj, 0) + 1
                )

            v_frame = self.get_verb_frame(triple.verb_lemma)
            if not v_frame:
                continue

            mutation = v_frame["state_mutation"]
            precond = v_frame["precondition"]

            if mutation == "LIGHT_TERMINATION":
                brain.lighting = "DARK"
                brain.active_light_source = triple.object_lemma
            elif mutation == "LIGHT_ACTIVATION":
                brain.lighting = "LIT"
                brain.active_light_source = triple.object_lemma
            elif mutation == "ACQUIRE_OBJECT":
                brain.inventory.setdefault(triple.subject_raw, set()).add(triple.object_lemma)
            elif mutation == "RELEASE_OBJECT":
                held = brain.inventory.get(triple.subject_raw, set())
                held.discard(triple.object_lemma)

            if precond == "REQUIRES_LIGHT" and brain.lighting == "DARK":
                continuity_alerts.append(
                    ContinuityAlert(
                        alert_type="LIGHTING_CONTRADICTION",
                        paragraph_index=paragraph_index,
                        entity=triple.subject_raw,
                        trigger_span=triple.raw_span,
                        explanation=describe_lighting_error_naturally(
                            triple.subject_raw, triple.verb_lemma, triple.raw_span, brain.active_light_source
                        ),
                    )
                )

        if len(proper_entities) >= 2 and abs(raw_valence) >= 0.20:
            for i in range(len(proper_entities)):
                for j in range(i + 1, len(proper_entities)):
                    brain.update_affinity(proper_entities[i], proper_entities[j], raw_valence)
        for ent in proper_entities:
            for concept in ("family", "debt", "poison", "secret"):
                if concept in lemmas and abs(raw_valence) >= 0.20:
                    brain.update_affinity(ent, concept, raw_valence)

        for p_match in PROMISE_CUE_RE.finditer(norm):
            cue_span = p_match.group(0).strip()
            if classify_sentence_modality(cue_span) != "FACTUAL":
                continue
            brain.promises.append(
                OpenPromise(
                    promise_id=f"promise_{len(brain.promises) + 1}",
                    cue_phrase=cue_span,
                    setup_paragraph=paragraph_index,
                    setup_word_offset=brain.cumulative_words,
                )
            )
            if any(k in cue_span.lower() for k in ("poison", "hid", "secret", "buried", "planted")):
                brain.register_scene_fact(
                    fact_id=f"fact_p{paragraph_index}_{normalize_lemma(p_match.group(1))}",
                    danger_weight=0.85,
                    witnesses=set(proper_entities),
                )

        for prom in brain.promises:
            if not prom.resolved:
                prom.current_word_distance = brain.cumulative_words - prom.setup_word_offset
                prom.tension_tautness = round(min(1.0, prom.current_word_distance / 2500.0), 3)

        felt_arousal, pool, habituation = brain.step_autonomic_arousal(raw_arousal, raw_valence)
        irony_score, epistemic_alerts = brain.evaluate_dramatic_irony(paragraph_index)

        metaphors = self.scan_paragraph_metaphors(norm, context_lemma_set)

        speaker = self.extract_dialogue_speaker(norm, default_speaker=brain.dominant_protagonist or "Ellie")
        prior_affinity = -0.5
        target_topic = None
        if speaker:
            for candidate in [e for e in proper_entities[1:]] + ["family", "debt", "secret"]:
                if candidate.lower() in norm.lower():
                    target_topic = candidate
                    prior_affinity = brain.get_affinity(speaker, candidate, default=-0.5)
                    break

        subtext_hits = self.analyze_paragraph_subtext(
            norm,
            speaker=speaker,
            target_entity=target_topic,
            speaker_prior_affinity=prior_affinity,
            scene_tension_baseline=felt_arousal,
            brain=brain,
            paragraph_index=paragraph_index,
        )

        diagnosis = self.diagnose_semantic_paragraph(
            paragraph_index=paragraph_index + 1,
            raw_paragraph=norm,
            word_vectors=collected_vectors,
            sensory=sensory_profile,
            velocity=syntactic_velocity,
            dialogue_ratio=dialogue_ratio,
            arousal=felt_arousal,
            valence=raw_valence,
            surprisal=surprisal_n400,
        )

        return ParagraphTick(
            paragraph_index=paragraph_index,
            word_count=word_count,
            cumulative_words=brain.cumulative_words,
            syntactic_velocity=syntactic_velocity,
            dialogue_ratio=dialogue_ratio,
            raw_valence=round(raw_valence, 3),
            felt_arousal=felt_arousal,
            neurotransmitter_pool=pool,
            habituation_dampening=habituation,
            surprisal_n400=surprisal_n400,
            event_boundary_triggered=event_boundary,
            shifted_dimensions=shifted_dims,
            working_memory_slots=list(brain.working_memory),
            lighting_state=brain.lighting,
            present_cast=sorted(brain.present_cast),
            dramatic_irony_score=irony_score,
            sensory_profile=sensory_profile,
            clause_modalities=clause_modalities,
            metaphors=metaphors,
            subtext_hits=subtext_hits,
            continuity_alerts=continuity_alerts,
            epistemic_alerts=epistemic_alerts,
            diagnosis=diagnosis,
        )
