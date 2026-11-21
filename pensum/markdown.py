"""Markdown for reading a note: the source is cut into blocks whose text is
Pango markup. Only for display; the source is never rewritten, except for
the one character a ticked checkbox changes (`toggle_task`). Everything
that is not recognised, raw HTML included, is shown as the text it is.
The subset follows what Super Productivity shows in a task's notes
(docs/markdown-notes.md). No GTK."""
import html
import re
from dataclasses import dataclass, field

# Schemes a link may open; everything else stays text. Narrower than Super
# Productivity's list: no file: and no app deep links.
LINK_SCHEMES = ("http", "https", "mailto", "tel", "sms")

_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})(.*)$")
_HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_RULE = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_QUOTE = re.compile(r"^\s*(?:>\s*)+")
# A checklist line, as Super Productivity's editor finds it (TASK_LINE_RE).
_TASK = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+\[([ xX])\]\s?")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_ORDERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_BARE_HOST = re.compile(
    r"^(?:www\.[a-z0-9-]+(?:\.[a-z0-9-]+)*(?=$|[/?#])"
    r"|[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+(?=[/?#]))", re.I)
_SCHEME = re.compile(r"^([a-z][a-z0-9+.-]*):", re.I)

_INLINE = re.compile(r"""
  (?P<escape>\\(?P<escaped>[\\`*_{}\[\]()#+\-.!~>|]))
 |(?P<code>(?P<ticks>`+)(?P<code_text>.+?)(?<!`)(?P=ticks)(?!`))
 |(?P<image>!\[(?P<alt>[^\]]*)\]\(\s*(?P<src><[^>]*>|(?:[^\s()]|\([^\s()]*\))+)[^)]*\))
 |(?P<link>\[(?P<label>[^\]]+)\]\(\s*(?P<href><[^>]*>|(?:[^\s()]|\([^\s()]*\))+)
     (?:\s+"[^"]*")?\s*\))
 |(?P<auto><(?P<auto_url>[a-zA-Z][a-zA-Z0-9+.-]*:[^\s<>]+)>)
 |(?P<bare>(?<![\w/@.])(?:https?://|www\.)[^\s<>"']+)
 |(?P<bold>(?P<bm>\*\*|__)(?=\S)(?P<bold_text>.+?)(?<=\S)(?P=bm))
 |(?P<strike>~~(?=\S)(?P<strike_text>.+?)(?<=\S)~~)
 |(?P<star>\*(?=[^\s*])(?P<star_text>[^*]+?)(?<=\S)\*)
 |(?P<under>(?<!\w)_(?=[^\s_])(?P<under_text>[^_]+?)(?<=\S)_(?!\w))
""", re.X)


@dataclass
class Block:
    """One piece of a note. `kind` is "paragraph", "heading", "bullet",
    "ordered", "task", "code" or "rule"; `markup` is Pango markup."""
    kind: str
    markup: str = ""
    level: int = 0          # heading 1–6; list items: depth of indentation
    quoted: bool = False    # inside a block quote
    number: str = ""        # an ordered item's number
    checked: bool = False   # a task item's state
    line: int = -1          # a task item's line in the source, from 0
    lines: list = field(default_factory=list)  # source lines of a paragraph


def link_target(raw):
    """The URI a link may open, or None: only a few schemes, a bare host
    gets http:// and //host gets https: (Super Productivity's rule)."""
    href = (raw or "").strip()
    if href.startswith("<") and href.endswith(">"):
        href = href[1:-1].strip()
    if not href or any(ord(c) < 32 for c in href):
        return None
    if href.startswith("//"):
        href = "https:" + href
    elif not _SCHEME.match(href) and _BARE_HOST.match(href):
        href = "http://" + href
    scheme = _SCHEME.match(href)
    if not scheme or scheme.group(1).lower() not in LINK_SCHEMES:
        return None
    return href


def _text(value):
    return html.escape(value, quote=True)


def _anchor(href, label_markup):
    target = link_target(href)
    if target is None:
        return label_markup
    return f'<a href="{_text(target)}">{label_markup}</a>'


def inline(text):
    """A line's text as Pango markup: emphasis, code, links; the rest
    escaped, so tags typed into a note show as typed."""
    out, at = [], 0
    for match in _INLINE.finditer(text):
        out.append(_text(text[at:match.start()]))
        at = match.end()
        kind = match.lastgroup
        if kind == "escape":
            out.append(_text(match.group("escaped")))
        elif kind == "code":
            out.append(f"<tt>{_text(match.group('code_text').strip())}</tt>")
        elif kind == "image":
            # Never loaded: the description, as a link to the picture.
            label = _text(match.group("alt") or "Image")
            out.append(_anchor(match.group("src"), f"<i>{label}</i>"))
        elif kind == "link":
            out.append(_anchor(match.group("href"), inline(match.group("label"))))
        elif kind == "auto":
            out.append(_anchor(match.group("auto_url"), _text(match.group("auto_url"))))
        elif kind == "bare":
            url = match.group("bare")
            tail = len(url) - len(url.rstrip(".,;:!?)'\""))
            if tail:
                url, at = url[:-tail], at - tail
            out.append(_anchor(url, _text(url)))
        elif kind == "bold":
            out.append(f"<b>{inline(match.group('bold_text'))}</b>")
        elif kind == "strike":
            out.append(f"<s>{inline(match.group('strike_text'))}</s>")
        elif kind == "star":
            out.append(f"<i>{inline(match.group('star_text'))}</i>")
        else:
            out.append(f"<i>{inline(match.group('under_text'))}</i>")
    out.append(_text(text[at:]))
    return "".join(out)


def _depth(indent):
    return min(len(indent.expandtabs(4)) // 2, 4)


def parse(source):
    """A note's blocks, in order. Lines are the source's lines split at
    "\\n"; a task block knows its line for `toggle_task`."""
    blocks, paragraph, fence, code = [], None, None, []
    lines = (source or "").split("\n")

    def close():
        nonlocal paragraph
        if paragraph is not None:
            paragraph.markup = "\n".join(inline(line) for line in paragraph.lines)
            blocks.append(paragraph)
            paragraph = None

    for number, raw in enumerate(lines):
        line = raw[:-1] if raw.endswith("\r") else raw
        opening = _FENCE.match(line)
        if fence is not None:
            if opening and opening.group(1)[0] == fence[0] \
                    and len(opening.group(1)) >= len(fence) \
                    and not opening.group(2).strip():
                blocks.append(Block("code", _text("\n".join(code))))
                fence, code = None, []
            else:
                code.append(line)
            continue
        if opening:
            close()
            fence = opening.group(1)
            continue
        quote = _QUOTE.match(line)
        quoted = bool(quote)
        rest = line[quote.end():] if quote else line
        if not rest.strip():
            close()
            continue
        heading = _HEADING.match(rest)
        task = _TASK.match(rest)
        if heading:
            close()
            blocks.append(Block("heading", inline(heading.group(2)), quoted=quoted,
                                level=len(heading.group(1))))
        elif _RULE.match(rest):
            close()
            blocks.append(Block("rule", quoted=quoted))
        elif task:
            close()
            blocks.append(Block("task", inline(rest[task.end():]), quoted=quoted,
                                level=_depth(task.group(1)), line=number,
                                checked=task.group(3) != " "))
        elif _BULLET.match(rest):
            close()
            found = _BULLET.match(rest)
            blocks.append(Block("bullet", inline(found.group(2)), quoted=quoted,
                                level=_depth(found.group(1))))
        elif _ORDERED.match(rest):
            close()
            found = _ORDERED.match(rest)
            blocks.append(Block("ordered", inline(found.group(3)), quoted=quoted,
                                level=_depth(found.group(1)), number=found.group(2)))
        else:
            if paragraph is not None and paragraph.quoted != quoted:
                close()
            if paragraph is None:
                paragraph = Block("paragraph", quoted=quoted)
            paragraph.lines.append(rest.strip())
    close()
    if fence is not None:  # a fence left open runs to the end
        blocks.append(Block("code", _text("\n".join(code))))
    return blocks


def toggle_task(source, line):
    """The source with the checkbox of line `line` (from 0) ticked or
    unticked: one character between its brackets changes, " " to "x" or
    "x"/"X" to " " (Super Productivity's taskMarkerToggleFor); every other
    byte stays. The source itself when the line is no checklist line."""
    lines = source.split("\n")
    if not 0 <= line < len(lines):
        return source
    text = lines[line]
    quote = _QUOTE.match(text)
    offset = quote.end() if quote else 0
    task = _TASK.match(text[offset:])
    if not task:
        return source
    at = sum(len(part) + 1 for part in lines[:line]) + offset + task.group(0).index("[") + 1
    return source[:at] + ("x" if source[at] == " " else " ") + source[at + 1:]
