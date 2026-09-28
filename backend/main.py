import os
import re
import socket
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import STATIC_DIR
from backend.database import get_db
from backend.models import init_db

# Import all 6 modular domain routers
from backend.routers.binder import router as binder_router
from backend.routers.craft import router as craft_router
from backend.routers.narrative import router as narrative_router
from backend.routers.entities import router as entities_router
from backend.routers.importer import router as importer_router
from backend.routers.publishing import router as publishing_router
from backend.routers.lore import router as lore_router

app = FastAPI(title="Thedral Studio Core", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# Mount all 6 modular domain routers
app.include_router(binder_router)
app.include_router(craft_router)
app.include_router(narrative_router)
app.include_router(entities_router)
app.include_router(importer_router)
app.include_router(publishing_router)
app.include_router(lore_router)

@app.get("/api/network_info")
def get_network_info():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = "localhost"
    return {"local_ip": ip, "port": 8000, "url": f"http://{ip}:8000"}

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

static_path = str(STATIC_DIR)
os.makedirs(static_path, exist_ok=True)

@app.get("/")
def serve_index():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "Thedral Studio Backend Online."}

app.mount("/static", StaticFiles(directory=static_path), name="static")
