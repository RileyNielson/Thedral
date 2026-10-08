import os
from pathlib import Path

# =============================================================================
# 1. BASE DIRECTORY & FILE PATHS
# =============================================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
STATIC_DIR = PROJECT_ROOT / "static"
EXPORTS_DIR = PROJECT_ROOT / "exports"
DB_PATH = PROJECT_ROOT / "studio_vault.db"

# Ensure required runtime directories exist on disk
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# =============================================================================
# 2. LOCAL AI & SOVEREIGN PURE MATH SWITCH
# =============================================================================

# Set ENABLE_AI=false in .env to disable all LLM features completely
ENABLE_AI = os.environ.get("ENABLE_AI", "true").lower() in ("true", "1", "yes")

STUDIO_MODEL = os.environ.get("STUDIO_MODEL", "llama3.2:3b")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

LLM_OPTIONS = {
    "num_ctx": 8192,
    "temperature": 0.25,
    "top_p": 0.9,
}

# =============================================================================
# 3. STUDIO NETWORK & HOST SETTINGS
# =============================================================================

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))

# =============================================================================
# 4. MASTER CRAFT & TELEMETRY LEXICONS
# =============================================================================

FILTER_VERBS = [
    "saw", "heard", "felt", "noticed", "watched", 
    "wondered", "realized", "seemed", "appeared", 
    "decided", "noted", "looked", "sounded"
]

CRUTCH_WORDS = [
    "suddenly", "glanced", "nodded", "frowned", "slightly", 
    "almost", "began to", "just", "really", "very", 
    "a bit", "shrugged", "sighed", "turned"
]

TENSION_KEYWORDS = [
    "blood", "blade", "death", "kill", "fire", "screamed", "gun",
    "shout", "danger", "run", "breath", "clutched", "strike",
    "shadow", "terror", "betrayal", "poison", "iron", "dark",
    "lethal", "frozen", "collapse", "ruin", "urgent", "blast"
]

COMMON_ANACHRONISMS = [
    "at the end of the day", "process my feelings", "process his feelings", "process her feelings",
    "toxic relationship", "red flag", "bandwidth", "unpack that", "trauma bond",
    "on the same page", "reach out", "circle back", "touch base", "game changer",
    "micro-manage", "coping mechanism", "passive aggressive", "narcissist"
]