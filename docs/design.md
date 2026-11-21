---
type: Concept
title: Visual design
description: Stock libadwaita with Pensum's indigo accent, the screens at 360 px and on the desktop.
tags: [design, accent, adaptive, libadwaita]
resource: ../pensum/style.css
generated: { by: claude-code/2.1.318, at: 2026-11-12T00:00:00Z }
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
- **Reorder by dragging** (`pensum/ui/row_drag.py`): a task row dropped
  on another row of the same list takes its place; a line in the accent
  colour shows where it lands (above the row when moving up, below when
  moving down), the dragged row is dimmed. A pointer drags at once. A
  finger drags after a long press (the row is tinted when it is ready),
  because until then a drag scrolls the list. Near the upper or lower
  edge the list scrolls. Open tasks, done tasks, the backlog and a
  task's subtasks each reorder among themselves; overdue tasks have no
  order. Checked with a real pointer (Xvfb) and with real touch events
  in a headless Mutter on 2026-11-21; the feel on the phone is still to
  be checked there.
- **Row menu**: a long press let go without moving, a right click or the
  Menu key (Shift+F10) on a task row opens Move to Top / Up / Down / to
  Bottom, the accessible way to reorder; Alt+↑/↓ moves the focused row.
  The list stays where it is scrolled and the moved row keeps the focus
  (`pensum/ui/scroll.py`).
- **Timer bar** at the very bottom while a task runs: title, time today,
  stop button; tapping it opens the task. Hidden on that task's own page, without the reveal animation (animating it while the page slid in crashed gtk4-broadwayd).
- **Undo**: deleting a task or a list and Finish Day act at once and
  show a toast with Undo (GNOME HIG: undo instead of confirmation).
  Import still asks first; it replaces everything. When the current data
  has changes the file lacks, the question becomes a warning with counts
  ("Import Older Data?", "3 tasks and 1 journey entry would be lost",
  the journey's lost completions by day) and **Import Anyway** /
  **Cancel**; the automatic backup before the import stays the undo
  (#47).

# Navigation

The layout is Ephyra's, which swipes back correctly on the phone (owner,
2026-11-06; phosh-toolkit adaptive rule 9): one `AdwNavigationView`
whose first page holds an `AdwNavigationSplitView` with the lists as
sidebar and the shown list (or Journeys) as content. Below 600 sp the
split view collapses: the list lies above the lists, so a swipe from a
list goes back to them, and its header has a back button. Task, search,
archived projects and the journey's own pages are pushed on the
navigation view and swipe back to where they were opened.

Day Planner opens on Journeys once the dataset holds a QuestArc record,
and Journeys is then the first row of the sidebar; without one it opens
on the list shown last, with Today first (#78,
[decision](decisions/habits-first.md)). An import opens the same way.

While a journey grows a step, Today starts with one strip of fixed
height (72 × 48 px picture, two lines that never wrap) that opens the
journey; the first task stays in view at 360 × 720 (#57,
[journeys](journeys.md)).

History: v0.1.0 nested a second navigation view in the split view's
content, and the back swipe did not work on the phone. The next layout
(one navigation view with the lists as its first page, moved into an
`AdwOverlaySplitView` on wide windows) was the owner's report on
2026-11-06 ("back to the overview is missing", compared with Ephyra and
Nauta). The Ephyra layout was checked with real touch events (headless
Mutter at 360 × 720, touch through its remote-desktop API): a swipe from
Today, from Journeys and from a task goes back, also when the window
starts wide and is maximised later. To be confirmed on the phone (#5).

# The Valley

The home of the journeys is one picture, the Valley ([Valley](valley.md)):
the pictures' colours come from libadwaita's roles and each place's hue
from QuestArc's palette, so light and dark follow the system, and the
only colour of the app's own is the accent in `style.css`. Names stand on
tinted ground in the text colour (QuestArc checks 4.5 : 1 for every hue,
light and dark, on libadwaita's cards). The growing place's name is bold:
shape, not colour, says which one grows. Every place is a 44 px button;
nothing scrolls sideways at 360 px.

# Not yet done

Swipe actions on rows, Markdown rendering of notes.
