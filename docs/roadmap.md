---
type: Plan
title: Roadmap
description: Goals and exit criteria of Pensum's milestones; the work items are GitHub issues in those milestones.
tags: [plan, roadmap, milestones]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# How the plan is tracked

Work items are [issues](https://github.com/nexumia-de/pensum/issues),
grouped by [milestones](https://github.com/nexumia-de/pensum/milestones)
and `area: …` labels; issues without a milestone are the backlog. This
file keeps only the goals; which Super Productivity feature lands where
is in [features](features.md). Workflow: the toolkit's
[planning with issues and milestones](../../phosh-toolkit/docs/planning.md).

# M1 – Daily use on the phone

**Goal**: the owner plans the day and tracks time on the phone with the
same data as Super Productivity.

**Exit criteria**: first release installed from the shared repository;
a Super Productivity export opens in Pensum and a Pensum export imports
into Super Productivity without repair; visible name chosen; tasks can
be reordered by touch.

# M2 – Planning like Super Productivity

**Goal**: the planning features people use daily: overdue tasks, time
of day, deadlines, priority, backlog, sections, repeating tasks,
reminders, short syntax, search, finish day with archive, editing
time spent.

**Exit criteria**: every M2 line in [features](features.md) works on
the phone and survives a round trip through Super Productivity.

# M3 – Focus, habits and reports

**Goal**: Pomodoro/Flowtime focus sessions, break reminders, habits,
worklog and daily summary, project notes, attachments, planner days,
menu folders.

# M4 – Sync with Super Productivity

**Goal**: Pensum and Super Productivity share one WebDAV (or Nextcloud,
or local) sync folder without manual export and import.

**Exit criteria**: reads v2 and v3 sync files incl. compressed and
encrypted ones; writes ops that Super Productivity replays to the same
state, proven by end-to-end tests in both directions with concurrent
edits ([sync files](super-productivity-sync.md)).

# Risks

- **Super Productivity's model changes**: new versions add optional
  fields (kept untouched); a new `crossModelVersion` is refused until
  Pensum supports it ([data model](super-productivity-data.md)).
- **Sync is the hard part**: Super Productivity's sync rules call it
  high-risk; M4 starts read-only.
