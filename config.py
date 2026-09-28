import os
import json

STUDIO_MODEL = "llama3.1:8b"
LLM_OPTIONS = {"num_ctx": 8192, "temperature": 0.25, "top_p": 0.9}

DOCS_DIR = os.path.expanduser("~/Documents")
TARGET_DIR = None
for candidate in ["Victorian Skies", "Victorian skies", "victorian skies"]:
    p = os.path.join(DOCS_DIR, candidate)
    if os.path.exists(p):
        TARGET_DIR = p
        break

if not TARGET_DIR:
    TARGET_DIR = os.path.join(DOCS_DIR, "Victorian Skies")

WORKSPACE_DIR = os.path.join(TARGET_DIR, "_Studio_Workspace")
DB_PATH = os.path.join(WORKSPACE_DIR, "Database", "manuscript.db")
MIRROR_DIR = os.path.join(WORKSPACE_DIR, "Manuscript_Mirror")
EXPORTS_DIR = os.path.join(WORKSPACE_DIR, "Exports")

STUDIO_ROOT = os.path.expanduser("~/Developer/ManuscriptStudio")
AUTH_FILE = os.path.join(STUDIO_ROOT, "authorized_user.txt")
SESSION_FILE = os.path.join(STUDIO_ROOT, "active_session.json")

for folder in [os.path.dirname(DB_PATH), MIRROR_DIR, EXPORTS_DIR, STUDIO_ROOT]:
    os.makedirs(folder, exist_ok=True)

DEFAULT_SESSION = {
    "is_locked": False,
    "book_title": "None",
    "book_id": "ACTIVE_BOOK",
    "series": "Victorian Skies",
    "book_num": 1,
    "active_chapter": 1,
    "active_para": None,
    "mode": "IDLE",
    "file": "",
    "total_words": 0,
    "total_paras": 0
}

def load_session() -> dict:
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return {**DEFAULT_SESSION, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SESSION.copy()

def save_session(session_data: dict):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save session: {e}")

ACTIVE_CONTEXT = load_session()
