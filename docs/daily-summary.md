---
type: Concept
title: Daily summary
description: The day's done tasks, time, breaks and focus sessions, and Super Productivity's evaluation (impact, energy, reflection) in the slice metric.
tags: [summary, evaluation, metric]
resource: ../pensum/store/metric.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Daily summary

(#23) **Daily Summary** in the main menu and after **Finish Day**: the
tasks worked on or done that day with their time, the day's total,
breaks and focus sessions, and the evaluation. Rules from
`metric.model.ts`, `metric.reducer.ts`, the evaluation sheet and
the reflection note[^sp20]:

- One `metric` entity per day, id = the day string. Writing a field
  creates it with `focusSessions: [], remindTomorrow: false,
  reflections: []` first (upsert).
- `impactOfWork` 1-4 ("How do you rate the impact of your work
  today?"), `energyCheckin` 1-3 (exhausted, OK, good).
- The reflection is `reflections[0] = {text, created}`: trimmed; an
  empty text writes `[]`; `created` stays from the first save.
- `globalConfig.evaluation.isHideEvaluationSheet` is kept as read.

Tests: `tests/test_evaluation.py`, `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
