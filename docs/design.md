---
type: Concept
title: Visual design
description: Stock libadwaita with Pensum's indigo accent, the screens at 360 px and on the desktop.
tags: [design, accent, adaptive, libadwaita]
resource: ../pensum/style.css
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

Pensum follows the toolkit's [visual design](../../phosh-toolkit/docs/design.md)
and [adaptive UI](../../phosh-toolkit/docs/adaptive-libadwaita.md) rules.

# Accent

Indigo `#5b4fc7` with white text (contrast 6.2:1), set only through
`--accent-bg-color`/`--accent-fg-color` in `style.css` (plus
`@define-color` for libadwaita 1.5 hosts)
([one accent per app](../../phosh-toolkit/docs/decisions/app-accent-colours.md)).
Light and dark follow the system; Preferences → Appearance → Style
offers Follow System / Light / Dark. Metainfo branding colours:
`#cdc8f2` (light), `#2e2666` (dark).

# Screens

- **Lists** (sidebar; on the phone the first page): Today, the projects
  and the tags with their open task counts; add buttons and the main
  menu (import, export, preferences, about) in the header.
- **List**: an entry row "Add Task" on top (new tasks go to the top, as
  in Super Productivity), the open tasks, then "Done". Each row: check
  button, title, a subtitle with time spent / estimate, subtask count
  and (in Today and tag lists) the project, and a play button.
- **Task** (pushed, swipe back): title, done, time spent with the timer
  button, estimate, Today switch, planned day (calendar popover), project,
  tags (dialog), notes, subtasks (each opens its own page), delete.
- **Row menu**: long press or right click on a task row opens Move to
  Top / Up / Down / to Bottom; Alt+↑/↓ does the same from the keyboard.
- **Archived Projects** (main menu): open or unarchive them.
- **Timer bar** at the bottom while a task runs: title, time today,
  stop button; tapping it opens the task.

At 600 sp and below the split view collapses: the lists page is the
root, a list and its task pages are pushed on it.

# Not yet done

Drag to reorder, swipe actions on rows,
Markdown rendering of notes.
