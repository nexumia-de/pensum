---
type: Concept
title: Markdown in notes
description: How a task's notes are shown formatted - what Super Productivity renders in notes (its live editor and marked options), the subset Day Planner shows with Pango markup, what is never done with a note (no web view, no pictures, no HTML), ticking a checkbox, and that the stored note stays as typed.
tags: [notes, markdown, checklist, links, security]
resource: ../pensum/markdown.py
generated: { by: claude-code/2.1.330, at: 2026-11-21 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Markdown in notes

A task's `notes` is Markdown source. Day Planner shows it formatted and
edits it as plain text (#18). The stored string is what was typed.

## What Super Productivity does[^sp20]

Read on 2026-11-21: `src/app/ui/inline-markdown/inline-markdown.component.{ts,html}`,
`src/app/ui/inline-markdown/live-markdown/live-markdown-ranges.ts`,
`src/app/ui/marked-options-factory.ts`, `src/app/ui/link-href.util.ts`,
`electron/shared-with-frontend/is-external-url-allowed.ts`, `package.json`.

- **Switch.** `globalConfig.tasks.isMarkdownFormattingInNotesEnabled`,
  on when missing. Off, a note is a plain text field.
- **In a task's notes** the formatting is a live editor (CodeMirror):
  the source stays in the field and is decorated; the markers of the
  line the caret is on stay visible. It decorates headings, emphasis,
  inline code, block quotes, horizontal rules, fenced and indented code,
  tables, URLs, pictures and checklist lines.
- **A checklist line** is `- [ ] `, `* [x] `, `+ [X] `, `1. [ ] ` or
  `1) [ ] ` after any indentation, also inside a block quote
  (`TASK_LINE_RE`). A click changes the one character between the
  brackets: a blank becomes `x`, `x` or `X` becomes a blank
  (`taskMarkerToggleFor`).
- **Elsewhere** (the preview renderer, `markedOptionsFactory`): `marked`
  `^18.0.5` through `ngx-markdown` with `gfm: true`, `breaks: true` (a
  single line break is a line break), `pedantic: false`; own rules for
  checklist items, for a paragraph line with `h1.` to `h6.` as a
  heading, for `![alt](url =WxH)` picture sizes and for `webexteams://`
  links.
- **Links** render only when `toRenderableHref` allows them: the scheme
  must be on a list (`http`, `https`, `mailto`, `mid`, `file` (local
  only), `tel`, `sms` and app links such as `obsidian`, `vscode`,
  `zotero`, `notion`, `outlook`); a bare host gets `http://`, `//host`
  gets `https:`. Other links show as text.
- **Pictures** are loaded from the web; rendered HTML is sanitized, not
  shown as text.

## What Day Planner shows

`pensum/markdown.py` cuts the source into blocks whose text is Pango
markup; `pensum/ui/notes_view.py` shows them as labels,
`pensum/ui/notes_box.py` is the Notes group of the task page. No new
dependency: Pango markup and GTK labels of the GNOME runtime.

| Source | Shown |
|---|---|
| `# ` to `###### ` | heading (three sizes, then bold) |
| blank line / single line break | new paragraph / line break |
| `**a**`, `__a__`, `*a*`, `_a_`, `~~a~~`, `` `a` `` | bold, italic, struck through, monospace (`_` only at word edges) |
| `- `, `* `, `+ `, `1. `, `1) ` | list items, indented by their depth |
| `- [ ] `, `- [x] ` (the forms above) | a checkbox that can be ticked, the text dimmed when done |
| `> ` | a bar at the side |
| `---`, `***`, `___` | a line |
| fenced code (three or more backticks or tildes) | monospace block, as typed, wrapping |
| `[text](url)`, `<url>`, `https://…`, `www.…` | a link, if the scheme is `http`, `https`, `mailto`, `tel` or `sms` |
| `![alt](url)` | the description in italics as a link to the picture; never loaded |
| `\*` and other escapes | the character |
| everything else: raw HTML, tables, `h1.`, indented code, setext headings, reference links | the text as typed |

Deliberately narrower than Super Productivity: no `file:` and no app
links, no pictures, no HTML.

## Rules

- **The note stays as typed.** Showing a note writes nothing. The text
  field saves only after the user changed its text (not when its
  content merely differs, so a note the field cannot hold exactly is
  not rewritten by opening it). A test stores a note with CRLF, tabs,
  trailing spaces and HTML, opens, views, switches to the field and
  back, leaves, saves, and compares the string.
- **Ticking a checkbox** changes that one character in the source
  (`markdown.toggle_task`), by Super Productivity's rule.
- **Nothing of a note is run or loaded:** no web view, no pictures, no
  HTML. All text is escaped before it becomes markup.
- **Links** open only on a tap, through the system's handler
  (`Gtk.UriLauncher`), and only for the schemes above; the scheme is
  checked when the markup is made and again on the tap.
- **Reading and editing:** a note opens formatted, an empty one as the
  empty text field; no field has the focus when the page opens. The
  Edit / Done button in the group's header switches with one tap
  (44 px). With the switch off in Super Productivity's settings there
  is only the text field.
- Logs never contain note text (there is no logging in these modules).

## Open

The editor is a plain text field: no toolbar, no live decoration, no
checklist button. Tables and indented code show as typed. Not tried on
the phone with the on-screen keyboard.
