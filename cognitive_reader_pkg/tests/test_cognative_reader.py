from pathlib import Path
from cognitive_reader import CognitiveEngine, VirtualBrainState


def get_test_engine(tmp_path: Path) -> CognitiveEngine:
    return CognitiveEngine(db_path=tmp_path / "test_cognitive_v3.db")


def test_wiktionary_primitive_derived_metaphor(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    hits = engine.scan_paragraph_metaphors("Melancholy is a corroded anvil.")
    assert len(hits) == 1
    hit = hits[0]
    assert hit.target_concept == "melancholy"
    assert hit.source_concept == "corroded anvil"
    assert hit.projected_physics["mass_weight"] >= 0.85
    assert "heavy and crushing" in hit.comprehension_note


def test_denominal_verb_metaphor_steeled_himself(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    # From Chapter 2 of Lance and the Dragon: "He 'steeled' himself"
    hits = engine.scan_paragraph_metaphors("He 'steeled' himself by pretending his skin was made of metal.")
    denom_hits = [h for h in hits if h.metaphor_type == "denominal_verb_metaphor"]
    assert len(denom_hits) == 1
    assert denom_hits[0].source_concept == "steel"
    assert denom_hits[0].projected_physics["dominance"] >= 0.7


def test_polysemy_sense_disambiguation(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    tree_sense = engine.get_vector("bark", context_lemmas={"oak", "tree", "trunk"})
    assert tree_sense is not None
    assert tree_sense["ontological_domain"] == "ARTIFACT_SOLID"

    dog_sense = engine.get_vector("bark", context_lemmas={"hound", "dog", "loud"})
    assert dog_sense is not None
    assert dog_sense["ontological_domain"] == "SOUND"


def test_counterfactual_and_aborted_modality_gating(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    manuscript = (
        "Had Mara extinguished the lantern, the room would have been dark.\n\n"
        "Mara almost extinguished the lantern.\n\n"
        "Kael read the inscription."
    )
    report = engine.analyze_document(manuscript)
    assert report.ticks[0].lighting_state == "LIT"
    assert report.ticks[1].lighting_state == "LIT"
    assert len(report.continuity_alerts) == 0


def test_passive_voice_phrasal_verb_and_pronoun_coreference(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    manuscript = (
        "The lantern was put out by Mara.\n\n"
        "Kael stepped into the room. He read the inscription."
    )
    report = engine.analyze_document(manuscript)
    assert report.ticks[0].lighting_state == "DARK"
    lighting_errors = [a for a in report.continuity_alerts if a.alert_type == "LIGHTING_CONTRADICTION"]
    assert len(lighting_errors) == 1
    assert lighting_errors[0].entity == "Kael"
    assert "pitch black" in lighting_errors[0].explanation


def test_entity_name_collision_sir_grinn_vs_sir_grimm(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    # Mirrors Chapter 4 of Lance and the Dragon: 'Sir Grinn' (frequent) vs 'Sir Grimm' (1-time typo)
    manuscript = "\n\n".join([
        "Sir Grinn taught the knightlings how to use a compass.",
        "Sir Grinn moved quietly in his leather and chain mail.",
        "Sir Grinn dabbed the banneret with a towel.",
        "Sir Grimm took the bucket of water from Lance.",
    ])
    report = engine.analyze_document(manuscript)
    collisions = [a for a in report.continuity_alerts if a.alert_type == "ENTITY_NAME_COLLISION"]
    assert len(collisions) == 1
    assert collisions[0].entity == "Sir Grimm"
    assert "Sir Grinn" in collisions[0].explanation


def test_compound_ngram_typo_anomaly_knight_kings(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    # Mirrors Chapter 18 of Lance and the Dragon: 'knightlings' vs 'knight kings'
    manuscript = "\n\n".join([
        "The knightlings practiced in the yard.",
        "Sir Balk instructed the knightlings on the course.",
        "The knightlings pulled a stone from their bags.",
        "Let us get the two knight kings home to your father.",
    ])
    report = engine.analyze_document(manuscript)
    anomalies = [a for a in report.continuity_alerts if a.alert_type == "NGRAM_TYPO_ANOMALY"]
    assert len(anomalies) == 1
    assert anomalies[0].trigger_span == "knight kings"
    assert "knightlings" in anomalies[0].explanation


def test_bidirectional_appositive_alias_binding(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    # Mirrors Chapter 4: "Dame Verona, the short knight in purple armor, was the strictest."
    manuscript = (
        "Dame Verona, the short knight in purple armor, was the strictest.\n\n"
        "Later, the purple knight entered the yard."
    )
    report = engine.analyze_document(manuscript)
    assert report.resolved_aliases.get("purple knight") == "Dame Verona"
    assert "Dame Verona" in report.ticks[1].present_cast


def test_temporal_hyperbole_sarcasm_selica(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    # Mirrors Chapter 3 of Lance and the Dragon: Selica's temporal snark
    manuscript = (
        '"Hopefully, the next one will only take half a day rather than a full one," Selica groaned.'
    )
    report = engine.analyze_document(manuscript)
    assert len(report.subtext_hits) == 1
    assert report.subtext_hits[0].subtext_category == "TEMPORAL_HYPERBOLE_SARCASM"


def test_gricean_evasion_subtext(tmp_path: Path) -> None:
    engine = get_test_engine(tmp_path)
    manuscript = (
        'Mara stared at Kael. "Did you burn the secret letter?"\n\n'
        '"The tavern is freezing," Kael said.'
    )
    report = engine.analyze_document(manuscript)
    evasion_hits = [s for s in report.subtext_hits if s.subtext_category == "GRICEAN_EVASION"]
    assert len(evasion_hits) == 1
    assert "total dodge" in evasion_hits[0].comprehension_note