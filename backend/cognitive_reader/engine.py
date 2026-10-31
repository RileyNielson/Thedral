import json
import re
import sqlite3
from collections import Counter
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
                    direct_answer_tokens = {"yes", "no", "maybe", "never", "of", "course", "sure", "did", "didn't", "can't", "won't"}

                    is_copular_identification = bool(
                        re.match(r"^(?:this|that|it|he|she|they)\s+(?:is|are|was|were|'s|'re)\b", quote.strip(), re.IGNORECASE)
                    )
                    is_wh_question = bool(re.search(r"\b(who|what|where|which|how|called|name)\b", prev.utterance.lower()))
                    has_substantive_noun_phrase = len(words) >= 3 and any(w[0].isupper() for w in quote.split())

                    is_cooperative_answer = (
                        bool(overlap)
                        or any(w in direct_answer_tokens for w in words)
                        or is_copular_identification
                        or (is_wh_question and has_substantive_noun_phrase)
                    )

                    if not is_cooperative_answer:
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
