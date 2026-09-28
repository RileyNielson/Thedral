import ollama
from config import STUDIO_MODEL, LLM_OPTIONS, ACTIVE_CONTEXT
from db import get_db

HIGH_TIER_CRAFT_RUBRIC = """
YOU ARE AN ELITE LITERARY STYLIST AND SENIOR EDITOR.
Analyze the target prose against the FOUR TIERS OF MASTER-CRAFT FICTION:

=== LEVEL 2: VISCERAL SHOWING (SENSOR DECOUPLING) ===
1. ELIMINATE FILTER WORDS: Decouple the sensory apparatus. Strip "I saw", "he heard", "she noticed". Make the world act directly on the reader.
2. SOMATIC REFLEXES OVER LABELS: Replace named emotions ("a jolt of panic", "he was furious") with involuntary physical mechanics (lungs locking on an exhale, heel dragging, pulse hammering in the molars).
3. FORENSIC DEDUCTION: Show the physical damage/evidence; never state the conclusion. (Don't say "a violent struggle took place"; show the silvered mirror plates caved inward at shoulder-height with skin clinging to the glass).

=== LEVEL 3: SUBTEXT & NARRATIVE PRESSURE ===
1. WEAPONIZED PERCEPTION (BIASED LENS): No description is neutral. Every object, chandelier, or street must be filtered through the POV character's economic trauma, prejudices, and survival fears. (A ballroom isn't crystal and silk—it's "three hundred tax receipts swaddled in watered silk beneath glittering icicles").
2. DISPLACEMENT OF INTENT (PROXY DIALOGUE): Characters must NEVER speak on-the-nose emotion. Displace terror/grief/love onto a trivial physical proxy (the cost of tallow, a frayed twine, a dull knife).
3. ASYMMETRY OF INFORMATION (ENGINEERED 2 + 2 GAPS): Withhold the connective tissue. Give the reader 2 + 2; never give them 4. (Don't say the guard is a rebel docker; show him checking the printer's mark in the margin rather than the magistrate's wax seal).
4. RHYTHMIC COUNTERPOINT:
   - Staccato Climax: Monosyllabic impacts for kinetic violence ("Boot struck stone. The slate split.").
   - Suspended Shock: Long, falling, polysyllabic cadences for aftermath and shock.

=== LEVEL 4: STRUCTURAL INEVITABILITY & THEMATIC RESONANCE ===
1. THE MICROCOSM PRINCIPLE: Ensure tactical micro-actions mirror the macro-thematic tragedy/paradox of the entire book.
2. THEMATIC DISSONANCE IN DICTION: Collide mismatched vocabularies (e.g. cold bureaucratic ledger terms colliding with warm decaying human flesh).
3. DRAMATIC IRONY AS COMPLICITY: Let the POV character rationalize their own trap while the reader spots the teeth closing.
4. TERMINAL STRESS (SYNTACTIC END-FOCUS): The heaviest, most fatal, emotionally charged word or image MUST land as the final syllable of the sentence. Never allow a sentence to dribble away into weak modifiers or prepositional phrases.

IMMUTABLE CREATIVE SAFEGUARD (ZERO AI PROSE):
- NEVER write replacement sentences or ghostwrite revised prose.
- Pinpoint the exact quoted words where the technique falls short.
- Formulate 2-3 surgical Socratic prompts that force the AUTHOR to apply these master-tier techniques.
"""

def query_socratic(user_text: str, context_str: str = "", telemetry_dict: dict = None) -> str:
    telemetry_summary = ""
    if telemetry_dict:
        telemetry_summary = (
            f"\n[SCENE TELEMETRY DATA]:\n"
            f"• Tension Elevation (Y): {telemetry_dict.get('tension_elevation', 'N/A')}\n"
            f"• Pacing Slope (dY/dX): {telemetry_dict.get('pacing_slope', 'N/A')} ({telemetry_dict.get('slope_diagnosis', 'N/A')})\n"
            f"• Cadence StDev: {telemetry_dict.get('cadence_stdev', 'N/A')} (Avg length: {telemetry_dict.get('avg_sentence_len', 'N/A')} words)\n"
            f"• Top Filter Verbs: {telemetry_dict.get('top_filters', {})}\n"
            f"• Top Crutch Words: {telemetry_dict.get('top_crutches', {})}\n"
        )

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT term, rule FROM style_sheet LIMIT 10")
    rules = c.fetchall()
    conn.close()

    style_rules_str = "\n[STYLE CONVENTIONS]:\n" + "\n".join([f"• {r['term']}: {r['rule']}" for r in rules]) if rules else ""

    meta_context = (
        f"MANUSCRIPT: {ACTIVE_CONTEXT.get('book_title', 'Victorian Skies')}\n"
        f"ACTIVE CHAPTER: {ACTIVE_CONTEXT.get('active_chapter', 1)}\n"
        f"{style_rules_str}\n{telemetry_summary}\n"
        f"=== SURROUNDING SCENE BEAT ===\n{context_str}\n"
    )

    full_prompt = (
        f"{HIGH_TIER_CRAFT_RUBRIC}\n\n"
        f"=== CONTEXT ===\n{meta_context}\n"
        f"=== AUTHOR'S PASSAGE / QUERY ===\n{user_text}\n\n"
        f"Diagnose this text. Focus on: (1) Current Tier Assessment, (2) Specific Mechanical Flaws (Filters, Labels, Neutral Camera, Weak Endings), and (3) Socratic Craft Prompts for Level 2-4 Elevation."
    )

    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": full_prompt}], options=LLM_OPTIONS)
        return resp['message']['content']
    except Exception as e:
        return f"⚠️ Socratic Engine Notice: Local Ollama error ({e}). Ensure `ollama serve` is running."

def elevate_prose_diagnosis(target_text: str, scene_context: str) -> str:
    """Specialized deep-dive diagnostic for pushing a specific paragraph to Level 3 & 4."""
    prompt = (
        f"{HIGH_TIER_CRAFT_RUBRIC}\n\n"
        f"=== SURROUNDING SCENE ===\n{scene_context}\n\n"
        f"=== TARGET PASSAGE TO ELEVATE ===\n\"{target_text}\"\n\n"
        f"Perform an uncompromising Level 2 to Level 4 elevation analysis:\n"
        f"1. ⚡ SENSORY & SOMATIC AUDIT: Flag any emotional labels, filter verbs, or stated conclusions.\n"
        f"2. 🎭 SUBTEXT & PRESSURE AUDIT: How can the perception be weaponized? Is the dialogue displaced onto a proxy?\n"
        f"3. 🏛️ TERMINAL STRESS & CADENCE: Does the final sentence hit with fatal weight, or does it dissipate?\n"
        f"4. 💡 SOCRATIC ELEVATION PROMPTS: 3 questions challenging the author to rewrite this into master-tier prose."
    )
    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": prompt}], options=LLM_OPTIONS)
        return resp['message']['content']
    except Exception as e:
        return f"⚠️ Could not complete elevation analysis: {e}"

def generate_kdp_package(sample_text: str) -> str:
    KDP_MARKETING_PROMPT = """Analyze the story sample and output:
1. 🎯 7 HIGH-TRAFFIC SEARCH KEYWORDS (Target long-tail buyer phrases).
2. 🏷️ 3 SPECIFIC AMAZON CATEGORY PATHS.
3. 🪝 3 BACK-COVER BLURB HOOKS.
4. 📚 2 COMPARATIVE TITLES/AUTHORS.
"""
    user_prompt = f"Book Title: {ACTIVE_CONTEXT.get('book_title', 'Victorian Skies')}\nSample:\n{sample_text[:4000]}"
    try:
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "system", "content": KDP_MARKETING_PROMPT}, {"role": "user", "content": user_prompt}], options=LLM_OPTIONS)
        return resp['message']['content']
    except Exception as e:
        return f"⚠️ KDP Engine Notice: Ollama error ({e})."
