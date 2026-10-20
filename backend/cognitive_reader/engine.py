import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from cognitive_reader.compiler import DEFAULT_DB_PATH, build_cognitive_database
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
    ParagraphTick,
    ReaderNote,
    SubtextHit,
)
from cognitive_reader.parser import (
    CAUSAL_CONNECTIVES,
    COPULA_AND_SIMILE_RE,
    DENOMINAL_VERB_RE,
    DIALOGUE_QUOTE_RE,
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
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            build_cognitive_database(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def get_vector(
        self, word: str, context_lemmas: Optional[Set[str]] = None
    ) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        raw = word.lower().strip(".,;!?\"'()")
        candidates = [raw]
        norm = normalize_lemma(raw)
        if norm != raw:
            candidates.append(norm)

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

    # -------------------------------------------------------------------------
    # Metaphor, Simile, Denominal Verb, & Idiom Scanner
    # -------------------------------------------------------------------------
    def scan_paragraph_metaphors(
        self, paragraph: str, context_lemmas: Optional[Set[str]] = None
    ) -> List[MetaphorHit]:
        hits: List[MetaphorHit] = []
        clean = normalize_text(paragraph).strip()
        if not clean:
            return hits

        if context_lemmas is None:
            context_lemmas = {normalize_lemma(w) for w in extract_words(clean)}

        # A. Multi-Word Idioms
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

        # B. Denominal / Zero-Shot Noun-to-Verb Metaphors ("He 'steeled' himself")
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

        # C. Copula & Simile Mapping ("Grief is a rusted anchor", "looked like an upside-down sunset")
        for match in COPULA_AND_SIMILE_RE.finditer(clean):
            full_span = match.group(0).strip()
            target_word = match.group(1).lower()
            rhs_phrase = match.group(2).strip().lower()
            rhs_tokens = [
                t for t in re.findall(r"[a-z\-]+", rhs_phrase)
                if t not in ("a", "an", "the", "of", "like", "as", "though", "if", "made")
            ]
            if not rhs_tokens:
                continue

            source_head = rhs_tokens[-1]
            modifiers = rhs_tokens[:-1]

            target_vec = self.get_vector(target_word, context_lemmas)
            source_vec = self.get_vector(source_head, context_lemmas)
            if not source_vec:
                continue

            # Allow pronouns ('he', 'she', 'his') as simile targets ("He looked like an upside-down sunset")
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
                    source_str = " ".join(rhs_tokens)
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

        # D. Verb Selectional Preference Violations ("The silence strangled the room")
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

    # -------------------------------------------------------------------------
    # Subtext, Sarcasm, & Gricean Turn-Pair Evasion Engine
    # -------------------------------------------------------------------------
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
                if prev.is_question and content_lemmas:
                    overlap = content_lemmas & prev.primed_neighborhood
                    direct_answer_words = {"yes", "no", "maybe", "never", "of", "course", "sure", "did", "didn't"}
                    if not overlap and not any(w in direct_answer_words for w in words):
                        hits.append(
                            SubtextHit(
                                utterance=quote,
                                speaker=speaker,
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
                                    quote, speaker, prev.speaker, "GRICEAN_EVASION",
                                    0.0, contextual_prior, [], [], prior_question=prev.utterance
                                ),
                            )
                        )
                if prev.word_count >= 22 and len(words) <= 3:
                    hits.append(
                        SubtextHit(
                            utterance=quote,
                            speaker=speaker,
                            target_entity=prev.speaker,
                            subtext_category="QUANTITY_ASYMMETRY",
                            surface_valence=0.0,
                            contextual_prior=round(contextual_prior, 2),
                            divergence_score=1.25,
                            is_sarcastic_or_masked=True,
                            mechanisms=[
                                f"Gricean Quantity Violation ({prev.word_count}-word turn met with {len(words)}-word stonewall)"
                            ],
                            comprehension_note=describe_subtext_naturally(
                                quote, speaker, prev.speaker, "QUANTITY_ASYMMETRY",
                                0.0, contextual_prior, [], [],
                                prior_word_count=prev.word_count, reply_word_count=len(words)
                            ),
                        )
                    )

            if brain is not None:
                brain.last_dialogue_turn = DialogueTurnRecord(
                    paragraph_index=paragraph_index,
                    speaker=speaker,
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
                        speaker=speaker,
                        target_entity=target_entity,
                        subtext_category=cat,
                        surface_valence=round(surface_valence, 2),
                        contextual_prior=round(contextual_prior, 2),
                        divergence_score=round(divergence_score, 2),
                        is_sarcastic_or_masked=bool(polarity_inverted or pragmatic_labels or matched_masks),
                        mechanisms=mechanisms,
                        comprehension_note=describe_subtext_naturally(
                            quote, speaker, target_entity, cat,
                            surface_valence, contextual_prior,
                            [m["phrase_pattern"] for m in matched_masks],
                            [l["phrase_pattern"] for l in matched_leaks],
                        ),
                    )
                )
        return hits

    # -------------------------------------------------------------------------
    # Single-Pass Sequential Simulation + Post-Pass Static Analysis
    # -------------------------------------------------------------------------
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

        for p_idx, para in enumerate(paragraphs):
            tick = self.step_paragraph(para, p_idx, brain)
            ticks.append(tick)
            all_metaphors.extend(tick.metaphors)
            all_subtext.extend(tick.subtext_hits)
            all_continuity.extend(tick.continuity_alerts)
            all_epistemic.extend(tick.epistemic_alerts)
            if tick.habituation_dampening >= 0.45:
                habituation_warnings.append(p_idx)

        # Post-Pass 1: Levenshtein / Phonetic Entity Collision Detection ('Sir Grimm' vs 'Sir Grinn')
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

        # Post-Pass 2: Compound N-Gram Split / Typo Detection ('knight kings' vs 'knightlings')
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

        # Compile Plain-English Reader Notes
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

        # 1. Learn Bidirectional Appositive Aliases ("Dame Verona, the short knight in purple armor,")
        new_aliases = extract_appositive_aliases(norm)
        brain.alias_map.update(new_aliases)

        # 2. Extract Proper Entities & Update Working Memory
        proper_entities = extract_proper_entities(norm, alias_map=brain.alias_map)
        for ent in proper_entities:
            brain.present_cast.add(ent)
            decay_alert = brain.touch_entity(ent, paragraph_index)
            if decay_alert:
                continuity_alerts.append(decay_alert)

        # 3. Scan Multi-Word Expressions
        idioms, phrasal_map = self.scan_mwes(norm)
        idiom_phrases = {idm["phrase"] for idm in idioms}

        # 4. Lexical Valence, Arousal, 6-Sense Profile, & Surprisal
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

        for lem in lemmas:
            vec = self.get_vector(lem, context_lemma_set)
            if not vec:
                continue
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

        # 5. Syntactic Velocity & Dialogue Ratio
        quote_spans = DIALOGUE_QUOTE_RE.findall(norm)
        quote_words = sum(len(extract_words(q)) for q in quote_spans)
        dialogue_ratio = round(quote_words / max(1, word_count), 2)
        syntactic_velocity = round(
            ((verb_count + 1) / (adj_count + 1)) * (12.0 / max(4.0, avg_sent_len)), 3
        )

        # 6. Event Segmentation Theory (5D Situation Boundary)
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

        # 7. Physical Situation Model & Modality-Gated SVO State Machine
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

        # 8. Relational Affinity Ledger
        if len(proper_entities) >= 2 and abs(raw_valence) >= 0.20:
            for i in range(len(proper_entities)):
                for j in range(i + 1, len(proper_entities)):
                    brain.update_affinity(proper_entities[i], proper_entities[j], raw_valence)
        for ent in proper_entities:
            for concept in ("family", "debt", "poison", "secret"):
                if concept in lemmas and abs(raw_valence) >= 0.20:
                    brain.update_affinity(ent, concept, raw_valence)

        # 9. Chekhov Promise Setup
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

        # 10. Homeostatic Arousal & Dramatic Irony
        felt_arousal, pool, habituation = brain.step_autonomic_arousal(raw_arousal, raw_valence)
        irony_score, epistemic_alerts = brain.evaluate_dramatic_irony(paragraph_index)

        # 11. Metaphor & Subtext Scans
        metaphors = self.scan_paragraph_metaphors(norm, context_lemma_set)

        speaker = proper_entities[0] if proper_entities else brain.dominant_protagonist
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
        )