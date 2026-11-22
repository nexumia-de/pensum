---
type: Concept
title: Break reminder
description: The calm break reminder after an hour of tracked work, snooze, and breaks counted in timeTracking b and bt, as Super Productivity's take-a-break service counts them.
tags: [breaks, take-a-break, timeTracking, notifications]
resource: ../pensum/store/breaks.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Break reminder

(#20) Rules from `take-a-break.service.ts`, `work-context.service.ts`
and the default config[^sp20]:

- Time tracked on a task adds to "working without a break". More than
  10 minutes with no task tracked resets it (once per stretch), and so
  does taking the break.
- When it is over `globalConfig.takeABreak.takeABreakMinWorkingTime`
  (60 min) while `isTakeABreakEnabled` (default on) and no snooze
  runs, a notification says so with **Take a Break** and **Snooze**
  (`takeABreakSnoozeTime`, 15 min). No lock screen, no full-screen
  blocker (Super Productivity's are Electron-only and off by default).
- **Take a Break** stops tracking. When tracking starts again, the time
  in between is one break of the list shown then:
  `timeTracking.<project|tag>.<id>.<day>.b` + 1 and `bt` + its ms
  (`addToBreakTimeForActiveContext`; Today is the tag `TODAY`).
- The counter lives in memory, as in Super Productivity; it is checked
  once a minute (`pensum/break_watch.py`).

Tests: `tests/test_breaks.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
