import os
import re

_SCAN_SKIP_DIRS = {
    'venv', '.venv', 'site-packages', 'temp', 'tmp', 'node_modules', '.git', 'library',
    'microsoft user data', 'my games', 'custom office templates', 'templates', 'backups',
    'applications', 'cache', 'caches', '__macosx',
}
_SCAN_SKIP_SUFFIXES = (
    '.app', '.photoslibrary', '.xcodeproj', '.framework', '.bundle', '.pages', '.numbers',
    '.key', '.lproj', '.imovielibrary', '.fcpbundle', '.band', '.sparsebundle',
)
_SCAN_SKIP_NAME_WORDS = {
    'resume', 'cv', 'invoice', 'receipt', 'template', 'syllabus', 'agenda', 'minutes',
    'contract', 'lease', 'tax', 'statement', 'form', 'readme', 'license', 'schedule', 'budget',
    'worksheet', 'homework', 'assignment', 'flyer', 'menu', 'itinerary', 'application',
}
_MIN_DOCX_BYTES = 12 * 1024
_MIN_TEXT_BYTES = 30 * 1024
_TEXT_EXTENSIONS = ('.rtf', '.txt', '.md')
_CLOUD_FOLDERS = (
    ("Library", "Mobile Documents", "com~apple~CloudDocs"),
    ("Dropbox",), ("OneDrive",), ("Google Drive",), ("Library", "CloudStorage"),
)
_MAX_SCAN_DEPTH = 5


def scan_local_manuscripts(with_status: bool = False):
    """Find Scrivener projects (best signal) and and substantial .docx/.rtf/.txt/.md files that look like manuscripts."""
    found = []
    folders = []
    home = os.path.expanduser("~")
    roots = [(name,) for name in ("Documents", "Desktop", "Downloads")] + list(_CLOUD_FOLDERS)
    for parts in roots:
        folder = os.path.join(home, *parts)
        if parts in _CLOUD_FOLDERS and not os.path.isdir(folder):
            continue
        status = {"folder": folder, "exists": os.path.isdir(folder), "readable": False}
        if status["exists"]:
            try:
                os.listdir(folder)
                status["readable"] = True
            except OSError:
                pass
        folders.append(status)
        if status["readable"]:
            found.extend(_scan_manuscript_folder(folder, home, _SCAN_SKIP_DIRS))
    order = {"SCRIVENER": 0, "DOCX": 1, "TEXT": 2}
    seen, unique = set(), []
    for item in found:
        if item["path"] not in seen:
            seen.add(item["path"])
            unique.append(item)
    found = sorted(unique, key=lambda x: (order.get(x["type"], 3), -x.get("size", 0), x["title"].lower()))[:60]
    
    return {"items": found, "folders": folders} if with_status else found


def _looks_like_manuscript(filename: str, size: int, minimum: int = _MIN_DOCX_BYTES) -> bool:
    if size < minimum:
        return False
    words = set(re.findall(r"[a-z]+", filename.lower()))
    return not (words & _SCAN_SKIP_NAME_WORDS)


def _scan_manuscript_folder(docs_dir: str, home: str, ignored: set[str]) -> list[dict]:
    found = []
    base_depth = docs_dir.rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(docs_dir, onerror=lambda e: None):
        depth = root.rstrip(os.sep).count(os.sep) - base_depth
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and d.lower() not in ignored
            and (d.lower().endswith('.scriv') or not d.lower().endswith(_SCAN_SKIP_SUFFIXES))
        ]
        if depth >= _MAX_SCAN_DEPTH:
            dirs[:] = [d for d in dirs if d.lower().endswith('.scriv')]

        for d in list(dirs):
            if d.lower().endswith('.scriv'):
                abs_p = os.path.join(root, d)
                try:
                    has_project = any(n.lower().endswith('.scrivx') for n in os.listdir(abs_p))
                except OSError:
                    has_project = False
                if has_project:
                    found.append({
                        "type": "SCRIVENER",
                        "title": os.path.splitext(d)[0],
                        "path": abs_p,
                        "rel_path": os.path.relpath(abs_p, home)
                    })
                dirs.remove(d)

        for f in files:
            lower = f.lower()
            if lower.endswith(_TEXT_EXTENSIONS) and not f.startswith(('~$', '.')):
                abs_p = os.path.join(root, f)
                try:
                    size = os.path.getsize(abs_p)
                except OSError:
                    continue
                if _looks_like_manuscript(f, size, _MIN_TEXT_BYTES):
                    found.append({
                        "type": "TEXT",
                        "title": os.path.splitext(f)[0].replace("_", " "),
                        "path": abs_p,
                        "rel_path": os.path.relpath(abs_p, home),
                        "size": size,
                    })
                continue
            if lower.endswith('.docx') and not f.startswith(('~$', '.')):
                abs_p = os.path.join(root, f)
                try:
                    size = os.path.getsize(abs_p)
                except OSError:
                    continue
                if not _looks_like_manuscript(f, size):
                    continue
                found.append({
                    "type": "DOCX",
                    "title": os.path.splitext(f)[0].replace("_", " "),
                    "path": abs_p,
                    "rel_path": os.path.relpath(abs_p, home),
                    "size": size,
                })

    return found

