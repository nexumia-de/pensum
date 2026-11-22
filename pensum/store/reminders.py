"""Reminders of tasks, the way Super Productivity 20 keeps them
(docs/super-productivity-data.md, reminders): a task's reminder is its
`remindAt` (ms), a lead before `dueWithTime`; the older `reminders`
slice is kept as read. A repeat rule's `startTime` and `remindAt` (an
option id) give each new instance its time and reminder. `remindAt` is
optional and non-nullable: it is deleted, never set to null. No GTK."""
from datetime import datetime

from pensum.i18n import N_, _
from pensum.store import dates, planning, tasks
from pensum.store.repeat import instances

# Super Productivity's TaskReminderOptionId with a time, as minutes
# before the task's time, and the label of each.
LEAD_MINUTES = instances.REMIND_MINUTES
NONE = "DoNotRemind"
OPTIONS = [(NONE, N_("No reminder")), ("AtStart", N_("At the time")),
           ("m5", N_("5 minutes before")), ("m10", N_("10 minutes before")),
           ("m15", N_("15 minutes before")), ("m30", N_("30 minutes before")),
           ("h1", N_("1 hour before"))]
SNOOZE_MINUTES = 10


def option_labels():
    """The label of each option, in the user's language."""
    return [_(label) for _key, label in OPTIONS]


def option_of(task):
    """The option a task's reminder matches; "custom" for another moment
    (a snoozed reminder), DoNotRemind without one."""
    remind, due = task.get("remindAt"), task.get("dueWithTime")
    if not isinstance(remind, (int, float)):
        return NONE
    if isinstance(due, (int, float)):
        for option, minutes in LEAD_MINUTES.items():
            if due - remind == minutes * 60_000:
                return option
    return "custom"


def set_option(ds, task_id, option, now=None):
    """Remind `option` before the task's time; DoNotRemind removes the
    reminder and keeps the time. A task without a time gets none."""
    task = ds.tasks[task_id]
    due = task.get("dueWithTime")
    if option in LEAD_MINUTES and isinstance(due, (int, float)):
        task["remindAt"] = int(due) - LEAD_MINUTES[option] * 60_000
    else:
        task.pop("remindAt", None)
    tasks._touch(task, now or dates.now_ms())


def dismiss(ds, task_id, now=None):
    """Only the reminder goes; the time and the day stay."""
    set_option(ds, task_id, NONE, now)


def snooze(ds, task_id, minutes=SNOOZE_MINUTES, now=None):
    """Remind again in `minutes`; the task keeps its time, and one without
    a time is planned at the new moment."""
    now = now or dates.now_ms()
    task = ds.tasks[task_id]
    again = now + minutes * 60_000
    if not isinstance(task.get("dueWithTime"), (int, float)):
        moment = datetime.fromtimestamp(again / 1000)
        planning.schedule_time(ds, task_id, moment.strftime("%Y-%m-%d"), moment.hour,
                            moment.minute, now)
    task["remindAt"] = again
    tasks._touch(task, now)


def pending(ds):
    """(remindAt, task id) of every open task with a reminder, earliest first."""
    return sorted((int(t["remindAt"]), t["id"]) for t in ds.tasks.values()
                  if isinstance(t.get("remindAt"), (int, float)) and not t.get("isDone"))


def due(ds, now=None):
    """Ids of the open tasks whose reminder has come."""
    now = now or dates.now_ms()
    return [task_id for at, task_id in pending(ds) if at <= now]


def next_at(ds, now=None):
    """When the next reminder comes, or None."""
    now = now or dates.now_ms()
    return next((at for at, _ in pending(ds) if at > now), None)


def expected(ds):
    """Whether a reminder is waiting or will come: an open task has one,
    or a repeat rule that is not paused gives its instances one."""
    if pending(ds):
        return True
    return any(not cfg.get("isPaused") and rule_time(cfg)[1] != NONE
               for cfg in ds.data["taskRepeatCfg"]["entities"].values())


def rule_time(cfg):
    """(startTime, option) of a repeat rule as its instances get them: a
    reminder needs both a valid time and an option with a time."""
    start = cfg.get("startTime")
    if not instances._valid_time(start):
        return None, NONE
    option = cfg.get("remindAt")
    return start, option if option in LEAD_MINUTES else NONE


def set_rule_time(ds, cfg_id, start_time, option, today, now=None):
    """A repeat rule's time of day and reminder. With both, the open
    instance created today moves to that time with its reminder, as
    Super Productivity reschedules it; without a time the rule loses
    both and the instances stay as they are."""
    now = now or dates.now_ms()
    cfg = ds.data["taskRepeatCfg"]["entities"][cfg_id]
    if not instances._valid_time(start_time):
        cfg.pop("startTime", None)
        cfg.pop("remindAt", None)
        return
    cfg["startTime"] = start_time
    if option not in LEAD_MINUTES:
        cfg.pop("remindAt", None)
        return
    cfg["remindAt"] = option
    for task in instances.live_instances(ds, cfg_id):
        if task.get("isDone") or ds.today(task.get("created", 0)) != today:
            continue
        moment = datetime.fromtimestamp(instances.due_with_time(
            start_time, today, dates.day_offset_ms(ds.config)) / 1000)
        planning.schedule_time(ds, task["id"], moment.strftime("%Y-%m-%d"), moment.hour,
                            moment.minute, now)
        set_option(ds, task["id"], option, now)
