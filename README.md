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
2. **Node.js 18+ & npm**
3. **[Ollama](https://ollama.com)** (Optional, for Socratic Mirror & AI Survey)

```bash
# Pull the recommended local 3B model
ollama pull llama3.2:3b
Installation
code
Bash
# 1. Clone the sovereign repository
git clone https://github.com/your-username/Thedral.git
cd Thedral

# 2. Set up Python backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install fastapi uvicorn python-docx pydantic ollama

# 3. Set up Frontend interface
npm install
Running the Test Suite
Thedral ships with an end-to-end integration mega-suite that validates database triggers, FTS5 search, 3D manifold construction, and pacing math:
code
Bash
python tests/test_suite.py
(All 32/32 tests should report [PASS])
Launching the Studio
code
Bash
# Terminal 1: Backend
python app.py

# Terminal 2: Frontend
npm run dev -- --host
Open your browser to: http://localhost:5173
1-Click Launching (macOS)
For distraction-free writing without opening a terminal, double-click Run_Thedral.command in the project root. It will silently boot the backend, start Vite, verify Ollama, and open your studio in your browser.
Mobile PWA Bridge (Write on Phone/Tablet)
Ensure your phone and computer are on the same Wi-Fi network.
In Thedral, click the Phone icon in the top navigation bar.
Scan the generated QR code with your iPhone/Android camera.
(iOS Safari): Tap Share ❯ Add to Home Screen for a completely standalone, full-screen writing cockpit.
License & Sovereignty
Thedral is licensed under the GNU Affero General Public License v3 (AGPLv3).
See the LICENSE file for details.
This project was built to ensure that long-form narrative tools remain sovereign, open, and permanently protected from corporate paywalls.