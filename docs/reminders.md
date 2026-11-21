---
type: Concept
title: Reminders
description: How Day Planner keeps and shows task reminders - Super Productivity 20's task.remindAt and the time and reminder of a repeat rule, the notification with Done and Snooze, running in the background while the window is closed, and what is still to be checked on the phone.
tags: [reminders, notifications, background, repeat]
resource: ../pensum/store/reminders.py
generated: { by: claude-code/2.1.326, at: 2026-11-20 }
sources:
  - id: sp20
    title: Super Productivity 20.0.0, commit 9980fd76 (2026-11-18)
    url: https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
---

# Reminders

A reminder belongs to a task's time. Day Planner keeps it as Super
Productivity does and shows it as a notification, also while its window
is closed (#13).

## The data

Read from Super Productivity 20.0.0[^sp20] (MIT, Johannes Millan);
values are transcribed, no code is copied.

- **A task's reminder is `task.remindAt`** (ms), optional and
  non-nullable: it is deleted, never set to null. The older `reminders`
  slice is only migrated by Super Productivity
  (`features/reminder/migrate-legacy-task-reminders.util.ts`); Day
  Planner keeps it as read and writes nothing into it.
- **It is a lead before `dueWithTime`**: the option ids of
  `TaskReminderOptionId` (`features/tasks/task.model.ts`) are
  `DoNotRemind`, `AtStart`, `m5`, `m10`, `m15`, `m30`, `h1`, and the
  long leads `d1`, `d3`, `w1`; `remindAt = dueWithTime − lead`
  (`util/remind-option-to-milliseconds.ts`). Day Planner offers the
  first seven.
- **Rules of the reducers**
  (`root-store/meta/task-shared-meta-reducers/task-shared-scheduling.reducer.ts`,
  `features/tasks/store/task.reducer.ts`): scheduling a task at a time
  sets `dueWithTime` and `remindAt` and removes `dueDay`; planning it
  for a day alone, or unplanning it, removes `dueWithTime` and
  `remindAt`; dismissing a reminder removes only `remindAt`; snoozing
  reschedules with the new `remindAt` and keeps `dueWithTime` (a task
  without one gets the new moment as its time,
  `features/reminder/reminder.module.ts`).
- **A repeat rule** has `startTime` ("21:30") and `remindAt` (an option
  id). A new instance gets `dueWithTime` at that time on its day and
  `remindAt` before it only when the rule has both
  ([data model](super-productivity-data.md)). When they change, the open
  instance created today is rescheduled the same way
  (`features/task-repeat-cfg/store/task-repeat-cfg.effects.ts`).

## What Day Planner does

- `pensum/store/reminders.py`: `set_option`, `dismiss`, `snooze`
  (10 minutes), `pending`, `due`, `next_at`, and for a rule `rule_time`
  and `set_rule_time`. `planning.schedule_time` keeps the lead when the
  time moves; `planning.schedule_day` drops the reminder with the time.
- **Task page**: **Reminder** under the time, with the seven options;
  without a time it says "Set a time first". **Repeat page**: **Time**
  and **Reminder** for every new task of the rule.
- **Notification** (`pensum/reminder_watch.py`): when `remindAt` comes,
  a `GNotification` with the task's title, **Done** and **Snooze 10
  min**; tapping it opens the task and puts the reminder away. Each
  reminder is shown once while it waits. Logs name task ids only.
- **While the window is closed** the application stays alive as long as
  a reminder is pending or a repeat rule that is not paused will bring
  one (Preferences → Reminders → **Remind When Closed**, on by
  default). Without a window the watcher reads and writes the data
  file, and creates the repeat instances of a new day, so a habit's
  reminder comes on a day Day Planner was not opened. A closed window
  stops its own timers and never writes again.
- **Start with the session** (`pensum/background.py`): inside the
  Flatpak the Background portal is asked once for background running
  and autostart as `pensum --gapplication-service` (no window). Outside
  the Flatpak nothing is asked.
- The clock is checked at least once a minute: a timer does not count
  the time a phone sleeps, so after waking a due reminder comes within
  a minute.

## Journeys

QuestArc sends no notifications; the reminder is the task's
([journeys](journeys.md), QuestArc flow H). Its engine reads a rule's
`startTime` and `remindAt`, so the Repeat page is where a habit's
reminder is set. Day Planner shows QuestArc's sentence at set-up, the
suggestion in a station's first two weeks and "you may not need the
reminder any more" (`pensum/ui/journey/reminder_banner.py`), each with
**Open the task** and **Not Now**; it never sets or removes a reminder
there.

## Not checked yet (on the phone)

The cloud container has no notification daemon, no portal and no
Phosh. Open on the device:

- **A sleeping phone is not woken.** Nothing in the sandbox can set a
  wake alarm; the reminder comes when the phone wakes for another
  reason. Whether Phosh offers a way (a wake-up service of the
  distribution) is not known here.
- Whether Phosh's session starts the portal's autostart entry and keeps
  a windowless application running.
- How the notification's buttons look and work on the lock screen.
- Memory of the windowless process over a day.

Deadline reminders (`deadlineRemindAt`) are not shown yet.

## Tests

`tests/test_reminders.py` (the store, with `validate.problems()` empty
after every change), `tests/test_reminder_watch.py` (shown once, Done,
Snooze and opening with a window; the file, the day's instance and the
hold without one; the task and repeat pages),
`tests/test_journey_reminders.py` (QuestArc's sentence, suggestion and
**Not Now**).

[^sp20]: Super Productivity 20.0.0 at commit 9980fd76, https://github.com/johannesjo/super-productivity/tree/9980fd76f2c05da01df814f5339a22f6780c0747
