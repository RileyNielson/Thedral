import json
import re
from backend.config import STUDIO_MODEL, LLM_OPTIONS, ENABLE_AI

SOCRATIC_OFFLINE_NOTICE = (
    "🏛️ Sovereign Pure Math Mode Active.\n"
    "All local machine learning is disabled. Thedral is operating purely on "
    "deterministic pacing physics, cadence standard deviation, and SQLite event sourcing."
)

# =============================================================================
# 1. NON-PRESCRIPTIVE SOCRATIC MIRROR & VOICE PRESERVATION DIRECTIVE
# =============================================================================

SOCRATIC_MIRROR_RUBRIC = """You are the Socratic Mirror for Thedral.
Your supreme directive is NON-PRESCRIPTIVE PHENOMENOLOGICAL MIRRORING of the reader's consciousness.

===============================================================================
IMMUTABLE CRAFT LAWS:
===============================================================================
1. NEVER judge the prose as "good" or "bad."
2. NEVER prescribe what the author "should" or "must" do.
3. NEVER ghostwrite, autocomplete, or suggest replacement sentences.
4. PROTECT IDIOSYNCRASY: Never homogenize the author's voice into generic modern commercial boilerplate or sterile MFA minimalism. If the author uses ornate syntax, deliberate repetition, or poetic fragments, evaluate the musicality of the cadence rather than flattening it.
5. BAN CLICHÉD PHYSICALITY: Never suggest generic physiological tropes ("clenching jaws", "racing hearts", "sweating palms").

Treat the prose as an optical, somatic, and cognitive simulation running in the reader's brain.

OUTPUT FORMAT (STRICTLY USE THESE THREE EXACT HEADINGS):

⚡ 1. WHAT THE PROSE DOES (To the Reader's Consciousness)
- Objectively describe what the text accomplishes on the reader's psychology.
- Identify the active forces: cadence tempo, sensory decoupling, weaponized bias, psychic distance level, terminal stress.
- Cite exact quoted phrases demonstrating these effects.

🌑 2. WHAT THE PROSE DOES NOT DO (What It Denies the Reader)
- Objectively catalog the dramatic, physical, or emotional elements withheld from the reader.
- Note any unvoiced stakes, ungrounded environments, or suppressed emotional consequences.

⚖️ 3. THE SOVEREIGN INTENT INQUIRY
- Present the artistic divergence based on the author's potential goals:
  • "If your goal is [Reaction A, e.g. cold procedural momentum], keeping [X] unstated achieves that."
  • "If your goal is [Reaction B, e.g. intimate somatic dread], does leaving [Y] in the dark accomplish that, or does it leave the reader detached?"
- Leave all artistic decisions to the sovereign author.
"""

def elevate_prose_diagnosis(
    passage: str, 
    surrounding: str = "", 
    telemetry: dict | None = None, 
    scene_id: str | None = None
) -> str:
    """
    Evaluates what the text DOES and DOES NOT do to the reader without prescriptive AI bias.
    Dynamically injects the omniscient context dossier if a scene_id is supplied.
    """
    if not ENABLE_AI:
        return SOCRATIC_OFFLINE_NOTICE

    if not passage or not passage.strip():
        return "Select a passage in the editor to run a Socratic mirror diagnosis."

    try:
        import ollama
    except ImportError:
        return SOCRATIC_OFFLINE_NOTICE

    # Lazy import to keep module decoupled during standalone tests
    dossier_text = ""
    if scene_id:
        try:
            from backend.dossier import compile_scene_dossier
            from backend.database import get_db
            conn = get_db()
            dossier = compile_scene_dossier(conn, scene_id)
            dossier_text = dossier.get("briefing_text", "")
            conn.close()
        except Exception:
            dossier_text = ""

    telemetry_note = ""
    if telemetry:
        telemetry_note = (
            f"\n[PACING PHYSICS & TELEMETRY]:\n"
            f"• Tension Elevation: {telemetry.get('tension_elevation', 'N/A')}\n"
            f"• Pacing Momentum: {telemetry.get('pacing_momentum', 'N/A')} ({telemetry.get('slope_diagnosis', 'N/A')})\n"
            f"• Cadence StDev: {telemetry.get('cadence_stdev', 'N/A')} (Avg sentence: {telemetry.get('avg_sentence', 'N/A')}w)\n"
            f"• Filter Verbs: {list(telemetry.get('filters', {}).keys())}\n"
        )

    context_block = f"{dossier_text}\n\n=== SURROUNDING SCENE BEAT ===\n{surrounding}\n" if dossier_text else f"=== SURROUNDING SCENE BEAT ===\n{surrounding}\n"

    prompt = (
        f"{SOCRATIC_MIRROR_RUBRIC}\n\n"
        f"{context_block}"
        f"{telemetry_note}\n"
        f"=== TARGET PASSAGE TO MIRROR ===\n\"{passage}\"\n\n"
        f"Hold up the mirror. Dissect what the prose DOES, what it DOES NOT DO, and present the Sovereign Intent Inquiry."
    )

    try:
        resp = ollama.chat(
            model=STUDIO_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options=LLM_OPTIONS
        )
        return resp['message']['content']
    except Exception as e:
        return SOCRATIC_OFFLINE_NOTICE

# =============================================================================
# 2. GHOST SURVEYOR (Clutter-Shielded Relational Extraction)
# =============================================================================

GHOST_SURVEYOR_PROMPT = """You are the automated Surveyor Engine for Cosmograph.
Extract character and item state transitions into THREE STRICT EPISTEMIC TIERS.

STRICT ENTITY CLASSIFICATION:
- "CHARACTER": ONLY named sentient beings (e.g. Ellie, Vance, Lord Malakor).
- "ITEM": ONLY plot-critical artifacts, weapons, keys, poisons, documents.
- FORBIDDEN: Do NOT extract food, meals, ordinary clothing, background furniture, or ambient clutter.

EPISTEMIC TIERS:
1. [FACT]: Direct, objective narrator statements describing reality (e.g. "The latch snapped." -> latch = broken).
2. [CLAIM]: Spoken dialogue, biased assumptions, or character declarations that may be false (e.g. "'I burned the letter,' Vance lied.").
3. [INFERENCE]: Physical symptoms or sensory deductions where the root cause is implied (e.g. "Dark liquid seeped through his bandages.").

OUTPUT FORMAT (STRICT JSON ONLY):
[
  {
    "detected_entity_name": "Entity Name",
    "entity_type": "CHARACTER" | "ITEM",
    "epistemic_tier": "FACT" | "CLAIM" | "INFERENCE",
    "attested_by": "Character Name or null",
    "source_span_text": "Exact short quote",
    "proposed_delta": {
      "location": "Location Name if known",
      "health_score": 1.0
    },
    "confidence": 0.8
  }
]
"""

def extract_ghost_proposals(scene_text: str) -> list[dict]:
    """Extracts candidate state deltas without modifying canonical database truth."""
    if not ENABLE_AI or not scene_text or len(scene_text.strip()) < 40:
        return []
    try:
        import ollama
        resp = ollama.chat(
            model=STUDIO_MODEL,
            messages=[
                {"role": "system", "content": GHOST_SURVEYOR_PROMPT},
                {"role": "user", "content": f"Scene Prose:\n{scene_text[:3500]}"}
            ],
            format="json",
            options=LLM_OPTIONS
        )
        data = json.loads(resp['message']['content'])
        if isinstance(data, dict):
            data = data.get("proposals", data.get("deltas", [data]))
        return [d for d in data if isinstance(d, dict) and d.get("detected_entity_name")]
    except Exception:
        return []

# =============================================================================
# 3. SYNAPTIC SERENDIPITY ENGINE
# =============================================================================

SERENDIPITY_PROMPT = """You are the Synaptic Resonance Engine for Thedral.
Examine this scene and review the established world lore. Identify ONE unexpected, organic connection that could tie this scene deeper into the universe's history, a dormant item, or a character's backstory.
Present it as an inquiry: "What if X is connected to Y from Chapter Z?"
Keep it under 3 sentences. Do not write the prose.
"""

def discover_synaptic_resonance(scene_text: str, lore_summary: str) -> str:
    """Uncovers dormant connections between the current scene and existing series lore."""
    if not ENABLE_AI:
        return "Resonance engine offline (Pure Math Mode active)."
    try:
        import ollama
        prompt = f"{SERENDIPITY_PROMPT}\n\nLORE REPOSITORY:\n{lore_summary}\n\nCURRENT SCENE TEXT:\n{scene_text[:3000]}"
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": prompt}], options=LLM_OPTIONS)
        return resp['message']['content']
    except Exception:
        return "Resonance calculation unavailable offline."

# =============================================================================
# 4. CROSS-GENRE SOCRATIC TUTOR
# =============================================================================

TUTOR_PROMPT = """You are an elite MFA Creative Writing Professor and Master Stylist.
The author is asking you for a specific craft technique or structural goal.

YOUR DIRECTIVE (THE CROSS-GENRE LAW):
To ensure the author never accidentally adopts your prose, you must NEVER teach the principle using the author's own setting, characters, or genre. 

1. Identify the core mechanical lever the author needs (e.g., to create claustrophobia, restrict the sensory radius; to create dread, dilate the time between cause and effect).
2. Teach this principle by writing a 2-sentence example from a COMPLETELY UNRELATED GENRE. 
   (e.g., If the author's context is a fantasy airship, teach the concept using a cold-war submarine, a western saloon, or a contemporary hospital room).
3. Contrast a "Basic" execution vs. a "Masterful" execution of your invented example using Level 2-4 Craft (Sensor Decoupling, Somatic Reflexes, Terminal Stress).
4. End with a probing question challenging the author to apply that exact mechanical lever back into their own scene.
"""

def get_socratic_lesson(question: str, context: str = "") -> str:
    """Delivers a mini-masterclass on a specific craft technique."""
    if not ENABLE_AI:
        return SOCRATIC_OFFLINE_NOTICE
    try:
        import ollama
        prompt = f"{TUTOR_PROMPT}\n\n=== AUTHOR'S GOAL ===\n{question}\n\n=== SCENE CONTEXT ===\n{context}"
        resp = ollama.chat(model=STUDIO_MODEL, messages=[{"role": "user", "content": prompt}], options=LLM_OPTIONS)
        return resp["message"]["content"]
    except Exception:
        return SOCRATIC_OFFLINE_NOTICE