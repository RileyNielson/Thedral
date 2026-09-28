import sys
import shutil
from pathlib import Path

# 1. Locate the exact backend directory Python is importing from
import backend
backend_dir = Path(backend.__file__).resolve().parent
main_file = backend_dir / "main.py"
routers_dir = backend_dir / "routers"

print(f"📍 Python is importing backend from: {backend_dir}")
print(f"📍 Target main.py: {main_file}")

# 2. Check if the router files exist
if not routers_dir.exists():
    print("❌ ERROR: backend/routers directory does not exist!")
    sys.exit(1)

router_files = [f.name for f in routers_dir.glob("*.py")]
print(f"📁 Router files found ({len(router_files)}): {router_files}")

# 3. Write the authoritative main.py directly to disk
new_main_code = """import os
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
    clean_q = re.sub(r'[^\\w\\s]', '', q) + '*'
    c.execute(\"\"\"
        SELECT f.node_id, f.title, snippet(binder_fts, 2, '<b>', '</b>', '...', 15) as snippet, b.node_type
        FROM binder_fts f
        JOIN binder_nodes b ON f.node_id = b.id
        WHERE binder_fts MATCH ?
        LIMIT 25
    \"\"\", (clean_q,))
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
"""

main_file.write_text(new_main_code, encoding="utf-8")
print(f"✍️ Successfully wrote {len(new_main_code)} bytes to {main_file}")

# 4. Remove stale bytecode files
for pyc in backend_dir.rglob("*.pyc"):
    try:
        pyc.unlink()
    except Exception:
        pass

# 5. Reload and inspect routes
if "backend.main" in sys.modules:
    del sys.modules["backend.main"]
import backend.main

count = len(backend.main.app.routes)
print(f"🔢 Total mounted routes: {count}")

assert count >= 20, f"Expected >= 20 routes, but got {count}"
print("🎉 Success! Master server verified with all domain routers active.")
