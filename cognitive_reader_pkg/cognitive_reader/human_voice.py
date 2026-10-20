from typing import Dict, List, Optional


def describe_metaphor_naturally(
    target_word: str,
    source_phrase: str,
    metaphor_type: str,
    physics: Dict[str, float],
) -> str:
    if metaphor_type == "idiom_expression":
        return (
            f"I read `{source_phrase}` as a figure of speech meaning *{target_word}*, "
            f"not as a literal physical action in the scene."
        )

    qualities: List[str] = []
    if physics.get("mass_weight", 0) >= 0.6:
        qualities.append("heavy and crushing")
    elif physics.get("mass_weight", 0) <= -0.6:
        qualities.append("light and fragile")

    if physics.get("velocity", 0) <= -0.6:
        qualities.append("stuck in place and impossible to shake")
    elif physics.get("velocity", 0) >= 0.6:
        qualities.append("fast and sudden")

    if physics.get("sharpness", 0) >= 0.6:
        qualities.append("sharp and cutting")
    elif physics.get("sharpness", 0) <= -0.6:
        qualities.append("soft and gentle")

    if physics.get("corrosion_decay", 0) >= 0.6:
        qualities.append("worn down and eating away at things")

    if physics.get("temperature", 0) >= 0.6:
        qualities.append("burning hot")
    elif physics.get("temperature", 0) <= -0.6:
        qualities.append("freezing and numb")

    if physics.get("dominance", 0) <= -0.7:
        qualities.append("suffocating and trapping")
    elif physics.get("dominance", 0) >= 0.65:
        qualities.append("armored, unyielding, and strong")

    if not qualities:
        qualities.append("vivid and physical")

    feeling_str = (
        qualities[0]
        if len(qualities) == 1
        else ", ".join(qualities[:-1]) + f", and {qualities[-1]}"
    )

    if metaphor_type == "denominal_verb_metaphor":
        return (
            f"Turning the noun `{source_phrase}` into an action here makes `{target_word}` "
            f"feel {feeling_str}."
        )

    if metaphor_type == "verb_frame_metaphor":
        subj, verb = (
            source_phrase.split("->")
            if "->" in source_phrase
            else (source_phrase, "acting on")
        )
        return (
            f"Having the `{subj}` literally *{verb}* the `{target_word}` makes the moment feel "
            f"{feeling_str}."
        )

    return (
        f"Comparing `{target_word}` to `{source_phrase}` really works—it makes the image "
        f"come across as {feeling_str}."
    )


def describe_subtext_naturally(
    utterance: str,
    speaker: Optional[str],
    target_entity: Optional[str],
    subtext_category: str,
    surface_valence: float,
    contextual_prior: float,
    matched_masks: List[str],
    matched_leaks: List[str],
    prior_question: Optional[str] = None,
    prior_word_count: int = 0,
    reply_word_count: int = 0,
) -> str:
    who = speaker or "The speaker"
    listener = target_entity or "them"

    if subtext_category == "GRICEAN_EVASION" and prior_question:
        return (
            f"When {who} says `\"{utterance}\"`, it feels like a total dodge. "
            f"{listener} just asked `\"{prior_question}\"`, and {who} completely changes the subject "
            f"instead of answering."
        )

    if subtext_category == "QUANTITY_ASYMMETRY":
        return (
            f"{listener} just spoke {prior_word_count} words, and {who} shuts it down with a "
            f"{reply_word_count}-word reply (`\"{utterance}\"`). It reads like {who} is stonewalling "
            f"or pulling away."
        )

    if subtext_category == "TEMPORAL_HYPERBOLE_SARCASM":
        return (
            f"`\"{utterance}\"` lands as dry, exaggerated snark—stretching the time out like that "
            f"makes it clear {who} is mocking the effort rather than actually being hopeful."
        )

    parts: List[str] = []
    if surface_valence >= 0.35 and contextual_prior <= -0.20:
        parts.append(
            f"`\"{utterance}\"` reads as sarcastic or insincere—the words sound super positive, "
            f"but the mood around {listener} is already tense and negative"
        )
    elif surface_valence <= -0.35 and contextual_prior >= 0.30:
        parts.append(
            f"`\"{utterance}\"` sounds like playful teasing or dry understatement, since {who} "
            f"is actually on warm terms with {listener}"
        )
    else:
        parts.append(f"There is a lot of unspoken tension underneath `\"{utterance}\"`")

    if matched_masks:
        mask_list = " and ".join(f"`{m}`" for m in matched_masks)
        parts.append(
            f"especially since {who} puts on a polite front ({mask_list}) to hide how they really feel"
        )

    if matched_leaks:
        leak_list = " and ".join(f"`{l}`" for l in matched_leaks)
        parts.append(
            f"and their body language ({leak_list}) gives away how stressed or angry they actually are"
        )

    return ", ".join(parts) + "."


def describe_lighting_error_naturally(
    actor: str, verb_lemma: str, raw_span: str, light_source: Optional[str]
) -> str:
    src = f"the `{light_source}`" if light_source else "the light"
    return (
        f"Wait—{src} was put out earlier, so the room should be pitch black right now. "
        f"How is `{actor}` able to `{verb_lemma}` in `{raw_span}` without a light source?"
    )


def describe_memory_decay_naturally(entity: str, words_since_seen: int) -> str:
    pages_approx = max(1, round(words_since_seen / 250))
    return (
        f"When `{entity}` showed up here, I had to pause and ask, *'Wait, who or what is that again?'* "
        f"It was only mentioned once about {words_since_seen:,} words (~{pages_approx} pages) ago, "
        f"so it slipped out of my head. A quick reminder phrase would help."
    )


def describe_name_collision_naturally(
    rare_name: str, canonical_name: str, rare_count: int, canon_count: int
) -> str:
    return (
        f"Possible name typo: `{rare_name}` only appears {rare_count} time(s), and it looks almost "
        f"identical to `{canonical_name}` (which appears {canon_count} times). Did you mean `{canonical_name}`?"
    )


def describe_ngram_anomaly_naturally(odd_bigram: str, expected_compound: str) -> str:
    return (
        f"Possible word-split typo: `{odd_bigram}` looks like an accidental split or spellcheck swap "
        f"for `{expected_compound}` (which you use elsewhere in the story)."
    )


def describe_habituation_naturally(high_intensity_words: List[str]) -> str:
    sample = ", ".join(f"`{w}`" for w in high_intensity_words[:4])
    return (
        f"I'm starting to feel a little numb to the intensity here. We've had several heavy paragraphs "
        f"in a row packed with intense words ({sample}). Giving the reader a quiet beat to breathe "
        f"would make the next big hit land much harder."
    )