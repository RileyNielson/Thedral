import re
from backend.text_utils import html_to_text
from backend.importing.structure import is_scene_divider

def build_import_report(manifest: dict, warnings: list[str] | None = None) -> dict:
    tuples = manifest.get("manuscript", [])
    scene_titles = [item for item in tuples if item[0].startswith("### SCENE_TITLE: ")]
    outline_only = 0
    scene_count = 0
    scene_open = False
    synopses = 0
    notes = 0
    prose_count = 0
    for position, item in enumerate(tuples):
        text = item[0]
        is_scene_title = text.startswith("### SCENE_TITLE: ")
        is_chapter = text.startswith("Chapter: ")
        synopsis = item[3].strip() if len(item) > 3 and isinstance(item[3], str) else ""
        note = item[4].strip() if len(item) > 4 and isinstance(item[4], str) else ""
        if is_scene_title or is_chapter:
            synopses += bool(synopsis)
            notes += bool(note)
        if is_chapter:
            scene_open = False
            continue
        if is_scene_title:
            scene_count += 1
            scene_open = True
        elif is_scene_divider(text):
            scene_open = False
        elif text.strip():
            prose_count += 1
            if not scene_open:
                scene_count += 1
                scene_open = True

    scene_count = max(len(scene_titles), scene_count)
    for position, item in enumerate(tuples):
        if not item[0].startswith("### SCENE_TITLE: "):
            continue
        has_prose = False
        for entry in tuples[position + 1:]:
            if entry[0].startswith(("### SCENE_TITLE: ", "Chapter: ")):
                break
            if not is_scene_divider(entry[0]) and entry[0].strip():
                has_prose = True
                break
        if not has_prose:
            outline_only += 1
    paragraphs = [
        item[0] for item in tuples
        if not item[0].startswith(("### SCENE_TITLE: ", "Chapter: "))
        and not is_scene_divider(item[0])
    ]
    formatted_count = sum(
        1 for paragraph in paragraphs
        if re.search(r"</?(?:strong|em)>", paragraph, re.IGNORECASE)
    )
    word_count = len(html_to_text("\n".join(paragraphs)).split())
    report_warnings = list(warnings or [])
    report_warnings.extend(manifest.get("import_warnings", []))
    return {
        "chapters": sum(item[0].startswith("Chapter: ") for item in tuples),
        "scenes": scene_count,
        "outline_only": outline_only,
        "paragraphs": len(paragraphs),
        "words": word_count,
        "formatted_paragraphs": formatted_count,
        "characters": len(manifest.get("characters", [])),
        "locations": len(manifest.get("locations", [])),
        "lore": len(manifest.get("lore", [])),
        "synopses": synopses,
        "notes": notes,
        "warnings": list(dict.fromkeys(report_warnings)),
    }

