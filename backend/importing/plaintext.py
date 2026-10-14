from backend.importing.text_cleaning import normalize_paragraphs
from backend.importing.structure import is_chapter_heading, is_scene_divider

def parse_plaintext(fpath: str) -> list[tuple[str, bool, str, str, str]]:
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
        output = []
        for p in normalize_paragraphs(content):
            is_ch, ch_title = is_chapter_heading(p)
            if is_ch:
                output.append((f"Chapter: {ch_title}", True, ch_title, "", ""))
            elif is_scene_divider(p):
                output.append(("* * *", False, "", "", ""))
            else:
                output.append((p, False, "", "", ""))
        return output

