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
        brain: VirtualBrainState,
    ) -> ParagraphDiagnosis:
        clean = raw_paragraph.strip()
        words = [w.lower() for w in extract_words(clean)]
        word_set = set(words)
        low_para = clean.lower()
        has_dialogue_quote = any(q in clean for q in ('"', "“", "”"))

        substantive_vectors = [v for v in word_vectors if v and v["lemma"] not in EXCLUDED_FROM_ENTITIES]
        content_nouns = {w for w in word_set if len(w) >= 4 and w not in EXCLUDED_FROM_ENTITIES}

        # --- 1. TRACK THE STORY SO FAR (CUMULATIVE WORKING MEMORY) ---
        tension_label = "High Tension" if arousal >= 0.6 else "Moderate Pressure" if arousal >= 0.3 else "Reflective / Calm"
        active_thread_labels = [t.label for t in brain.active_threads if t.status != "RESOLVED"][:3]
        
        story_so_far = StorySoFar(
            location=brain.current_location,
            characters_present=list(brain.present_cast)[:4],
            active_threads=active_thread_labels,
            active_tension_level=tension_label
        )

        # --- 2. MEASURE THREAD IMPACT (SEED, ESCALATE, PAYOFF) ---
        thread_impact = None

        # Check for Thread Seed: Major volition, goal, or unanswered question
        if any(v in low_para for v in ("one way or another", "had a plan", "a plan if", "don't get caught", "hoped one day")) or (
            "?" in clean and not has_dialogue_quote and len(words) >= 6
        ):
            seed_label = (
                "Unshakable Resolve" if "one way or another" in low_para else
                "Secret Contingency Plan" if "had a plan" in low_para else
                "Core Goal: Evade Capture" if "don't get caught" in low_para else
                "Aspirational Yearning" if "hoped one day" in low_para else
                f"Curiosity Hook: {clean[:40]}..."
            )
            thread_id = f"thread_{len(brain.active_threads) + 1}"
            brain.active_threads.append(
                ActiveStoryThread(
                    thread_id=thread_id,
                    label=seed_label,
                    seeded_paragraph=paragraph_index,
                    last_touched_paragraph=paragraph_index,
                    key_terms=content_nouns,
                    status="ACTIVE"
                )
            )
            thread_impact = ThreadImpact(
                action_type="SEED",
                thread_name=seed_label,
                detail="Seeds a new question or objective the reader carries forward."
            )

        # Check for Thread Escalation or Payoff
        elif brain.active_threads:
            for thread in reversed(brain.active_threads):
                if thread.status == "RESOLVED":
                    continue
                # Overlap with thread's key terms
                if thread.key_terms & content_nouns or (any(c.lower() in low_para for c in brain.present_cast)):
                    thread.last_touched_paragraph = paragraph_index
                    # Payoff cue
                    if any(w in word_set for w in ("finally", "escaped", "managed", "landed", "saved", "confirmed", "revealed")):
                        thread.status = "RESOLVED"
                        thread_impact = ThreadImpact(
                            action_type="PAYOFF",
                            thread_name=thread.label,
                            detail=f"Delivers a tangible outcome or answer to earlier setup from P{thread.seeded_paragraph}."
                        )
                        break
                    # Escalation cue
                    elif any(w in word_set for w in ("scars", "trapped", "guards", "caught", "screaming", "crashed", "danger", "hissed", "afraid", "pain")):
                        thread.status = "ESCALATED"
                        thread_impact = ThreadImpact(
                            action_type="ESCALATE",
                            thread_name=thread.label,
                            detail=f"Complicates or raises the stakes on '{thread.label}'."
                        )
                        break

        if not thread_impact:
            thread_impact = ThreadImpact(
                action_type="MAINTAIN",
                thread_name="Active Currents",
                detail="Develops narrative momentum and sensory setting without shifting main threads."
            )

        # --- 3. CLASSIFY PARAGRAPH SENSORY & CRAFT FUNCTION ---
        # Section boundary
        if paragraph_index == 1 and len(words) <= 4 and not has_dialogue_quote:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Scene / Chapter Heading",
                cognitive_function="HEADING",
                reader_experience="Sets the formal boundary of the section.",
                salient_words=[w for w in words if w not in EXCLUDED_FROM_ENTITIES],
                primary_senses=[],
                craft_advisory=None,
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Staccato beat
        if len(words) <= 3 and not has_dialogue_quote:
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Staccato Pulse & Kinetic Acceleration",
                cognitive_function="STACCATO_PULSE",
                reader_experience="Isolated staccato pulse. Drops narrative padding to accelerate reader heart rate.",
                salient_words=[w for w in words if w not in EXCLUDED_FROM_ENTITIES],
                primary_senses=["Pacing/Heartbeat"],
                craft_advisory="High kinetic friction during an escape or confrontation.",
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Non-visual sensory grounding
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
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Kinetic action
        kinetic_verbs = [
            v["lemma"] for v in substantive_vectors 
            if v.get("pos") == "verb" and float(v.get("velocity", 0)) >= 0.45
        ]
        if len(kinetic_verbs) >= 2 or any(k in word_set for k in ("sprint", "sprinted", "chase", "chased", "running", "ran")):
            salient = list(dict.fromkeys(kinetic_verbs + [w for w in ("running", "ran", "sprinted", "escaped") if w in word_set]))[:4]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Kinetic Momentum & Motion",
                cognitive_function="KINETIC_ACTION",
                reader_experience="High physical velocity. The reader visualizes active movement and anticipates impact.",
                salient_words=salient,
                primary_senses=["Visual/Kinetic"],
                craft_advisory="Strong forward momentum. Great place for clean, staccato physical verbs.",
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Social hierarchy & status
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
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Spatial architecture pause
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
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Character interiority & concealed secrets
        interior_lemmas = [
            v["lemma"] for v in substantive_vectors 
            if v.get("ontological_domain") == "ABSTRACT_STATE" 
            and (float(v.get("arousal", 0)) >= 0.25 or float(v.get("valence", 0)) <= -0.25)
        ]
        has_secrets = any(w in word_set for w in ("secret", "secrets", "thief", "hiding", "heartthrob", "worried", "nerves", "afraid"))
        if (len(interior_lemmas) >= 2 or has_secrets or "?" in clean) and not has_dialogue_quote:
            salient = list(dict.fromkeys(interior_lemmas + [w for w in ("secret", "thief", "hiding", "nerves", "afraid", "worried") if w in word_set]))[:4]
            return ParagraphDiagnosis(
                paragraph_index=paragraph_index,
                headline="Internal Stakes & Concealed Secrets",
                cognitive_function="INTERIOR_STAKES",
                reader_experience=(
                    "Internal stakes. The reader steps inside the protagonist's mind as she navigates fear, conceals her identity, and weighs her options under pressure."
                ),
                salient_words=salient,
                primary_senses=["Interoception/Doubt"],
                craft_advisory="Strong character intimacy. The reader feels the pressure of keeping secrets.",
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Dialogue & speech acts
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
                story_so_far=story_so_far,
                thread_impact=thread_impact
            )

        # Default Narrative Flow
        clean_salient = [w for w in words if len(w) > 4 and w not in EXCLUDED_FROM_ENTITIES]
        return ParagraphDiagnosis(
            paragraph_index=paragraph_index,
            headline="Narrative Progression",
            cognitive_function="NARRATIVE_FLOW",
            reader_experience="Seamless narrative movement carrying the scene forward.",
            salient_words=clean_salient[:3],
            primary_senses=["Visual"],
            craft_advisory=None,
            story_so_far=story_so_far,
            thread_impact=thread_impact
        )
