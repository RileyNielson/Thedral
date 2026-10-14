import re

def is_chapter_heading(text: str, is_heading_style: bool = False, is_bold: bool = False) -> tuple[bool, str]:
    t = text.strip()
    if not t or len(t) > 85:
        return False, ""
    
    clean = re.sub(r"[\*#_~]", "", t).strip()
    clean_lower = clean.lower()

    if clean.isdigit() and int(clean) < 150:
        return True, f"Chapter {clean}"
    if re.match(r"^(?:[IVXLCDM]+)\.?$", clean, re.IGNORECASE) and len(clean) <= 6:
        return True, f"Chapter {clean.upper()}"

    words = ["one","two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen","eighteen","nineteen","twenty"]
    if clean_lower in words:
        return True, f"Chapter {clean.title()}"

    match = re.match(r"^(?:chapter|act|part|prologue|epilogue|interlude|book)\b(?:\s+[\w\d]+)?(?:\s*[:\-–—]\s*(.*))?$", clean, re.I)
    if match:
        return True, clean

    if (is_heading_style or is_bold) and len(clean) < 55:
        if not clean.endswith(('.', '!', '?')) and len(clean.split()) <= 7:
            return True, clean

    return False, ""

def is_scene_divider(text: str) -> bool:
    t = text.strip()
    return bool(re.match(r"^(?:(?:\*\s*){3,}|(?:#\s*){3,}|(?:~\s*){3,}|(?:•\s*){3,}|-{3,})$", t))

def derive_smart_scene_title(first_para: str, sc_num: int, ch_title: str, custom_title: str | None = None) -> str:
    if custom_title and custom_title.strip() and not custom_title.lower().startswith(("scene ", "untitled")):
        return custom_title.strip()
    sub_match = re.search(r"[:\-–—]\s*(.+)$", ch_title)
    if sc_num == 1 and sub_match:
        return sub_match.group(1).strip()
    if first_para:
        first_sentence = re.split(r'[.!?]', first_para)[0].strip()
        words = first_sentence.split()
        if len(words) >= 2:
            candidate = " ".join(words[:5]).strip('.,;:"!?')
            candidate = re.sub(r'^(and|but|then|so|because|when|the|a|an)\s+', '', candidate, flags=re.I)
            if len(candidate) > 3:
                return candidate.title()
    return f"Scene {sc_num}"

