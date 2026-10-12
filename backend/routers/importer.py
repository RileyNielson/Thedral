import os
import uuid
import zipfile
import shutil
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from backend.config import EXPORTS_DIR
from backend.importer import (
    parse_docx, parse_plaintext, parse_scrivener_project, 
    build_binder_from_manifest, build_import_report, inspect_docx_import, scan_local_manuscripts
)


def _safe_extract_zip(zip_path: str, extract_dir: str) -> None:
    """Extract a zip archive without allowing path traversal or arbitrary writes."""
    os.makedirs(extract_dir, exist_ok=True)
    target_root = os.path.abspath(extract_dir)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = os.path.abspath(os.path.join(target_root, member.filename))
            if os.path.commonpath([target_root, member_path]) != target_root:
                raise ValueError(f"Unsafe archive member: {member.filename}")

            if member.filename.endswith("/"):
                os.makedirs(member_path, exist_ok=True)
                continue

            os.makedirs(os.path.dirname(member_path), exist_ok=True)
            with zip_ref.open(member, "r") as src, open(member_path, "wb") as dst:
                shutil.copyfileobj(src, dst)


def _scrivener_import_warnings(scriv_path: str) -> list[str]:
    media_count = 0
    has_hyperlinks = False
    has_footnotes = False
    for root_dir, _, files in os.walk(scriv_path):
        for name in files:
            extension = os.path.splitext(name)[1].lower()
            if extension in {".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff", ".pdf"}:
                media_count += 1
            if extension == ".rtf":
                with open(os.path.join(root_dir, name), "r", encoding="latin-1") as source:
                    content = source.read().lower()
                has_hyperlinks |= "hyperlink" in content
                has_footnotes |= "\\footnote" in content
    warnings = []
    if media_count:
        warnings.append(f"{media_count} image or PDF attachment(s) were found; they are not imported into the writing editor.")
    if has_hyperlinks:
        warnings.append("Hyperlinks were found; link targets are not preserved in the writing editor.")
    if has_footnotes:
        warnings.append("Footnotes were found; they are not imported into the writing editor.")
    return warnings


router = APIRouter(tags=["Importer"])

class LocalPathImport(BaseModel):
    path: str


def _parse_import(path: str, filename: str):
    ext = os.path.splitext(filename)[1].lower()
    title = os.path.splitext(os.path.basename(filename.rstrip("/")))[0].replace("_", " ")
    warnings = []

    if ext == ".scriv" or os.path.isdir(path):
        manifest = parse_scrivener_project(path)
        warnings.extend(_scrivener_import_warnings(path))
    elif ext in {".docx", ".doc"}:
        manifest = {"manuscript": parse_docx(path)}
        if ext == ".docx":
            warnings.extend(inspect_docx_import(path))
    elif ext == ".zip":
        with tempfile.TemporaryDirectory(prefix="import_extract_", dir=str(EXPORTS_DIR)) as extract_dir:
            _safe_extract_zip(path, extract_dir)
            scriv_dir = None
            for root_dir, _, files in os.walk(extract_dir):
                if any(name.lower().endswith(".scrivx") for name in files):
                    scriv_dir = root_dir
                    break
            if not scriv_dir:
                raise ValueError("No .scrivx project file found inside the ZIP. Ensure you zipped a valid Scrivener project.")
            title = os.path.basename(scriv_dir).replace(".scriv", "").replace("_", " ") or title
            manifest = parse_scrivener_project(scriv_dir)
            warnings.extend(_scrivener_import_warnings(scriv_dir))
    else:
        manifest = {"manuscript": parse_plaintext(path)}

    report = build_import_report(manifest, warnings)
    return manifest, title, report

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
        manifest, title, report = _parse_import(p, p)
        first_sc = build_binder_from_manifest(manifest, title)
        return {
            "status": "success", 
            "first_scene_id": first_sc,
            "characters_imported": len(manifest.get("characters", [])),
            "lore_imported": len(manifest.get("lore", [])),
            "report": report,
        }
    except Exception as e:
        raise HTTPException(400, detail=f"Import Failed: {str(e)}")


@router.post("/api/import/preview/local-path")
def preview_local_path(payload: LocalPathImport):
    p = os.path.expanduser(payload.path)
    if not os.path.exists(p):
        raise HTTPException(400, detail=f"Path does not exist: {p}")
    try:
        _, title, report = _parse_import(p, p)
        return {"title": title, "report": report}
    except Exception as e:
        raise HTTPException(400, detail=f"Import Preview Failed: {str(e)}")

@router.post("/api/import/upload")
async def import_uploaded_file(file: UploadFile = File(...)):
    filename = file.filename or "Uploaded_Manuscript"
    temp_dir = str(EXPORTS_DIR)
    temp_path = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex[:6]}_{os.path.basename(filename)}")
    
    with open(temp_path, "wb") as f:
        f.write(await file.read())

    try:
        manifest, title, report = _parse_import(temp_path, filename)
        first_scene_id = build_binder_from_manifest(manifest, title)
        return {"status": "success", "first_scene_id": first_scene_id, "report": report}
        
    except Exception as e:
        # This properly routes the error message back to the frontend toast popup!
        raise HTTPException(400, detail=f"Upload Failed: {str(e)}")
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/api/import/preview/upload")
async def preview_uploaded_file(file: UploadFile = File(...)):
    filename = file.filename or "Uploaded_Manuscript"
    temp_path = os.path.join(str(EXPORTS_DIR), f"temp_{uuid.uuid4().hex[:6]}_{os.path.basename(filename)}")
    extract_dir = temp_path + "_extracted"
    try:
        with open(temp_path, "wb") as target:
            shutil.copyfileobj(file.file, target)
        _, title, report = _parse_import(temp_path, filename)
        return {"title": title, "report": report}
    except Exception as e:
        raise HTTPException(400, detail=f"Import Preview Failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
