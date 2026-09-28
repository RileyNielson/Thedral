import os
import uuid
import zipfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from backend.config import EXPORTS_DIR
from backend.importer import (
    parse_docx, parse_plaintext, parse_scrivener_project, 
    build_binder_from_manifest, scan_local_manuscripts
)

router = APIRouter(tags=["Importer"])

class LocalPathImport(BaseModel):
    path: str

@router.get("/api/import/discover")
def discover_local_files():
    return scan_local_manuscripts()

@router.post("/api/import/local-path")
def import_local_path(payload: LocalPathImport):
    p = os.path.expanduser(payload.path)
    if not os.path.exists(p):
        raise HTTPException(400, f"Path does not exist: {p}")
        
    title = os.path.splitext(os.path.basename(p.rstrip("/")))[0].replace("_", " ")
    if p.lower().endswith(".scriv") or os.path.isdir(p):
        manifest = parse_scrivener_project(p)
    elif p.lower().endswith((".docx", ".doc")):
        manifest = {"manuscript": parse_docx(p)}
    else:
        manifest = {"manuscript": parse_plaintext(p)}
        
    first_sc = build_binder_from_manifest(manifest, title)
    return {
        "status": "success", 
        "first_scene_id": first_sc,
        "characters_imported": len(manifest.get("characters", [])),
        "lore_imported": len(manifest.get("lore", []))
    }

@router.post("/api/import/upload")
async def import_uploaded_file(file: UploadFile = File(...)):
    filename = file.filename or "Uploaded_Manuscript"
    ext = os.path.splitext(filename)[1].lower()
    temp_dir = str(EXPORTS_DIR)
    temp_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex[:6]}_{filename}")
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        title = os.path.splitext(filename)[0].replace("_", " ")
        if ext in [".docx", ".doc"]:
            manifest = {"manuscript": parse_docx(temp_path)}
        elif ext == ".zip":
            extract_dir = temp_path + "_extracted"
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            scriv_dir = None
            for r, dirs, _ in os.walk(extract_dir):
                for d in dirs:
                    if d.lower().endswith('.scriv'):
                        scriv_dir = os.path.join(r, d)
                        title = os.path.splitext(d)[0]
                        break
                if scriv_dir: 
                    break
            manifest = parse_scrivener_project(scriv_dir) if scriv_dir else {"manuscript": []}
        else:
            manifest = {"manuscript": parse_plaintext(temp_path)}
        
        first_scene_id = build_binder_from_manifest(manifest, title)
        return {"status": "success", "first_scene_id": first_scene_id}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)