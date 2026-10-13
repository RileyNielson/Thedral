# 🏛️ Thedral

> **The Sovereign Narrative Flight Simulator for Novelists**  
> *Powered by the Creare Engine • Local-First • Air-Gapped • AGPLv3*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-amber.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Local Inference](https://img.shields.io/badge/Local_AI-Llama_3.2:3b-blue.svg)](https://ollama.com)
[![Engine Integrity](https://img.shields.io/badge/Tests-32%2F32_Passed-emerald.svg)](./tests/test_suite.py)
[![Zero Cloud Egress](https://img.shields.io/badge/Cloud_Surveillance-Zero-rose.svg)](#the-zero-ai-prose-law)

---

## The Sovereign Manifesto

Modern writing tools have converged on two extremes:
1. **Outdated Silos**: Legacy desktop word processors with static 2D outliners and zero awareness of pacing dynamics or diegetic spacetime.
2. **Predatory Cloud AI**: Subscription SaaS platforms charging $20–$60/month to scrape your private manuscripts into cloud training caches, encouraging generic generative text that flattens authorial voice.

**Thedral is an open-source flight simulator for long-form fiction.**  
It runs 100% locally on your machine via SQLite Write-Ahead Logging (WAL) and local Ollama inference. Your manuscript never touches an outside server, cannot be subscription-paywalled, and belongs entirely to you.

### The Zero-AI-Prose Law
> **The machine shall never ghostwrite, autocomplete, or inject prose.**  
> In Thedral, the local language model (Llama 3.2:3b) is architecturally constrained to **Adversarial Socratic Diagnosis**. It acts as a mirror to your prose—evaluating cadence, psychic distance, and suppressed narrative consequences—while leaving 100% of the creative voice in the hands of the sovereign author.

---

## Architectural Pillars

### 1. The 8-Layer 3D Spacetime Manifold (The Cosmograph)
Fiction does not happen on a flat spreadsheet. Thedral plots your novel into a continuous, interactive **3D WebGL Spacetime Coordinate System** (Plotly):
- **X-Axis (Time)**: Continuous Story Days or sequential reading beats.
- **Y-Axis (Space)**: Real story geography (*The Sky Docks, The Sinks, The High Citadel*) or Dramatic Channels (*Interiority vs. Dialogue vs. Action*).
- **Z-Axis (Stakes)**: Cumulative somatic tension elevation ($0.05 \le Z \le 0.98$).
code
Code
Z (Stakes Elevation)
    ▲
    │       ╭─── Climax Peak (Z=0.92)
    │      ╱│
    │  ╭──╯ │   ╭── Falling Action
    │ ╱     │  ╱
    ┼───────┼─┼────────────────► X (Story Time / Beats)
   ╱        │╱
  ▼         ▼
 Y (Physical Geography / Locations)
code
Code
* **Kinematics & Somatics**: Character worldlines rendered as volumetric ribbons shifting color along a biological health gradient (Green $\rightarrow$ Yellow $\rightarrow$ Rose).
* **Convergence Knots**: Cyan diamonds indicating where characters physically inhabit the same room at the same time.
* **Chekhov Gravity Wells**: Visual attractors tracking foreshadowed promises to their payoff chapters.
* **Spatial Teleportation Alarms**: Flags continuity collisions when a character traverses distance with $\Delta t \le 0.05$ days.
* **Flight Camera Angles**: Instant snaps between **3D Spacetime**, **Pacing Mountain Range (X-Z)**, and **Geographic Map (X-Y)**.
* **Sniper-Scroll**: Clicking any 3D anomaly or node transports the editor viewport directly to that paragraph in the prose.

### 2. The Scriptorium & The Void
- **TipTap / ProseMirror Core**: Desktop publishing-grade typography (automatic em-dashes `—`, ellipses `…`, and proper paragraph indents).
- **The Void**: A pure black, sensory-deprivation drafting mode with a breathing HUD for uninhibited flow states.
- **Micro-Stall Whirlpool Alert**: Detects when an author rewrites the same section 14+ times without forward velocity, prompting an automated `[TK]` insertion protocol.
- **Craft X-Ray**: Real-time sentence classification:
  - 🟥 **Escalators**: Staccato cadence ($<9\text{w}$) and kinetic friction.
  - 🟩 **Resolvers**: Falling cadences ($\ge 22\text{w}$) and contemplative breathing space.
  - 🟨 **Pivots**: Complication and narrative hinge clauses.
  - ⬜ **Slack**: Filter verb and crutch word clutter.
- **Live Reading Bead**: As you scroll down your manuscript, a glowing cyan bead glides along the 3D Chapter Lens in real time, showing your exact position in the dramatic arc.

### 3. Span-Linked Causality & Severed Threads
- Paragraphs are hashed using **Content-Normalized Semantic Block Hashing** (case- and punctuation-invariant).
- Canonical worldlines attach established story facts directly to paragraph hashes.
- If an author excises or rewrites a sentence that anchored an established worldline fact, the engine flags a **Severed Causal Thread** warning without modifying the prose.
- **Story Underneath** automatically analyzes every scene after import, follows explicit questions and promises into later callbacks, spots `yes, and` / `yes, but` / `no, and` / `no, but` turns, and connects selected care, vulnerability, loss, evasion, reassurance, and broken-promise cues across scenes. While drafting, the Reader tab refreshes the current scene from live text and surrounding manuscript context. Each prediction links to its setup and payoff passage and can jump back to the prose. These are deterministic text-pattern rules—not generative AI—and make a confident prediction about a typical reader while acknowledging once that individual reactions vary.
- The no-AI reader lens can optionally use the prepared [English Wiktionary SQLite dataset](https://huggingface.co/datasets/cstr/en-wiktionary-sqlite-full) to expand cue vocabulary with synonyms and word forms. Install it with `./venv/bin/python -m backend.wiktionary_lexicon --download` (about 418 MB compressed, plus space for the expanded database), or provide an already-downloaded database with `--install /path/to/en_wiktionary_normalized_full.db`. The database stays in the operating system's local Thedral data directory, is queried read-only, and is never committed with the project. The dataset is licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); Thedral reports its source and license in local lexicon status.
- **Cast & Relics Directory** can scan a manuscript for recurring capitalized names and invented terms. It suggests candidates with excerpt evidence and mention counts, but only adds an entity after the author confirms its type. Each canon entity has one primary name and can have multiple alternate names (nicknames, titles, former names, or transliterations). Add one alternate name per line; matches are case-insensitive and whole-name only. A name already assigned to another entity is rejected so a shared title does not silently merge two characters in the maps. When Wiktionary is installed, the review list also identifies whether a term appears in its English entries. Confirmed names and aliases are used in chapter and manuscript maps; scene mentions are shown separately from author-mapped worldline events, and a missing location is left unspecified rather than carried into another scene.

### 4. Non-Prescriptive Socratic Mirror
Powered by a local, air-gapped **Llama 3.2:3b** model via Ollama:
1. **What the Prose Does**: Objectively mirrors the impact on the reader's consciousness (cadence tempo, psychic distance, terminal stress).
2. **What the Prose Denies**: Catalogs suppressed consequences, ungrounded environments, or withheld stakes.
3. **The Sovereign Intent Inquiry**: Poses divergent artistic paths, leaving all choices to the author.
4. **Cross-Genre Tutor**: Teaches narrative craft levers using examples from an unrelated genre to prevent the author from copying the model's diction.

### 5. Deterministic Publishing & Authorship Suite
- **Cryptographic Proof of Authorship**: Generates a tamper-evident SHA-256 audit certificate derived from the append-only SQLite WAL revision history, proving multi-session organic human drafting to legally defend against AI accusations.
- **Omniscient Scrivener Importer**: Ingests `.scriv`, `.docx`, `.txt`, and `.md` bundles, extracting chapters, scenes, index card synopses, document notes, character sheets, and worldbuilding lore into SQLite.
- **Audiobook Narrator Pack**: Compiles phonetic pronunciation guides from the Living Style Sheet and vocal delivery profiles for ACX voice actors.
- **Publication-Grade Word Compiler**: Exports formatted `.docx` manuscripts with centered chapter headers, indented paragraphs, and decoupled epigraphs.

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Engine** | Python 3.11+, FastAPI, SQLite 3 (WAL Mode) |
| **Frontend Studio** | Vue 3 (Composition API), Vite, Tailwind CSS |
| **Rich Text Editor** | TipTap 3, ProseMirror |
| **3D Narrative Spacetime** | Plotly.js (WebGL 3D Scatter & Mesh) |
| **Local Inference** | Ollama (`llama3.2:3b`, 4-bit quantized ~2.0 GB RAM) |
| **Mobile PWA Bridge** | Local Wi-Fi socket listener with dynamic SVG QR code |

---

## Getting Started

### Prerequisites
1. **Python 3.11+**
2. **Node.js 20.19+ or 22.12+ and npm** (the launchers rebuild the interface at startup)
3. **[Ollama](https://ollama.com/download)** (Full mode only)

### Choose Lite or Full

Run `Run_Thedral.bat` on Windows or `Run_Thedral.command` on macOS and select a mode. On Windows, `Run_Thedral_AI.bat` is a shortcut that starts directly in Full mode. If the optional local Wiktionary database is missing, the launchers offer to download it once; declining or a failed download does not prevent Thedral from starting. The downloader reports progress while it streams the compressed dataset.

- **Lite** installs core dependencies only. It does not require Ollama or an AI model. Writing, organization, and deterministic text analysis remain available; AI-assisted actions are disabled and the app displays a Lite-mode notice.
- **Full** enables local AI-assisted features through Ollama. Install and start Ollama, then download the configured model (default `llama3.2:3b`) with `ollama pull llama3.2:3b` before launching. The launchers verify that Ollama is responding and the configured model is present.

On first launch, the launcher creates the Python environment and installs the selected dependencies. Each new start rebuilds the frontend from current sources and checks that the backend is ready before opening the browser. Startup output is shown in the backend console on Windows and recorded at `exports/thedral-backend.log` on macOS. Close the backend console on Windows or press **Control-C** in the macOS launcher to stop Thedral; neither launcher terminates unrelated Python processes.

Configuration can be set in a root `.env` file (copy `.env.example` to `.env`). The launchers set `ENABLE_AI` for the chosen mode; other settings, including `STUDIO_MODEL` and `OLLAMA_HOST`, can be customized there.

### Manual setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt       # Lite
# For Full, use: pip install -r requirements-ai.txt
npm --prefix frontend ci
npm --prefix frontend run build
python app.py
```

Set `ENABLE_AI=false` in the environment for Lite mode, or `ENABLE_AI=true` for Full mode. Full mode additionally requires a running Ollama service and the configured local model.

### Running the Test Suite

```bash
python tests/test_suite.py
```

### Launching the development interface

```bash
# Terminal 1: backend
python app.py

# Terminal 2: frontend development server
cd frontend
npm run dev -- --host
```

Open `http://localhost:5173`.

Mobile PWA Bridge (Write on Phone/Tablet)
Ensure your phone and computer are on the same Wi-Fi network.
In Thedral, click the Phone icon in the top navigation bar.
Scan the generated QR code with your iPhone/Android camera.
(iOS Safari): Tap Share ❯ Add to Home Screen for a completely standalone, full-screen writing cockpit.
License & Sovereignty
Thedral is licensed under the GNU Affero General Public License v3 (AGPLv3).
See the LICENSE file for details.
This project was built to ensure that long-form narrative tools remain sovereign, open, and permanently protected from corporate paywalls.