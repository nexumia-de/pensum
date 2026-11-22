---
type: Concept
title: Worklog and time sheet
description: Time per day of a list for a week or a month from open and archived tasks, and the CSV time sheet with the list's worklogExportSettings, as Super Productivity's worklog export makes it.
tags: [worklog, time sheet, csv, export]
resource: ../pensum/store/worklog.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Worklog and time sheet

(#22) **Worklog** in a list's menu: the days of a week or a month with
the time worked, the task titles and the total; **Export Time Sheet**
writes a CSV. Rules from `worklog-export.util.ts` and
`WORKLOG_EXPORT_DEFAULTS`[^sp20]:

- Tasks: the open and archived tasks of the list (a project's; a tag's
  own or, for a subtask without tags, its parent's; Today: every task)
  with `timeSpentOnDay` cut to the range. A parent's time is its
  subtasks', so day totals count tasks without subtasks.
- Work start and end of a day: the list's `timeTracking` entry
  (`s`, `e`).
- Settings: the list's `advancedCfg.worklogExportSettings`, missing keys
  from the defaults (`DATE, START, END, TIME_CLOCK,
  TITLES_INCLUDING_SUB`, grouped by date, ` | ` between tasks, no
  rounding). Grouping DATE, PARENT, TASK or WORKLOG; every column type;
  work time rounded up to 5, 15, 30 or 60 minutes, start and end to
  the nearest quarter, half or full hour.
- Cells joined by `;`; a cell that starts with `= + - @`, tab or a
  line break gets a leading `'` (formula injection), cells with `;`,
  quotes or line breaks are quoted. Headers stay English. File name
  `tasks<first>-<last>.csv`.

Not built: editing the export settings (they come from Super
Productivity), the year view.

Tests: `tests/test_worklog.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
