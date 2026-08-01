"""Markdown -> Ed lesson document XML (the subset our writeups use).

Supported:
- # ## ### headings (Ed heading levels 1-3); #### and deeper have no Ed
  heading, so they become a bold paragraph (matches VS Code's visual
  fallback).
- paragraphs; - bullet and 1. numbered lists; | tables |.
- ``` fenced code blocks: with a language tag (```java) they become Ed
  code SNIPPETS (line numbers on). Runnable is AUTO-DETECTED: any java
  snippet containing a main method (`void main(` — classic or compact)
  gets the Run button. Force with ```java runnable / ```java norun.
  Bare ``` fences stay <pre> (terminal transcripts etc.).
- inline `code`, **bold**, *italic* and _italic_ (outside code spans),
  [text](url) links.
- ![alt](path-or-url) images -> <figure><image/>. Local paths are
  uploaded to Ed via the image_uploader callback (see ed_api.upload_file);
  http(s) URLs pass through. Without a callback, local images raise.
- --- / ---- horizontal rules: Ed's document schema has NO rule element
  (verified against pulled slides), so they become an empty spacer
  paragraph.

The output dialect is the one round-tripped from real Ed slides:
document/heading/paragraph/pre+break/snippet+snippet-file/list+list-item/
table+table-row+table-cell/figure+image, with <code>, <bold>, <italic>
and <link href> inline.
"""

import re
import struct

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(text: str) -> str:
    """Like _escape, but also quotes — for use inside a "..." attribute
    value (src=, alt=, href=), where a literal " would truncate the
    attribute and break the XML."""
    return _escape(text).replace('"', "&quot;")


def _inline(text: str) -> str:
    """Escape, wrap `code`, then apply [links](url), **bold**, and
    *italic*/_italic_ with the code spans hidden behind placeholders —
    so markers INSIDE code (like `/**` or `snake_case`) can never
    trigger formatting, while markers AROUND code (**`code`**) still
    nest correctly."""
    parts = text.split("`")
    codes: list[str] = []
    buf = []
    for i, part in enumerate(parts):
        if i % 2 == 1 and i != len(parts) - 1:      # inside balanced backticks
            codes.append("<code>" + _escape(part) + "</code>")
            buf.append(f"\x00{len(codes) - 1}\x00")
        else:
            buf.append(_escape(part))
    s = "".join(buf)
    # s is already & / < / > escaped by the loop above; only quotes are left
    # to guard here, since re-running _escape_attr would double-escape &.
    s = LINK_RE.sub(lambda m: f'<link href="{m.group(2).replace(chr(34), "&quot;")}">'
                              f'{m.group(1)}</link>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<bold>\1</bold>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<italic>\1</italic>", s)
    s = re.sub(r"(?<![\w_])_([^_\n]+)_(?![\w_])", r"<italic>\1</italic>", s)
    for i, code in enumerate(codes):
        s = s.replace(f"\x00{i}\x00", code)
    return s


def png_size(data: bytes) -> tuple[int, int] | None:
    """Width/height from a PNG IHDR header; None for other formats."""
    if len(data) > 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    return None


def _flush_paragraph(lines: list[str], xml: list[str]) -> None:
    text = " ".join(l.strip() for l in lines).strip()
    if text:
        xml.append("<paragraph>" + _inline(text) + "</paragraph>")
    lines.clear()


def _table_row(line: str, header: bool = False) -> str:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    inner = "".join("<table-cell><paragraph>" + _inline(c) + "</paragraph></table-cell>"
                    for c in cells)
    return "<table-row>" + inner + "</table-row>"


def markdown_to_ed_xml(md: str, image_uploader=None) -> str:
    """Convert markdown to Ed document XML.

    image_uploader: callback taking the image path/URL from ![...](...)
    and returning (url, width_or_None, height_or_None). Required if the
    markdown references local (non-http) images.
    """
    xml: list[str] = []
    para: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # fenced code block: language tag -> snippet, bare -> pre
        m = re.match(r"```(\S*)(?:\s+(runnable|norun))?\s*$", stripped)
        if m:
            _flush_paragraph(para, xml)
            lang, flag = m.group(1).lower(), m.group(2)
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            raw = "\n".join(block)
            code = _escape(raw)
            if lang:
                if flag:
                    runnable = flag == "runnable"
                else:   # auto: a main method (classic or compact) => Run button
                    runnable = bool(re.search(r"\bvoid\s+main\s*\(", raw))
                xml.append(f'<snippet language="{lang}" runnable='
                           f'"{str(runnable).lower()}" line-numbers="true">'
                           f'<snippet-file id="code">{code}</snippet-file></snippet>')
            else:
                xml.append("<pre>" + code.replace("\n", "<break/>") + "</pre>")
            continue

        # horizontal rule (Ed has no rule element -> spacer paragraph)
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):
            _flush_paragraph(para, xml)
            xml.append("<paragraph></paragraph>")
            i += 1
            continue

        # image on its own line
        m = IMAGE_RE.match(stripped)
        if m:
            _flush_paragraph(para, xml)
            alt, src = m.group(1), m.group(2)
            w = h = None
            if src.startswith("http://") or src.startswith("https://"):
                url = src
            elif image_uploader:
                url, w, h = image_uploader(src)
            else:
                raise ValueError(f"local image {src!r} needs an image_uploader")
            dims = (f' width="{w}" height="{h}"' if w and h else "")
            xml.append(f'<figure><image src="{_escape_attr(url)}" alt="{_escape_attr(alt)}"'
                       f'{dims}></image></figure>')
            i += 1
            continue

        # heading: Ed supports levels 1-3; deeper -> bold paragraph
        m = re.match(r"(#{1,6})\s+(.*)", stripped)
        if m:
            _flush_paragraph(para, xml)
            level = len(m.group(1))
            if level <= 3:
                xml.append(f'<heading level="{level}">' + _inline(m.group(2)) + "</heading>")
            else:
                xml.append("<paragraph><bold>" + _inline(m.group(2)) + "</bold></paragraph>")
            i += 1
            continue

        # table (a | line followed by a |---| separator)
        if stripped.startswith("|") and i + 1 < len(lines) \
                and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            _flush_paragraph(para, xml)
            rows = [_table_row(stripped, header=True)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_table_row(lines[i].strip()))
                i += 1
            xml.append("<table>" + "".join(rows) + "</table>")
            continue

        # list (bullet or numbered), with two-space continuation lines
        m = re.match(r"([-*]|\d+\.)\s+(.*)", stripped)
        if m:
            _flush_paragraph(para, xml)
            style = "bullet" if m.group(1) in ("-", "*") else "number"
            items = []
            while i < len(lines):
                lm = re.match(r"([-*]|\d+\.)\s+(.*)", lines[i].strip())
                if lm:
                    items.append([lm.group(2)])
                    i += 1
                elif lines[i].startswith("  ") and lines[i].strip() and items:
                    items[-1].append(lines[i].strip())
                    i += 1
                elif not lines[i].strip():
                    # blank line ends the list unless the next line continues it
                    if i + 1 < len(lines) and re.match(r"([-*]|\d+\.)\s+", lines[i + 1].strip()):
                        i += 1
                    else:
                        break
                else:
                    break
            inner = "".join("<list-item><paragraph>" + _inline(" ".join(it)) + "</paragraph></list-item>"
                            for it in items)
            xml.append(f'<list style="{style}">' + inner + "</list>")
            continue

        # blank line = paragraph break
        if not stripped:
            _flush_paragraph(para, xml)
            i += 1
            continue

        para.append(line)
        i += 1

    _flush_paragraph(para, xml)
    return '<document version="2.0">' + "".join(xml) + "</document>"


if __name__ == "__main__":
    import sys
    print(markdown_to_ed_xml(open(sys.argv[1]).read()))
