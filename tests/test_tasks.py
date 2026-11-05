"""Task, project, tag and time changes keep the dataset one that Super
Productivity's import checks accept."""
import pytest

from pensum.store import backup, contexts, dates, defaults, tasks, tracking, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000  # 2026-05-28


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def valid(ds):
    assert validate.problems(ds.data) == []


def test_add_in_today_project_and_tag(ds):
    today = tasks.add_task(ds, " Write report ", Context.today(), NOW)
    assert today["title"] == "Write report"
    assert today["dueDay"] == ds.today(NOW)
    assert today["projectId"] == defaults.INBOX_ID
    assert defaults.TODAY_ID not in today["tagIds"]
    assert ds.list_tasks(Context.today(), ds.today(NOW))[0] == [today]

    project = contexts.add_project(ds, "Garden")
    in_project = tasks.add_task(ds, "Seeds", Context("project", project["id"]), NOW)
    assert ds.top_level_ids(Context("project", project["id"])) == [in_project["id"]]

    tag = contexts.add_tag(ds, "calls", NOW)
    tagged = tasks.add_task(ds, "Call Bob", Context("tag", tag["id"]), NOW)
    assert tagged["tagIds"] == [tag["id"]]
    assert ds.top_level_ids(Context("tag", tag["id"])) == [tagged["id"]]
    valid(ds)


def test_subtasks_sum_up_into_the_parent(ds):
    parent = tasks.add_task(ds, "Move", Context.today(), NOW)
    a = tasks.add_subtask(ds, parent["id"], "Boxes", NOW)
    b = tasks.add_subtask(ds, parent["id"], "Van", NOW)
    tasks.set_estimate(ds, a["id"], 3_600_000)
    tasks.set_estimate(ds, b["id"], 1_800_000)
    assert parent["timeEstimate"] == 5_400_000
    tracking.add_time(ds, a["id"], 600_000, NOW)
    assert parent["timeSpent"] == 600_000
    assert parent["timeEstimate"] == 4_800_000
    tasks.set_done(ds, b["id"], True, NOW)
    assert parent["timeEstimate"] == 3_000_000
    assert ds.top_level_ids(Context.today(), ds.today(NOW)) == [parent["id"]]
    valid(ds)
    tasks.delete(ds, parent["id"])
    assert not ds.tasks
    valid(ds)


def test_tracking_books_day_and_work_span(ds):
    project = contexts.add_project(ds, "Work")
    task = tasks.add_task(ds, "Code", Context("project", project["id"]), NOW)
    assert tracking.set_current(ds, task["id"])
    tracking.add_time(ds, task["id"], 60_000, NOW)
    day = ds.today(NOW)
    assert task["timeSpentOnDay"] == {day: 60_000} and task["timeSpent"] == 60_000
    span = ds.data["timeTracking"]["project"][project["id"]][day]
    assert span == {"s": NOW - 60_000, "e": NOW}
    # Worked on, so it is on today's list (isAutoAddWorkedOnToToday).
    assert ds.is_due_today(task, day)
    tasks.set_done(ds, task["id"], True, NOW)
    assert ds.current_task_id() is None and task["doneOn"] == NOW
    tasks.set_done(ds, task["id"], False, NOW)
    assert "doneOn" not in task
    valid(ds)


def test_parent_is_not_tracked_itself(ds):
    parent = tasks.add_task(ds, "P", Context.today(), NOW)
    tasks.add_subtask(ds, parent["id"], "S", NOW)
    assert not tracking.set_current(ds, parent["id"])


def test_schedule_move_and_tags(ds):
    task = tasks.add_task(ds, "Plan", Context.today(), NOW)
    tomorrow = dates.shift_day(ds.today(NOW), 1)
    tasks.schedule_day(ds, task["id"], tomorrow, NOW)
    assert task["id"] not in ds.tag_entities[defaults.TODAY_ID]["taskIds"]
    assert ds.data["planner"]["days"][tomorrow] == [task["id"]]
    tasks.schedule_day(ds, task["id"], None, NOW)
    assert task["dueDay"] is None and ds.data["planner"]["days"][tomorrow] == []

    project = contexts.add_project(ds, "Home")
    tasks.move_to_project(ds, task["id"], project["id"], NOW)
    assert task["id"] in ds.project_entities[project["id"]]["taskIds"]
    assert task["id"] not in ds.project_entities[defaults.INBOX_ID]["taskIds"]
    tag = contexts.add_tag(ds, "x", NOW)
    tasks.set_tags(ds, task["id"], [tag["id"], defaults.TODAY_ID])
    assert task["tagIds"] == [tag["id"]]
    valid(ds)
    contexts.delete_tag(ds, tag["id"])
    assert task["tagIds"] == []
    contexts.delete_project(ds, project["id"])
    assert task["id"] not in ds.tasks
    valid(ds)


def test_reorder(ds):
    a = tasks.add_task(ds, "a", Context.today(), NOW, top=False)
    b = tasks.add_task(ds, "b", Context.today(), NOW, top=False)
    tasks.move(ds, b["id"], Context.today(), -1, ds.today(NOW))
    assert ds.top_level_ids(Context.today(), ds.today(NOW)) == [b["id"], a["id"]]


def test_logical_day_respects_start_of_next_day(ds):
    ds.config["misc"]["startOfNextDayTime"] = "04:00"
    from datetime import datetime
    early = int(datetime(2026, 5, 28, 3, 0).timestamp() * 1000)
    assert ds.today(early) == "2026-05-27"


def test_changes_on_real_backup_stay_valid(sp_backup):
    ds = Dataset(backup.read(sp_backup))
    task = tasks.add_task(ds, "New", Context("project", defaults.INBOX_ID), NOW)
    tasks.add_subtask(ds, task["id"], "Sub", NOW)
    tasks.delete(ds, "active-task-1")
    valid(ds)


def test_move_to_edges_and_subtasks(ds):
    a, b, c = (tasks.add_task(ds, n, Context.today(), NOW, top=False) for n in "abc")
    day = ds.today(NOW)
    assert tasks.move(ds, c["id"], Context.today(), -100, day)
    assert ds.top_level_ids(Context.today(), day) == [c["id"], a["id"], b["id"]]
    assert tasks.move(ds, c["id"], Context.today(), 100, day)
    assert ds.top_level_ids(Context.today(), day) == [a["id"], b["id"], c["id"]]
    assert not tasks.move(ds, c["id"], Context.today(), 1, day)
    s1 = tasks.add_subtask(ds, a["id"], "s1", NOW)
    s2 = tasks.add_subtask(ds, a["id"], "s2", NOW)
    assert tasks.move(ds, s2["id"], None, -1)
    assert a["subTaskIds"] == [s2["id"], s1["id"]]
    project = Context("project", defaults.INBOX_ID)
    assert tasks.move(ds, a["id"], project, 1, day)
    valid(ds)
