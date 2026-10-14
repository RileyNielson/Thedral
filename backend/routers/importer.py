import os
import uuid
import zipfile
import shutil
import tempfile
from urllib.parse import unquote, urlparse
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


def _clean_user_path(raw: str) -> str:
    """Accept paths as pasted from Finder or dragged into Terminal."""
    value = (raw or "").strip().strip("'\"")
    if value.startswith("file://"):
        value = unquote(urlparse(value).path)
    value = value.replace("\\ ", " ")
    return os.path.expanduser(value)


def _resolve_scrivener_dir(path: str) -> str | None:
    """Return the .scriv folder for a project folder, a .scrivx file, or its parent."""
    if os.path.isfile(path) and path.lower().endswith(".scrivx"):
        return os.path.dirname(path)
    if not os.path.isdir(path):
        return None
    if any(name.lower().endswith(".scrivx") for name in os.listdir(path)):
        return path
    children = [
        os.path.join(path, name) for name in os.listdir(path)
        if name.lower().endswith(".scriv") and os.path.isdir(os.path.join(path, name))
    ]
    return children[0] if len(children) == 1 else None


def _find_scrivener_in_extract(extract_dir: str) -> str | None:
    for root_dir, dirs, files in os.walk(extract_dir):
        dirs[:] = [d for d in dirs if d != "__MACOSX"]
        if any(name.lower().endswith(".scrivx") and not name.startswith("._") for name in files):
            return root_dir
    return None


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


SUPPORTED_TEXT = {".txt", ".md", ".markdown", ".text", ".rtf"}


def _parse_import(path: str, filename: str, uploaded: bool = False):
    ext = os.path.splitext(filename.rstrip("/"))[1].lower()
    title = os.path.splitext(os.path.basename(filename.rstrip("/")))[0].replace("_", " ")
    warnings = []

    scriv_dir = None if uploaded else (_resolve_scrivener_dir(path) if os.path.exists(path) else None)
    if scriv_dir:
        title = os.path.splitext(os.path.basename(scriv_dir))[0].replace("_", " ") or title
        manifest = parse_scrivener_project(scriv_dir)
        warnings.extend(_scrivener_import_warnings(scriv_dir))
    elif os.path.isdir(path) and not uploaded:
        raise ValueError(
            "That folder is not a Scrivener project (no .scrivx file inside). "
            "Choose the .scriv folder itself."
        )
    elif ext == ".scrivx":
        raise ValueError(
            "A Scrivener project is a folder, so its .scrivx file can't be uploaded alone. "
            "Zip the whole .scriv folder and upload the ZIP, or paste the folder path."
        )
    elif ext in {".docx", ".doc"}:
        manifest = {"manuscript": parse_docx(path)}
        if ext == ".docx":
            warnings.extend(inspect_docx_import(path))
    elif ext == ".zip" or (ext == ".scriv" and zipfile.is_zipfile(path)):
        with tempfile.TemporaryDirectory(prefix="import_extract_", dir=str(EXPORTS_DIR)) as extract_dir:
            _safe_extract_zip(path, extract_dir)
            scriv_dir = _find_scrivener_in_extract(extract_dir)
            if not scriv_dir:
                raise ValueError("No .scrivx project file found inside the ZIP. Zip the whole .scriv folder, not just its contents.")
            title = os.path.basename(scriv_dir).replace(".scriv", "").replace("_", " ") or title
            manifest = parse_scrivener_project(scriv_dir)
            warnings.extend(_scrivener_import_warnings(scriv_dir))
    elif ext in SUPPORTED_TEXT or not ext:
        manifest = {"manuscript": parse_plaintext(path) if ext != ".rtf" else _parse_rtf(path)}
    else:
        raise ValueError(
            f"{ext or 'This file type'} isn't supported. Import a .docx, .txt, .md, .rtf, "
            "a Scrivener project folder (.scriv), or a ZIP of one."
        )

    report = build_import_report(manifest, warnings)
    return manifest, title, report


def _parse_rtf(path: str):
    from backend.importer import read_file_content, normalize_paragraphs
    return [(paragraph, False, "", "", "") for paragraph in normalize_paragraphs(read_file_content(path))]


@router.get("/api/import/discover")
def discover_local_files():
    return scan_local_manuscripts(with_status=True)

@router.post("/api/import/local-path")
def import_local_path(payload: LocalPathImport):
    p = _clean_user_path(payload.path)
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
    p = _clean_user_path(payload.path)
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
    
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        manifest, title, report = _parse_import(temp_path, filename, uploaded=True)
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
        _, title, report = _parse_import(temp_path, filename, uploaded=True)
        return {"title": title, "report": report}
    except Exception as e:
        raise HTTPException(400, detail=f"Import Preview Failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
