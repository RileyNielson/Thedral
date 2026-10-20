import math
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from cognitive_reader.models import ContinuityAlert, EpistemicAlert, OpenPromise


@dataclass
class MemoryTrace:
    entity_name: str
    activation: float = 1.0
    decay_rate: float = 0.0025
    mentions: int = 1
    last_word_offset: int = 0

    def current_activation(self, current_word_offset: int) -> float:
        delta_t = max(0, current_word_offset - self.last_word_offset)
        return self.activation * math.exp(-self.decay_rate * delta_t)

    def rehearse(self, current_word_offset: int) -> None:
        self.activation = 1.0
        self.mentions += 1
        self.decay_rate = max(0.0003, self.decay_rate * 0.78)
        self.last_word_offset = current_word_offset


@dataclass
class DialogueTurnRecord:
    paragraph_index: int
    speaker: Optional[str]
    utterance: str
    word_count: int
    is_question: bool
    content_lemmas: Set[str]
    primed_neighborhood: Set[str]


class VirtualBrainState:
    WORKING_MEMORY_CAPACITY = 7
    RECALL_FAILURE_THRESHOLD = 0.18

    def __init__(self) -> None:
        self.cumulative_words: int = 0
        self.hippocampus: Dict[str, MemoryTrace] = {}
        self.working_memory: List[str] = []

        # Entity Alias & Collision Tracking
        self.alias_map: Dict[str, str] = {}
        self.entity_mention_counts: Counter = Counter()
        self.entity_first_paragraph: Dict[str, int] = {}

        # Autonomic Nervous System
        self.neurotransmitter_pool: float = 1.0
        self.felt_arousal: float = 0.15

        # 5D Situation Model
        self.current_location: str = "UNSPECIFIED"
        self.lighting: str = "LIT"
        self.active_light_source: Optional[str] = None
        self.present_cast: Set[str] = set()
        self.inventory: Dict[str, Set[str]] = {}
        self.dominant_protagonist: Optional[str] = None

        # Pronoun Coreference Stack & Gricean Turn Memory
        self.pronoun_stack: Dict[str, str] = {}
        self.last_dialogue_turn: Optional[DialogueTurnRecord] = None

        # Theory of Mind
        self.reader_knowledge: Set[str] = set()
        self.character_knowledge: Dict[str, Set[str]] = {}
        self.fact_danger_weights: Dict[str, float] = {}

        # Relational Affinity & Agency
        self.affinity_ledger: Dict[Tuple[str, str], float] = {}
        self.subject_action_counts: Dict[str, int] = {}
        self.object_target_counts: Dict[str, int] = {}

        # Chekhov Spans & Predictive Priming
        self.promises: List[OpenPromise] = []
        self.primed_concepts: Set[str] = set()

    def register_entity_in_stack(self, entity: str) -> None:
        self.pronoun_stack["LAST"] = entity
        if entity.endswith(("a", "e", "i")) or any(
            f in entity for f in ("Mara", "Elena", "Lindsey", "Sarah", "Selica", "Verona", "Dame")
        ):
            self.pronoun_stack["SHE"] = entity
        else:
            self.pronoun_stack["HE"] = entity

    def touch_entity(self, entity: str, paragraph_index: int) -> Optional[ContinuityAlert]:
        key = self.alias_map.get(entity.lower(), entity.strip())
        if not key:
            return None
        self.entity_mention_counts[key] += 1
        if key not in self.entity_first_paragraph:
            self.entity_first_paragraph[key] = paragraph_index

        self.register_entity_in_stack(key)
        alert = None
        if key in self.hippocampus:
            trace = self.hippocampus[key]
            act = trace.current_activation(self.cumulative_words)
            if act < self.RECALL_FAILURE_THRESHOLD and trace.mentions == 1:
                alert = ContinuityAlert(
                    alert_type="MEMORY_DECAY_FAILURE",
                    paragraph_index=paragraph_index,
                    entity=key,
                    trigger_span=key,
                    explanation=(
                        f"Cognitive Recall Failure: '{key}' re-entered after decaying to {act:.2f} "
                        f"(below {self.RECALL_FAILURE_THRESHOLD} threshold) with only 1 prior mention."
                    ),
                )
            trace.rehearse(self.cumulative_words)
        else:
            self.hippocampus[key] = MemoryTrace(
                entity_name=key,
                activation=1.0,
                last_word_offset=self.cumulative_words,
            )

        scored = [
            (t.current_activation(self.cumulative_words), name)
            for name, t in self.hippocampus.items()
        ]
        scored.sort(reverse=True)
        self.working_memory = [name for _, name in scored[: self.WORKING_MEMORY_CAPACITY]]
        return alert

    def step_autonomic_arousal(
        self, raw_stimulus_intensity: float, raw_valence: float
    ) -> Tuple[float, float, float]:
        if raw_stimulus_intensity >= 0.48:
            drain = (raw_stimulus_intensity - 0.30) * 0.38
            effective_multiplier = self.neurotransmitter_pool
            self.felt_arousal = min(1.0, raw_stimulus_intensity * effective_multiplier)
            habituation_dampening = max(0.0, 1.0 - effective_multiplier)
            self.neurotransmitter_pool = max(0.12, self.neurotransmitter_pool - drain)
        else:
            recovery_rate = 0.25 if raw_valence >= 0.15 else 0.14
            self.neurotransmitter_pool = min(1.0, self.neurotransmitter_pool + recovery_rate)
            self.felt_arousal = max(0.05, (self.felt_arousal * 0.5) + (raw_stimulus_intensity * 0.5))
            habituation_dampening = 0.0

        return (
            round(self.felt_arousal, 3),
            round(self.neurotransmitter_pool, 3),
            round(habituation_dampening, 3),
        )

    def register_scene_fact(
        self, fact_id: str, danger_weight: float = 0.7, witnesses: Optional[Set[str]] = None
    ) -> None:
        self.reader_knowledge.add(fact_id)
        self.fact_danger_weights[fact_id] = danger_weight
        active_witnesses = witnesses if witnesses is not None else self.present_cast
        for char in active_witnesses:
            self.character_knowledge.setdefault(char, set()).add(fact_id)

    def evaluate_dramatic_irony(
        self, paragraph_index: int
    ) -> Tuple[float, List[EpistemicAlert]]:
        if not self.present_cast or not self.reader_knowledge:
            return 0.0, []
        alerts: List[EpistemicAlert] = []
        max_irony = 0.0
        for char in sorted(self.present_cast):
            k_char = self.character_knowledge.get(char, set())
            unknown_facts = self.reader_knowledge - k_char
            if unknown_facts:
                score = sum(self.fact_danger_weights.get(f, 0.5) for f in unknown_facts)
                max_irony = max(max_irony, score)
                for f in sorted(unknown_facts):
                    if self.fact_danger_weights.get(f, 0.5) >= 0.6:
                        alerts.append(
                            EpistemicAlert(
                                alert_type="DRAMATIC_IRONY_SPIKE",
                                paragraph_index=paragraph_index,
                                character=char,
                                fact_id=f,
                                irony_delta=len(unknown_facts),
                                explanation=(
                                    f"Dramatic Irony: '{char}' is present in scene but unaware of "
                                    f"established high-stakes fact '{f}'."
                                ),
                            )
                        )
        return round(max_irony, 2), alerts

    def update_affinity(self, entity_a: str, entity_b: str, valence_delta: float) -> None:
        if entity_a == entity_b:
            return
        pair = (entity_a.lower(), entity_b.lower())
        rev_pair = (entity_b.lower(), entity_a.lower())
        current = self.affinity_ledger.get(pair, 0.0)
        updated = max(-1.0, min(1.0, (current * 0.65) + (valence_delta * 0.55)))
        self.affinity_ledger[pair] = round(updated, 3)
        self.affinity_ledger[rev_pair] = round(updated, 3)

    def get_affinity(self, entity_a: str, entity_b: str, default: float = 0.0) -> float:
        return self.affinity_ledger.get((entity_a.lower(), entity_b.lower()), default)