---
type: Concept
title: Planner
description: Today and the next six days with their open tasks and the estimate left, and moving a task to another day, by Super Productivity's planner rules.
tags: [planner, days, planning]
resource: ../pensum/store/planner.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Planner

(#26) **Planner** in the main menu: seven days from today. Rules from
`planner.reducer.ts` and `planner-shared.reducer.ts`[^sp20]:

- A later day lists the open top-level tasks planned for it
  (`dueWithTime`'s day wins over `dueDay`), in `planner.days[day]`
  order, then in `task.ids` order; tasks with a time first, by time.
  Today is Today's list.
- A day's estimate is the sum of `timeEstimate - timeSpent` (not
  below 0) of its tasks.
- **Move to Another Day** plans the task there
  (`planning.schedule_day`: Today's order or `planner.days`, the time
  of day and reminder dropped as `planTaskForDay` does).

Not built: dragging between days, more than seven days.

Tests: `tests/test_planner.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
