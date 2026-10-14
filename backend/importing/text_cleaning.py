import os
import re
import sys
import html
import subprocess

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\x0b', '\n').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[\x00-\x08\x0e-\x1f]', '', text)
    return text.strip()

def strip_rtf_native(rtf_text: str, preserve_formatting: bool = False) -> str:
    """
    Cross-Platform RTF Stripper for Windows and Linux:
    Removes RTF formatting while decoding common ANSI and Unicode escapes.
    """
    if not rtf_text:
        return ""

    codepage_match = re.search(r'\\ansicpg(\d+)', rtf_text)
    encoding = f"cp{codepage_match.group(1)}" if codepage_match else "cp1252"
    output = []
    group_stack = []
    skip_group = False
    bold = False
    italic = False
    unicode_fallback_count = 1
    fallback_remaining = 0
    pending_high_surrogate = None
    index = 0

    def emit(text):
        if text:
            output.append((text, bold, italic))

    def append_unicode_unit(unit):
        nonlocal pending_high_surrogate
        if 0xD800 <= unit <= 0xDBFF:
            if pending_high_surrogate is not None:
                emit("\ufffd")
            pending_high_surrogate = unit
        elif 0xDC00 <= unit <= 0xDFFF and pending_high_surrogate is not None:
            emit(chr(0x10000 + ((pending_high_surrogate - 0xD800) << 10) + unit - 0xDC00))
            pending_high_surrogate = None
        else:
            if pending_high_surrogate is not None:
                emit("\ufffd")
                pending_high_surrogate = None
            emit(chr(unit))

    while index < len(rtf_text):
        char = rtf_text[index]
        if char == "{":
            prefix = rtf_text[index + 1:index + 80]
            destination = re.match(
                r"\\(?:\*\\)?([a-zA-Z]+)",
                prefix
            )
            destination_name = destination.group(1).lower() if destination else ""
            known_destinations = {
                "fonttbl", "colortbl", "stylesheet", "info", "pict", "object",
                "header", "headerl", "headerr", "footer", "footerl", "footerr",
                "footnote", "annotation", "datastore", "themedata",
                "colorschememapping",
            }
            starred_match = re.match(r"\\\*\\([a-zA-Z]+)", prefix)
            is_unknown_starred_destination = bool(starred_match and starred_match.group(1).lower() not in known_destinations)
            group_stack.append((skip_group, unicode_fallback_count, bold, italic))
            skip_group = skip_group or destination_name in known_destinations or is_unknown_starred_destination
            index += 1
            continue
        if char == "}":
            if group_stack:
                skip_group, unicode_fallback_count, bold, italic = group_stack.pop()
            index += 1
            continue
        if char != "\\":
            if fallback_remaining:
                fallback_remaining -= 1
            elif not skip_group:
                emit(char)
            index += 1
            continue

        index += 1
        if index >= len(rtf_text):
            break
        symbol = rtf_text[index]
        if symbol in "\\{}":
            if fallback_remaining:
                fallback_remaining -= 1
            elif not skip_group:
                emit(symbol)
            index += 1
            continue
        if symbol == "'":
            match = re.match(r"'([0-9a-fA-F]{2})", rtf_text[index:])
            if match:
                if fallback_remaining:
                    fallback_remaining -= 1
                elif not skip_group:
                    try:
                        emit(bytes.fromhex(match.group(1)).decode(encoding, errors="replace"))
                    except LookupError:
                        emit(bytes.fromhex(match.group(1)).decode("cp1252", errors="replace"))
                index += len(match.group(0))
            else:
                index += 1
            continue
        if not symbol.isalpha():
            if not skip_group and not fallback_remaining:
                emit({"~": "\u00a0", "_": "\u2011", "-": ""}.get(symbol, ""))
            elif fallback_remaining:
                fallback_remaining -= 1
            index += 1
            continue

        start = index
        while index < len(rtf_text) and rtf_text[index].isalpha():
            index += 1
        word = rtf_text[start:index].lower()
        number_match = re.match(r"-?\d+", rtf_text[index:])
        number = int(number_match.group(0)) if number_match else None
        if number_match:
            index += len(number_match.group(0))
        if index < len(rtf_text) and rtf_text[index] == " ":
            index += 1

        if word == "uc" and number is not None:
            unicode_fallback_count = max(0, number)
        elif word == "u" and number is not None:
            if not skip_group and not fallback_remaining:
                append_unicode_unit(number if number >= 0 else number + 65536)
            fallback_remaining = unicode_fallback_count
        elif word == "b":
            bold = number != 0
        elif word == "i":
            italic = number != 0
        elif word in ("par", "line") and not skip_group:
            emit("\n")
        elif word == "tab" and not skip_group:
            emit("\t")
        elif word in ("emdash", "endash", "lquote", "rquote", "ldblquote", "rdblquote") and not skip_group:
            emit({
                "emdash": "\u2014", "endash": "\u2013", "lquote": "\u2018",
                "rquote": "\u2019", "ldblquote": "\u201c", "rdblquote": "\u201d",
            }[word])
        elif word == "bin" and number is not None:
            index += max(0, number)

    if pending_high_surrogate is not None:
        emit("\ufffd")

    if not preserve_formatting:
        return sanitize_text("".join(text for text, _, _ in output))

    paragraphs = [[]]
    for text, token_bold, token_italic in output:
        fragments = text.split("\n")
        for fragment_index, fragment in enumerate(fragments):
            if fragment:
                paragraphs[-1].append((fragment, token_bold, token_italic))
            if fragment_index < len(fragments) - 1:
                paragraphs.append([])

    rendered_paragraphs = []
    for paragraph in paragraphs:
        runs = []
        for text, token_bold, token_italic in paragraph:
            if runs and runs[-1][1:] == (token_bold, token_italic):
                runs[-1] = (runs[-1][0] + text, token_bold, token_italic)
            else:
                runs.append((text, token_bold, token_italic))
        rendered = []
        for text, token_bold, token_italic in runs:
            escaped = html.escape(text, quote=False)
            if token_bold and token_italic:
                escaped = f"<strong><em>{escaped}</em></strong>"
            elif token_bold:
                escaped = f"<strong>{escaped}</strong>"
            elif token_italic:
                escaped = f"<em>{escaped}</em>"
            rendered.append(escaped)
        rendered_paragraphs.append("".join(rendered))
    return "\n\n".join(rendered_paragraphs).strip()

def read_file_content(fp: str, preserve_formatting: bool = False) -> str:
    """Reads RTF, TXT, or MD files across macOS, Windows 10, and Linux."""
    if not fp or not os.path.exists(fp):
        return ""
    if fp.lower().endswith('.rtf'):
        if preserve_formatting:
            with open(fp, 'r', encoding='utf-8', errors='replace') as f:
                return strip_rtf_native(f.read(), preserve_formatting=True)
        if sys.platform == 'darwin':
            try:
                res = subprocess.run(['textutil', '-convert', 'txt', fp, '-stdout'], capture_output=True, text=True)
                if res.returncode == 0 and res.stdout:
                    return res.stdout
            except OSError:
                pass
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            return strip_rtf_native(f.read())

    if fp.lower().endswith(('.txt', '.md')):
        with open(fp, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    return ""

def _is_hard_wrapped(lines: list[str]) -> bool:
    """Plain-text files wrap lines at a fixed width; a real paragraph break is a newline after a finished sentence."""
    if len(lines) < 3:
        return False
    lengths = sorted(len(line.strip()) for line in lines)
    if lengths[len(lengths) // 2] > 90:
        return False
    open_ends = sum(1 for line in lines[:-1] if not re.search(r'[.!?:"\u201d\u2019)\]*_]$', line.strip()))
    return open_ends >= max(1, (len(lines) - 1) // 3)


def normalize_paragraphs(raw_text: str) -> list[str]:
    cleaned = sanitize_text(raw_text)
    if not cleaned:
        return []
    paragraphs = []
    for block in re.split(r'\n{2,}', cleaned):
        lines = [line for line in block.split("\n") if line.strip()]
        if _is_hard_wrapped(lines):
            lines = [" ".join(line.strip() for line in lines)]
        for c in lines:
            p = re.sub(r'^[ \t]+', '', c).strip()
            if p and not p.startswith("{\\rtf"):
                paragraphs.append(p)
    return paragraphs

def _safe_inline_markup(value: str) -> str:
    pieces = re.split(r"(<\/?(?:strong|em)>)", value, flags=re.IGNORECASE)
    return "".join(
        piece if re.fullmatch(r"<\/?(?:strong|em)>", piece, flags=re.IGNORECASE)
        else html.escape(html.unescape(piece), quote=False)
        for piece in pieces
    )

