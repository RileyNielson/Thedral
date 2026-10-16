import os
import re
import socket
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import STATIC_DIR, ENABLE_AI, STUDIO_MODEL, PORT
from backend.database import get_db
from backend.models import init_db

allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

# Import all modular domain routers
from backend.routers.binder import router as binder_router
from backend.routers.analytics import router as analytics_router
from backend.routers.binder_tools import router as binder_tools_router
from backend.routers.craft import router as craft_router
from backend.routers.reader_simulation import router as reader_simulation_router
from backend.routers.reader_feedback import router as reader_feedback_router
from backend.routers.narrative import router as narrative_router
from backend.routers.entities import router as entities_router
from backend.routers.importer import router as importer_router
from backend.routers.publishing import router as publishing_router
from backend.routers.lore import router as lore_router
from backend.routers.story_shape import router as story_shape_router

app = FastAPI(title="Thedral Studio Core", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Mount all modular domain routers
app.include_router(binder_router)
app.include_router(analytics_router)
app.include_router(story_shape_router)
app.include_router(binder_tools_router)
app.include_router(craft_router)
app.include_router(reader_simulation_router)
app.include_router(reader_feedback_router)
app.include_router(narrative_router)
app.include_router(entities_router)
app.include_router(importer_router)
app.include_router(publishing_router)
app.include_router(lore_router)

@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "app": "Thedral Studio",
        "mode": "FULL" if ENABLE_AI else "LITE",
        "ai_enabled": ENABLE_AI,
        "model": STUDIO_MODEL if ENABLE_AI else None,
    }

@app.get("/api/network_info")
def get_network_info():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "localhost"
    return {"local_ip": ip, "port": PORT, "url": f"http://{ip}:{PORT}"}

@app.get("/api/search")
def search_manuscript(q: str):
    if not q or len(q.strip()) < 2:
        return []
    conn = get_db()
    c = conn.cursor()
    clean_q = re.sub(r'[^\w\s]', '', q) + '*'
    c.execute("""
        SELECT f.node_id, f.title, snippet(binder_fts, 2, '<b>', '</b>', '...', 15) as snippet, b.node_type
        FROM binder_fts f
        JOIN binder_nodes b ON f.node_id = b.id
        WHERE binder_fts MATCH ?
        LIMIT 25
    """, (clean_q,))
    results = [dict(r) for r in c.fetchall()]
    conn.close()
    return results

# =============================================================================
# FRONTEND SPA MOUNTING (Compiled Vue/Vite App)
# =============================================================================

# Resolve the absolute path to the compiled frontend/dist directory
BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "frontend" / "dist"

@app.get("/")
def serve_index():
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "Thedral Studio Backend Online. Run 'npm run build' inside frontend/ to see interface."}

# Mount Vite's compiled assets folder (/assets/js, /assets/css)
assets_dir = DIST_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# Catch-all to serve any other static files in the root (like favicon.ico)
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=DIST_DIR, html=False), name="dist_root")
