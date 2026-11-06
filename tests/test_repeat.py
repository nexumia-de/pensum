"""Repeating tasks follow Super Productivity's rules (repeat schedule,
instance creation, making a task recurring, removing a rule) and keep
the dataset one that its import checks accept."""
import pytest

from pensum.store import defaults, tasks, validate
from pensum.store.dataset import Context, Dataset
from pensum.store.repeat import instances, rules, schedule
from pensum.store.repeat.instances import noon_ms

NOW = noon_ms("2026-11-04") + 3_600_000  # Wednesday 4 November 2026, 13:00


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def valid(ds):
    assert validate.problems(ds.data) == []


def rule(**fields):
    cfg = defaults.get("taskRepeatCfg")
    cfg.update(id="r", title="Walk", lastTaskCreationDay="1970-01-01")
    cfg.update(fields)
    return cfg


def add_rule(ds, **fields):
    cfg = rule(**fields)
    ds.data["taskRepeatCfg"]["ids"].append(cfg["id"])
    ds.data["taskRepeatCfg"]["entities"][cfg["id"]] = cfg
    return cfg


WORKDAYS = dict(repeatCycle="WEEKLY", saturday=False, sunday=False)


@pytest.mark.parametrize("fields, today, expected", [
    (dict(repeatCycle="DAILY", startDate="2026-11-01"), "2026-11-04", "2026-11-04"),
    (dict(repeatCycle="DAILY", repeatEvery=3, startDate="2026-11-01"), "2026-11-06", "2026-11-04"),
    (dict(repeatCycle="DAILY", lastTaskCreationDay="2026-11-04"), "2026-11-04", None),
    (dict(repeatCycle="DAILY", startDate="2026-11-10"), "2026-11-04", None),
    (dict(WORKDAYS, startDate="2026-11-01"), "2026-11-08", "2026-11-06"),  # Sunday → Friday
    (dict(WORKDAYS, startDate="2026-11-01", lastTaskCreationDay="2026-11-06"), "2026-11-08", None),
    (dict(repeatCycle="WEEKLY", repeatEvery=2, startDate="2026-11-02", monday=True,
          tuesday=False, wednesday=False, thursday=False, friday=False),
     "2026-11-12", "2026-11-02"),
    (dict(repeatCycle="MONTHLY", startDate="2026-01-31"), "2026-02-28", "2026-02-28"),
    (dict(repeatCycle="MONTHLY", startDate="2026-01-31"), "2026-03-15", "2026-02-28"),
    (dict(repeatCycle="MONTHLY", startDate="2026-01-10", monthlyLastDay=True), "2026-04-30",
     "2026-04-30"),
    (dict(repeatCycle="MONTHLY", startDate="2026-01-01", monthlyWeekOfMonth=1,
          monthlyWeekday=1), "2026-11-04", "2026-11-02"),  # first Monday
    (dict(repeatCycle="MONTHLY", startDate="2026-01-01", monthlyWeekOfMonth=-1,
          monthlyWeekday=5), "2026-11-04", "2026-10-30"),  # last Friday
    (dict(repeatCycle="YEARLY", startDate="2024-02-29"), "2027-03-01", "2027-02-28"),
    (dict(repeatCycle="DAILY", startDate="2026-11-01", repeatUntilDay="2026-11-02"),
     "2026-11-04", "2026-11-02"),
    (dict(repeatCycle="DAILY", repeatEvery=0), "2026-11-04", None),
])
def test_newest_due_day(fields, today, expected):
    assert schedule.newest_due_day(rule(**fields), today) == expected


@pytest.mark.parametrize("fields, expected", [
    (dict(repeatCycle="DAILY", startDate="2026-11-04"), "2026-11-04"),
    (dict(WORKDAYS, startDate="2026-11-07"), "2026-11-09"),  # Saturday → Monday
    (dict(repeatCycle="MONTHLY", startDate="2026-02-10", monthlyLastDay=True), "2026-02-28"),
    (dict(repeatCycle="MONTHLY", startDate="2026-11-10", monthlyWeekOfMonth=1,
          monthlyWeekday=1), "2026-12-07"),
    (dict(repeatCycle="DAILY"), None),
    (dict(WORKDAYS, startDate="2026-11-07", repeatUntilDay="2026-11-08"), None),
])
def test_first_day(fields, expected):
    assert schedule.first_day(rule(**fields)) == expected


def test_creates_one_instance_like_super_productivity(ds):
    add_rule(ds, repeatCycle="DAILY", startDate="2026-11-01", defaultEstimate=900_000,
             notes="Around the block", priority="high")
    created = instances.create_due(ds, NOW)
    assert [t["id"] for t in created] == ["rpt_r_2026-11-04"]
    task = created[0]
    assert task["repeatCfgId"] == "r"
    assert task["dueDay"] == "2026-11-04"
    assert task["created"] == noon_ms("2026-11-04")
    assert (task["timeEstimate"], task["notes"], task["priority"]) == (900_000, "Around the block", 3)
    assert task["id"] in ds.project_entities[defaults.INBOX_ID]["taskIds"]
    assert ds.list_tasks(Context.today(), "2026-11-04")[0] == [task]
    cfg = ds.data["taskRepeatCfg"]["entities"]["r"]
    assert cfg["lastTaskCreationDay"] == "2026-11-04"
    assert instances.create_due(ds, NOW) == []  # idempotent
    valid(ds)


def test_missed_days_are_not_backfilled(ds):
    add_rule(ds, repeatCycle="WEEKLY", startDate="2026-10-01", lastTaskCreationDay="2026-10-01")
    created = instances.create_due(ds, NOW)
    assert [t["dueDay"] for t in created] == ["2026-11-04"]


def test_skip_overdue_only_moves_the_cursor(ds):
    cfg = add_rule(ds, repeatCycle="DAILY", repeatEvery=7, startDate="2026-11-02",
                   skipOverdue=True)
    assert instances.create_due(ds, NOW) == []
    assert cfg["lastTaskCreationDay"] == "2026-11-02"


def test_paused_skipped_and_waiting_rules_create_nothing(ds):
    add_rule(ds, id="p", repeatCycle="DAILY", isPaused=True)
    add_rule(ds, id="s", repeatCycle="DAILY", deletedInstanceDates=["2026-11-04"])
    wait = add_rule(ds, id="w", repeatCycle="DAILY", waitForCompletion=True)
    open_task = tasks.add_task(ds, "Walk", Context.today(), NOW - 86_400_000)
    open_task["repeatCfgId"] = "w"
    open_task["created"] = noon_ms("2026-11-03")
    assert instances.create_due(ds, NOW) == []
    tasks.set_done(ds, open_task["id"], True, NOW)  # completing lets the next one come
    assert "rpt_w_2026-11-04" in ds.tasks
    assert wait["lastTaskCreationDay"] == "2026-11-04"
    valid(ds)


def test_timed_rule_and_subtasks(ds):
    add_rule(ds, repeatCycle="DAILY", startTime="08:30", remindAt="m10",
             shouldInheritSubtasks=True,
             subTaskTemplates=[{"title": "Shoes", "timeEstimate": 60_000}])
    task = instances.create_due(ds, NOW)[0]
    assert "dueDay" not in task
    assert task["dueWithTime"] == noon_ms("2026-11-04") - 3.5 * 3_600_000
    assert task["remindAt"] == task["dueWithTime"] - 600_000
    sub = ds.tasks["rpt_r_2026-11-04_sub_0"]
    assert (sub["title"], sub["parentId"]) == ("Shoes", task["id"])
    assert task["timeEstimate"] == 60_000
    valid(ds)


def test_repeat_from_completion_restarts_the_series(ds):
    cfg = add_rule(ds, repeatCycle="DAILY", repeatEvery=3, startDate="2026-10-01",
                   repeatFromCompletionDate=True)
    task = instances.create_due(ds, NOW - 2 * 86_400_000)[0]
    tasks.set_done(ds, task["id"], True, NOW)
    assert (cfg["startDate"], cfg["lastTaskCreationDay"]) == ("2026-11-04", "2026-11-04")


def test_make_recurring_today_keeps_the_task(ds):
    task = tasks.add_task(ds, "Walk", Context.today(), NOW)
    tasks.add_subtask(ds, task["id"], "Shoes", NOW)
    cfg = rules.make_recurring(ds, task["id"], rules.schedule_fields("DAILY", "2026-11-04"), NOW)
    assert task["repeatCfgId"] == cfg["id"]
    assert (cfg["title"], cfg["repeatCycle"], cfg["skipOverdue"]) == ("Walk", "DAILY", True)
    assert cfg["lastTaskCreationDay"] == "2026-11-04"
    assert cfg["subTaskTemplates"][0]["title"] == "Shoes"
    assert task["dueDay"] == "2026-11-04"
    assert instances.create_due(ds, NOW) == []  # today is covered by the task itself
    valid(ds)


def test_make_recurring_on_workdays_moves_a_weekend_task(ds):
    task = tasks.add_task(ds, "Plan", Context.today(), NOW)
    fields = rules.schedule_fields("MONDAY_TO_FRIDAY", "2026-11-07")
    assert fields["skipOverdue"] is False
    rules.make_recurring(ds, task["id"], fields, NOW)
    assert task["dueDay"] == "2026-11-09"
    assert task["created"] == noon_ms("2026-11-09")
    assert ds.list_tasks(Context.today(), "2026-11-04")[0] == []
    valid(ds)


def test_custom_schedules():
    every = rules.schedule_fields("CUSTOM", "2026-11-04", every=2, cycle="DAILY")
    assert (every["repeatCycle"], every["repeatEvery"], every["skipOverdue"]) == ("DAILY", 2, False)
    days = rules.schedule_fields("CUSTOM", "2026-11-04", cycle="WEEKLY",
                                 weekdays=("monday", "thursday"))
    assert [d for d in schedule.WEEKDAYS if days[d]] == ["monday", "thursday"]


def test_delete_rule_keeps_tasks_without_null(ds):
    add_rule(ds, repeatCycle="DAILY")
    task = instances.create_due(ds, NOW)[0]
    ds.data["archiveYoung"]["task"]["entities"]["old"] = {"id": "old", "repeatCfgId": "r"}
    saved = rules.snapshot(ds, "r")
    rules.delete(ds, "r", NOW)
    assert "repeatCfgId" not in task
    assert "repeatCfgId" not in ds.data["archiveYoung"]["task"]["entities"]["old"]
    assert ds.data["taskRepeatCfg"]["ids"] == []
    del ds.data["archiveYoung"]["task"]["entities"]["old"]
    valid(ds)
    rules.restore(ds, saved)
    assert task["repeatCfgId"] == "r" and ds.data["taskRepeatCfg"]["ids"] == ["r"]
    valid(ds)
