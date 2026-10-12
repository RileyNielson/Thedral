from html.parser import HTMLParser
import re


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = [[]]
        self.bold = False
        self.italic = False

    def _new_paragraph(self):
        if self.paragraphs[-1]:
            self.paragraphs.append([])

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._new_paragraph()
        elif tag == "br":
            self._append("\n")
        elif tag in {"strong", "b"}:
            self.bold = True
        elif tag in {"em", "i"}:
            self.italic = True

    def handle_endtag(self, tag):
        if tag in {"p", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self._new_paragraph()
        elif tag in {"strong", "b"}:
            self.bold = False
        elif tag in {"em", "i"}:
            self.italic = False

    def handle_data(self, data):
        self._append(data)

    def _append(self, text):
        if not text:
            return
        runs = self.paragraphs[-1]
        if runs and runs[-1][1:] == (self.bold, self.italic):
            runs[-1] = (runs[-1][0] + text, self.bold, self.italic)
        else:
            runs.append((text, self.bold, self.italic))


def html_to_formatted_paragraphs(value: str) -> list[list[tuple[str, bool, bool]]]:
    if not re.search(r"<\/?(?:p|div|strong|b|em|i|br|ul|ol|li|blockquote|h[1-6])\b", value or "", re.IGNORECASE):
        return [
            [(paragraph, False, False)]
            for paragraph in re.split(r"\n{2,}", value or "")
            if paragraph.strip()
        ]
    parser = _TextExtractor()
    parser.feed(value or "")
    parser.close()
    return [paragraph for paragraph in parser.paragraphs if paragraph]


def html_to_text(value: str) -> str:
    if not value:
        return ""
    paragraphs = html_to_formatted_paragraphs(value)
    return "\n\n".join(
        " ".join("".join(text for text, _, _ in paragraph).split())
        for paragraph in paragraphs
    )
