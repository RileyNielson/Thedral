"""Compatibility facade: the import pipeline now lives in backend/importing/, one concern per module."""
from backend.importing.text_cleaning import sanitize_text, strip_rtf_native, read_file_content, normalize_paragraphs, _safe_inline_markup
from backend.importing.structure import is_chapter_heading, is_scene_divider, derive_smart_scene_title
from backend.importing.documents import parse_docx, inspect_docx_import
from backend.importing.report import build_import_report
from backend.importing.plaintext import parse_plaintext
from backend.importing.scrivener import parse_scrivener_project
from backend.importing.binder_builder import build_binder_from_manifest
from backend.importing.discovery import scan_local_manuscripts, _looks_like_manuscript, _scan_manuscript_folder
