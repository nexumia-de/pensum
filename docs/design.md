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

Frequent actions sit in bottom bars, within thumb reach; header bars
keep the title, back and the menu ([adaptive rule 10](../../phosh-toolkit/docs/adaptive-libadwaita.md)).

- **Lists** (on the phone the first page, on wide windows the sidebar):
  Today, the projects and the tags with their open task counts; main
  menu (import, export, archived projects, preferences, about) in the
  header; Search and Add List in a bottom bar.
- **List**: overdue, open and done tasks, backlog; the add field with
  its button in a bottom bar (new tasks go to the top, as in Super
  Productivity). Each row: check button, title, a subtitle with time,
  estimate, deadline, planned day and project, and a play button on the
  right.
- **Task** (pushed, swipe back): title, time spent (opens the time
  editor), estimate, Today, planned day and time, deadline, priority,
  project, tags, notes, subtasks, and Delete at the end (out of easy
  reach on purpose). Mark as Done and Start/Stop Timer in a bottom bar, as normal buttons at least 44 px high (`.pensum-bar-button`); `pill` buttons there made gtk4-broadwayd crash in about half of the CI screenshots (checked locally with the GNOME 51 Flatpak, 2026-11-05).
- **Row menu**: long press or right click on a task row opens Move to
  Top / Up / Down / to Bottom; Alt+↑/↓ does the same from the keyboard.
- **Timer bar** at the very bottom while a task runs: title, time today,
  stop button; tapping it opens the task. Hidden on that task's own page, without the reveal animation (animating it while the page slid in crashed gtk4-broadwayd).
- **Undo**: deleting a task or a list and Finish Day act at once and
  show a toast with Undo (GNOME HIG: undo instead of confirmation).
  Import still asks first; it replaces everything.

# Navigation

One `AdwNavigationView` holds every page. Below 600 sp the lists are its
first page and a list is pushed on it, so a swipe from the left goes
back from a task to its list and from a list to the lists. From 600 sp
the same sidebar widget moves into an `AdwOverlaySplitView` and the list
becomes the first page. Before 2026-11-05 the list and its pages sat in
a second navigation view inside an `AdwNavigationSplitView`'s content;
the owner found that the back swipe did not work on the phone.

Checked on 2026-11-06 with real touch events (headless Mutter 46 at
360 × 720, touch injected through its remote-desktop D-Bus API, the
window maximised like in Phosh, also maximised late after starting
wide): on `main` a swipe from left to right on Today goes back to the
lists; v0.1.0 (still the stable release, before the change above) does
not react. Still to be confirmed on the phone with a build from `main`
(the nightly) or the next release (#5).

# Not yet done

Drag to reorder, swipe actions on rows,
Markdown rendering of notes.
