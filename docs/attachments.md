---
type: Concept
title: Task attachments
description: A task's attachments as Super Productivity keeps them: shown on the task page, links, pictures and files opened through the portal, links added, commands never run.
tags: [attachments, links, tasks]
resource: ../pensum/store/attachments.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Task attachments

(#25) **Attachments** on the task page. Data and rules from
`task-attachment.model.ts`, `drop-paste.model.ts`, `task.reducer.ts`
and the edit dialog[^sp20]:

- `task.attachments`: `{id, type, path, title?}`, type `LINK`,
  `FILE`, `IMG`, `COMMAND` or `NOTE`.
- **Add Link** appends `{type: LINK, path, id}` (title only when
  given); a path without a scheme gets `http://`, `//host` gets
  `http:`; an empty path adds nothing.
- Removing deletes by id, with Undo; the rest of the list stays as read.
- Opening: `LINK` and `IMG` with `http`, `https`, `mailto` or
  `file` through `Gtk.UriLauncher`, `FILE` through
  `Gtk.FileLauncher` (the OpenURI portal in the Flatpak). A
  `COMMAND` is listed and never run; `NOTE` is shown as text.

Tests: `tests/test_attachments.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
