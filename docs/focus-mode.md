---
type: Concept
title: Focus mode
description: Pomodoro, Flowtime and countdown sessions for the running task as Super Productivity's strategies run them, breaks that pause tracking, notifications, and focus sessions logged in metric.focusSessions.
tags: [focus, pomodoro, flowtime, metric]
resource: ../pensum/store/focus.py
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Focus mode

A focus page for one task (#19): **Focus** in the task's row menu or on
the task page. Rules from Super Productivity's `focus-mode-strategies.ts`
and `focus-mode.effects.ts`[^sp20]:

| Mode | Session | Break |
| --- | --- | --- |
| Pomodoro | `globalConfig.pomodoro.duration` (25 min) | `breakDuration` (5 min); after every `cyclesBeforeLongerBreak`-th (4) session `longerBreakDuration` (15 min); the next session starts after the break |
| Flowtime | counts up until ended | only with `flowtime.isBreakEnabled`: `breakPercentage` of the work, at least 1 min (mode `ratio`), or the first rule with `minDuration <= work < maxDuration` (mode `rule`) |
| Countdown | the minutes chosen (25 by default), shortened to the task's estimate left in whole minutes | none |

- Work starts tracking the task; a break stops tracking while
  `focusMode.isPauseTrackingDuringBreak` (default on) and starts it
  again afterwards.
- Every finished session appends its length in ms to
  `metric.<day>.focusSessions` (`logFocusSession`; a day's metric
  starts as `{id, focusSessions: [], remindTomorrow: false,
  reflections: []}`).
- The end of a session or a break comes as a notification.
- The running session is not stored, as in Super Productivity (local
  storage there); leaving the page leaves the session.

Not built: sounds, the preparation screen, Super Productivity's settings
dialogs for the three modes (the values are read from `globalConfig`).

Tests: `tests/test_focus.py` (strategies, defaults, logging,
`validate.problems()` empty), `tests/test_m3_ui.py`.

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
