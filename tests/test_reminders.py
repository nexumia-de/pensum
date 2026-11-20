"""Task reminders in the store (pensum/store/reminders.py): the dataset
stays valid for Super Productivity's import after every change (#13)."""
from datetime import datetime

from pensum.store import defaults, reminders, tasks, validate
from pensum.store.dataset import Context, Dataset
from pensum.store.repeat import instances, rules

DAY = "2026-11-20"
NOON = int(datetime(2026, 11, 20, 12, 0).timestamp() * 1000)


def fresh():
    return Dataset(defaults.fresh_dataset(NOON))


def timed(ds, hours=15, minutes=0):
    task = tasks.add_task(ds, "Call the plumber", Context.today(), now=NOON)
    tasks.schedule_time(ds, task["id"], DAY, hours, minutes, now=NOON)
    return ds.tasks[task["id"]]


def test_a_reminder_is_a_lead_before_the_time():
    ds = fresh()
    task = timed(ds)
    assert reminders.option_of(task) == "DoNotRemind" and "remindAt" not in task
    reminders.set_option(ds, task["id"], "m15", NOON)
    assert task["remindAt"] == task["dueWithTime"] - 15 * 60_000
    assert reminders.option_of(task) == "m15"
    assert reminders.pending(ds) == [(task["remindAt"], task["id"])]
    assert reminders.due(ds, NOON) == [] and reminders.next_at(ds, NOON) == task["remindAt"]
    assert reminders.due(ds, task["remindAt"]) == [task["id"]]
    assert validate.problems(ds.data) == []
    # The lead stays when the time moves; a day without a time drops it.
    tasks.schedule_time(ds, task["id"], DAY, 16, 30, now=NOON)
    assert reminders.option_of(task) == "m15"
    tasks.clear_time(ds, task["id"], NOON)
    assert "remindAt" not in task and task["dueDay"] == DAY
    assert validate.problems(ds.data) == []


def test_no_reminder_without_a_time_and_dismiss_keeps_the_time():
    ds = fresh()
    plain = tasks.add_task(ds, "Buy seeds", Context.today(), now=NOON)
    reminders.set_option(ds, plain["id"], "AtStart", NOON)
    assert "remindAt" not in ds.tasks[plain["id"]]
    task = timed(ds)
    reminders.set_option(ds, task["id"], "AtStart", NOON)
    due = task["dueWithTime"]
    reminders.dismiss(ds, task["id"], NOON)
    assert "remindAt" not in task and task["dueWithTime"] == due
    assert validate.problems(ds.data) == []


def test_snooze_and_done():
    ds = fresh()
    task = timed(ds)
    reminders.set_option(ds, task["id"], "AtStart", NOON)
    late = task["dueWithTime"] + 60_000
    reminders.snooze(ds, task["id"], 10, late)
    assert task["remindAt"] == late + 600_000 and reminders.option_of(task) == "custom"
    assert reminders.due(ds, late) == []
    # A task without a time is planned at the snoozed moment.
    plain = tasks.add_task(ds, "Buy seeds", Context.today(), now=NOON)
    reminders.snooze(ds, plain["id"], 10, NOON)
    assert ds.tasks[plain["id"]]["dueWithTime"] == ds.tasks[plain["id"]]["remindAt"]
    assert "dueDay" not in ds.tasks[plain["id"]]
    # A done task no longer reminds.
    tasks.set_done(ds, task["id"], True, late)
    assert task["id"] not in [i for _, i in reminders.pending(ds)]
    assert validate.problems(ds.data) == []


def test_a_repeat_rule_gives_its_instances_a_time_and_a_reminder():
    ds = fresh()
    task = tasks.add_task(ds, "Water the plants", Context.today(), now=NOON)
    cfg = rules.make_recurring(ds, task["id"], rules.schedule_fields("DAILY", DAY), now=NOON)
    assert reminders.rule_time(cfg) == (None, "DoNotRemind")
    reminders.set_rule_time(ds, cfg["id"], "21:30", "m10", DAY, NOON)
    assert reminders.rule_time(cfg) == ("21:30", "m10")
    live = ds.tasks[task["id"]]
    assert datetime.fromtimestamp(live["dueWithTime"] / 1000).strftime("%H:%M") == "21:30"
    assert live["remindAt"] == live["dueWithTime"] - 600_000 and "dueDay" not in live
    assert validate.problems(ds.data) == []
    # The next day's instance gets both from the rule.
    tasks.set_done(ds, task["id"], True, NOON)
    tomorrow = "2026-11-21"
    new = instances.create_for(ds, cfg, tomorrow, NOON + 86_400_000)
    assert new and reminders.option_of(new) == "m10"
    # A time without a reminder option, then no time at all.
    reminders.set_rule_time(ds, cfg["id"], "21:30", "DoNotRemind", tomorrow, NOON)
    assert cfg["startTime"] == "21:30" and "remindAt" not in cfg
    reminders.set_rule_time(ds, cfg["id"], "", "m10", tomorrow, NOON)
    assert "startTime" not in cfg and "remindAt" not in cfg
    assert validate.problems(ds.data) == []
