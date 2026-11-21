"""Markdown in notes: display only, the source stays as typed."""
import pytest

from pensum import markdown


def kinds(source):
    return [b.kind for b in markdown.parse(source)]


def test_blocks():
    source = ("# Plan\n\nFirst **bold** and *italic*,\nsecond line.\n\n"
              "- one\n  - nested\n1. first\n2) second\n\n> quoted\n\n---\n"
              "```py\nx = <b>1</b>\n```\n- [ ] open\n- [x] done\n> - [X] quoted done")
    blocks = markdown.parse(source)
    assert [b.kind for b in blocks] == [
        "heading", "paragraph", "bullet", "bullet", "ordered", "ordered",
        "paragraph", "rule", "code", "task", "task", "task"]
    assert blocks[0].level == 1 and blocks[0].markup == "Plan"
    # A single line break is a line break (marked's breaks: true).
    assert blocks[1].markup == "First <b>bold</b> and <i>italic</i>,\nsecond line."
    assert blocks[3].level == 1 and blocks[5].number == "2"
    assert blocks[6].quoted and blocks[6].markup == "quoted"
    # Code is shown as typed.
    assert blocks[8].markup == "x = &lt;b&gt;1&lt;/b&gt;"
    assert [(b.checked, b.line) for b in blocks[9:]] == [(False, 16), (True, 17), (True, 18)]
    assert blocks[11].quoted


def test_inline():
    assert markdown.inline("a `x*y*` b") == "a <tt>x*y*</tt> b"
    assert markdown.inline("~~gone~~ __strong__ _soft_") == \
        "<s>gone</s> <b>strong</b> <i>soft</i>"
    assert markdown.inline("snake_case_name and 2*3*4") == "snake_case_name and 2<i>3</i>4"
    assert markdown.inline(r"\*not italic\*") == "*not italic*"
    assert markdown.inline("**bold with *italic* inside**") == \
        "<b>bold with <i>italic</i> inside</b>"


def test_raw_html_shows_as_text():
    import re
    for source in ("<script>alert(1)</script>", '<img src="https://example.org/x.png">',
                   "<b>bold?</b> &amp; <a href='https://example.org'>x</a>",
                   "<iframe src=//example.org></iframe>", "<!-- c --> <p onclick=x>"):
        markup = markdown.parse(source)[0].markup
        # The only tags are the links Pensum made itself from bare URLs.
        own = re.sub(r'<a href="https?://example\.org[^"<>]*">|</a>', "", markup)
        assert "<" not in own and ">" not in own and "&lt;" in own
        assert html_text(markup) == source


def html_text(markup):
    """What a label shows for a markup: the tags gone, the entities read."""
    import html
    import re
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def test_links_only_with_safe_schemes():
    assert markdown.inline("[site](https://example.org/a?b=1&c=2)") == \
        '<a href="https://example.org/a?b=1&amp;c=2">site</a>'
    assert markdown.inline("see https://example.org/x. Then") == \
        'see <a href="https://example.org/x">https://example.org/x</a>. Then'
    assert markdown.inline("www.example.org") == \
        '<a href="http://www.example.org">www.example.org</a>'
    assert markdown.inline("<mailto:a@example.org>") == \
        '<a href="mailto:a@example.org">mailto:a@example.org</a>'
    assert markdown.inline("[docs](example.org/docs)") == \
        '<a href="http://example.org/docs">docs</a>'
    # Other schemes stay text: nothing to tap.
    for href in ("javascript:alert(1)", "file:///etc/passwd", "smb://host/share",
                 "data:text/html,x", "vscode://x", "relative/path", "#anchor"):
        assert markdown.inline(f"[label]({href})") == "label"
        assert markdown.link_target(href) is None
    assert markdown.link_target(" HTTPS://Example.org ") == "HTTPS://Example.org"
    # A picture is never loaded: its description links to it.
    assert markdown.inline("![a cat](https://example.org/cat.png =100x)") == \
        '<a href="https://example.org/cat.png"><i>a cat</i></a>'
    assert markdown.inline("![](file:///x.png)") == "<i>Image</i>"


def test_toggle_changes_one_character():
    source = "Intro\r\n- [ ] one\r\n  * [x] two\n> 1. [X] three\n- [] no\n-[ ] no\n"
    blocks = [b for b in markdown.parse(source) if b.kind == "task"]
    assert [b.line for b in blocks] == [1, 2, 3]
    assert markdown.toggle_task(source, 1) == source.replace("- [ ] one", "- [x] one")
    assert markdown.toggle_task(source, 2) == source.replace("* [x] two", "* [ ] two")
    assert markdown.toggle_task(source, 3) == source.replace("[X] three", "[ ] three")
    for line in (0, 4, 5, 6, 99, -1):
        assert markdown.toggle_task(source, line) is source
    for line in (1, 2, 3):
        changed = markdown.toggle_task(source, line)
        assert len(changed) == len(source)
        assert sum(a != b for a, b in zip(source, changed)) == 1
        # Ticking twice gives the lower-case x or the blank back.
        again = markdown.toggle_task(changed, line)
        assert again.lower() == source.lower() and len(again) == len(source)


def test_parse_never_fails_and_gives_valid_markup():
    import re
    gi = pytest.importorskip("gi")
    gi.require_version("Pango", "1.0")
    from gi.repository import Pango
    samples = ["", "\n\n", "```", "~~~\nopen", "**", "*a", "[x](", "![", "<", "&", "\\",
               "a_b_c *x **y* z**", "[a [b](https://e.org)](https://f.org)",
               "`` ` ``", "- ", "1.", "> ", "#", "####### seven", "| a | b |\n|---|---|",
               "h1. Jira", "\t- [ ] tab", "\x00\x01 odd", "a\rb", "🙂 **émoji**",
               "<a href=\"x\">&nbsp;</a>", "__init__ and *args, **kwargs"]
    for sample in samples:
        for block in markdown.parse(sample):
            # GTK's label reads the links itself; Pango checks the rest.
            plain = re.sub(r'<a href="[^"<>]*">|</a>', "", block.markup)
            ok, *_ = Pango.parse_markup(plain.replace("\x00", ""), -1, "\0")
            assert ok, sample
