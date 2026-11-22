---
type: Concept
title: Project notes
description: A project's notes in Super Productivity's slice note: list, edit, pin to Today, remove with Undo; the order rules of its note and project reducers.
tags: [notes, projects, today]
resource: ../pensum/store/notes.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Project notes

(#24) **Notes** in a project's menu lists its notes; a note's page
edits the Markdown text, **Pin to Today** and removes it with Undo.
Today shows the pinned notes above its tasks. Rules of the note and
project reducers[^sp20]:

- A new note `{id, projectId, isPinnedToToday, content, created,
  modified}` goes to the top of `note.ids`, of `project.noteIds`
  and, when pinned, of `note.todayOrder`.
- Pinning prepends a note that is not in `todayOrder` yet; unpinning
  removes it.
- Deleting removes it from all three; deleting a project removes its
  notes (already so, `contexts.delete_project`).
- `imgUrl`, `isLock`, `backgroundColor` are kept as read.

`validate.problems()` checks that every `noteIds` entry is a note of
that project and every `todayOrder` id a note.

Tests: `tests/test_notes.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
