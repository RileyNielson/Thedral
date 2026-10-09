import os
import uuid
import zipfile
import shutil
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
        raise HTTPException(400, detail=f"Path does not exist: {p}")
        
    title = os.path.splitext(os.path.basename(p.rstrip("/")))[0].replace("_", " ")
    try:
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
    except Exception as e:
        raise HTTPException(400, detail=f"Import Failed: {str(e)}")

@router.post("/api/import/upload")
async def import_uploaded_file(file: UploadFile = File(...)):
    filename = file.filename or "Uploaded_Manuscript"
    ext = os.path.splitext(filename)[1].lower()
    temp_dir = str(EXPORTS_DIR)
    temp_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex[:6]}_{filename}")
    extract_dir = temp_path + "_extracted"
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        title = os.path.splitext(filename)[0].replace("_", " ")
        
        if ext in [".docx", ".doc"]:
            manifest = {"manuscript": parse_docx(temp_path)}
            
        elif ext == ".zip":
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            scriv_dir = None
            
            # SMART WINDOWS ZIP DISCOVERY:
            # Look for the .scrivx file anywhere inside the extracted zip.
            for root_dir, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith('.scrivx'):
                        scriv_dir = root_dir
                        # If it's inside a folder, use that folder's name as the book title
                        if root_dir != extract_dir:
                            title = os.path.basename(root_dir).replace(".scriv", "").replace("_", " ")
                        break
                if scriv_dir:
                    break
                    
            if not scriv_dir:
                raise ValueError("No .scrivx project file found inside the ZIP. Ensure you zipped a valid Scrivener project.")
                
            manifest = parse_scrivener_project(scriv_dir)
            
        else:
            manifest = {"manuscript": parse_plaintext(temp_path)}
        
        first_scene_id = build_binder_from_manifest(manifest, title)
        return {"status": "success", "first_scene_id": first_scene_id}
        
    except Exception as e:
        # This properly routes the error message back to the frontend toast popup!
        raise HTTPException(400, detail=f"Upload Failed: {str(e)}")
        
    finally:
        # Clean up the temp files so we don't bloat the hard drive
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        if os.path.exists(extract_dir):
            try:
                shutil.rmtree(extract_dir)
            except:
                pass
