import os
import re
import time
from config import TARGET_DIR, WORKSPACE_DIR

EXCLUDED_DIR_NAMES = {'venv', '.venv', 'env', 'site-packages', '__pycache__', 'fonts', 'assets', 'images', 'covers', 'audio', 'settings', 'snapshots', 'quicklook', 'library', 'temp', 'node_modules', '.git', '.trash', 'trash'}

def natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def is_junk_or_temporary(filename: str) -> bool:
    fl = filename.lower()
    return fl.startswith(('~$', '._', '.ds_store', 'thumbs.db')) or fl.endswith(('.tmp', '.bak', '.autosave'))

def scan_bookshelf(search_query: str = "") -> list:
    scan_root = TARGET_DIR
    results = []
    if not os.path.exists(scan_root): return []
    real_workspace = os.path.realpath(WORKSPACE_DIR).lower()
    for root, dirs, files in os.walk(scan_root, topdown=True):
        real_root = os.path.realpath(root).lower()
        if real_root == real_workspace or real_root.startswith(real_workspace + os.sep):
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in EXCLUDED_DIR_NAMES]
        for sd in [d for d in dirs if d.lower().endswith('.scriv')]:
            abs_p = os.path.join(root, sd)
            rel_p = os.path.relpath(abs_p, scan_root)
            if not search_query or search_query.lower() in rel_p.lower():
                results.append(('📚 SCRIVENER', rel_p, abs_p))
            dirs.remove(sd)
        for f in files:
            if is_junk_or_temporary(f): continue
            fl = f.lower()
            abs_p = os.path.join(root, f)
            rel_p = os.path.relpath(abs_p, scan_root)
            if search_query and search_query.lower() not in rel_p.lower(): continue
            if fl.endswith(('.docx', '.doc')): results.append(('📄 DOCX', rel_p, abs_p))
            elif fl.endswith(('.md', '.markdown')): results.append(('📝 MARKDOWN', rel_p, abs_p))
            elif fl.endswith('.txt') and not fl.startswith('requirements'): results.append(('📄 TEXT', rel_p, abs_p))
    results.sort(key=lambda item: natural_sort_key(item[1]))
    return results

def get_file_metadata(abs_path: str) -> dict:
    if not os.path.exists(abs_path): return {}
    stat = os.stat(abs_path)
    mod_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
    total_size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(abs_path) for f in fs) if os.path.isdir(abs_path) else stat.st_size
    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1048576 else f"{total_size / 1048576:.1f} MB"
    return {"modified": mod_time, "size": size_str, "basename": os.path.basename(abs_path)}
