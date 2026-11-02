from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MetaphorHit:
    metaphor_type: str
    span: str
    target_concept: str
    source_concept: str
    violation_detail: str
    projected_physics: Dict[str, float]
    comprehension_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SubtextHit:
    utterance: str
    speaker: Optional[str]
    target_entity: Optional[str]
    subtext_category: str
    surface_valence: float
    contextual_prior: float
    divergence_score: float
    is_sarcastic_or_masked: bool
    mechanisms: List[str]
    comprehension_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContinuityAlert:
    alert_type: str
    paragraph_index: int
    entity: str
    trigger_span: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EpistemicAlert:
    alert_type: str
    paragraph_index: int
    character: str
    fact_id: str
    irony_delta: int
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpenPromise:
    promise_id: str
    cue_phrase: str
    setup_paragraph: int
    setup_word_offset: int
    resolved: bool = False
    resolved_paragraph: Optional[int] = None
    current_word_distance: int = 0
    tension_tautness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReaderNote:
    category: str
    label: str
    paragraph_index: int
    excerpt: str
    body: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreadImpact:
    action_type: str  # 'SEED' | 'ESCALATE' | 'PAYOFF' | 'MAINTAIN'
    thread_name: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StorySoFar:
    location: str
    characters_present: List[str]
    active_threads: List[str]
    active_tension_level: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParagraphDiagnosis:
    paragraph_index: int
    headline: str
    cognitive_function: str
    reader_experience: str
    salient_words: List[str]
    primary_senses: List[str]
    craft_advisory: Optional[str] = None
    story_so_far: Optional[StorySoFar] = None
    thread_impact: Optional[ThreadImpact] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.story_so_far:
            res["story_so_far"] = self.story_so_far.to_dict()
        if self.thread_impact:
            res["thread_impact"] = self.thread_impact.to_dict()
        return res


@dataclass
class ParagraphTick:
    paragraph_index: int
    word_count: int
    cumulative_words: int
    syntactic_velocity: float
    dialogue_ratio: float
    raw_valence: float
    felt_arousal: float
    neurotransmitter_pool: float
    habituation_dampening: float
    surprisal_n400: float
    event_boundary_triggered: bool
    shifted_dimensions: List[str]
    working_memory_slots: List[str]
    lighting_state: str
    present_cast: List[str]
    dramatic_irony_score: float
    sensory_profile: Dict[str, float] = field(default_factory=dict)
    clause_modalities: List[str] = field(default_factory=list)
    metaphors: List[MetaphorHit] = field(default_factory=list)
    subtext_hits: List[SubtextHit] = field(default_factory=list)
    continuity_alerts: List[ContinuityAlert] = field(default_factory=list)
    epistemic_alerts: List[EpistemicAlert] = field(default_factory=list)
    diagnosis: Optional[ParagraphDiagnosis] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DocumentReport:
    total_paragraphs: int
    total_words: int
    avg_syntactic_velocity: float
    avg_felt_arousal: float
    habituation_warnings: List[int]
    resolved_aliases: Dict[str, str]
    metaphors: List[MetaphorHit]
    subtext_hits: List[SubtextHit]
    continuity_alerts: List[ContinuityAlert]
    epistemic_alerts: List[EpistemicAlert]
    promises: List[OpenPromise]
    character_agency_ratios: Dict[str, float]
    affinity_matrix: Dict[str, float]
    reader_notes: List[ReaderNote]
    ticks: List[ParagraphTick]
    paragraph_diagnoses: List[ParagraphDiagnosis] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
