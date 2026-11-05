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


def test_overdue_tasks(ds):
    day = ds.today(NOW)
    old = tasks.add_task(ds, "old", Context.today(), NOW)
    tasks.schedule_day(ds, old["id"], dates.shift_day(day, -2), NOW)
    done = tasks.add_task(ds, "done", Context.today(), NOW)
    tasks.schedule_day(ds, done["id"], dates.shift_day(day, -1), NOW)
    tasks.set_done(ds, done["id"], True, NOW)
    assert [t["id"] for t in ds.overdue_tasks(day)] == [old["id"]]
    tasks.schedule_day(ds, old["id"], day, NOW)
    assert ds.overdue_tasks(day) == []
    assert ds.top_level_ids(Context.today(), day) == [old["id"]]


def test_priority_reads_words_and_writes_numbers(ds):
    task = tasks.add_task(ds, "p", Context.today(), NOW)
    assert tasks.priority_level(task) == 0
    task["priority"] = "high"
    assert tasks.priority_level(task) == 3
    tasks.set_priority(ds, task["id"], 3)
    assert task["priority"] == "high"  # same meaning: stored form kept
    tasks.set_priority(ds, task["id"], 1)
    assert task["priority"] == 1
    tasks.set_priority(ds, task["id"], 0)
    assert task["priority"] is None
    valid(ds)


def test_set_time_on_day(ds):
    parent = tasks.add_task(ds, "P", Context.today(), NOW)
    sub = tasks.add_subtask(ds, parent["id"], "S", NOW)
    assert tracking.set_time_on_day(ds, sub["id"], "2026-05-01", 3_600_000)
    assert parent["timeSpent"] == 3_600_000
    assert not tracking.set_time_on_day(ds, parent["id"], "2026-05-01", 1)
    tracking.set_time_on_day(ds, sub["id"], "2026-05-01", 0)
    assert sub["timeSpentOnDay"] == {} and parent["timeSpent"] == 0
    valid(ds)


def test_finish_day_archives_done_tasks(ds):
    from pensum.store import archive
    day = ds.today(NOW)
    parent = tasks.add_task(ds, "P", Context.today(), NOW)
    sub = tasks.add_subtask(ds, parent["id"], "S", NOW)
    tracking.add_time(ds, sub["id"], 60_000, NOW)
    ds.data["timeTracking"]["project"][defaults.INBOX_ID]["2026-05-01"] = {"s": 1, "e": 2}
    open_task = tasks.add_task(ds, "open", Context.today(), NOW)
    tasks.set_done(ds, parent["id"], True, NOW)
    done = archive.finishable(ds, Context.today(), day)
    assert [t["id"] for t in done] == [parent["id"]]
    assert archive.archive_tasks(ds, [parent["id"]], NOW) == 2
    assert set(ds.tasks) == {open_task["id"]}
    young = ds.data["archiveYoung"]
    # The first flush moves everything to archiveOld at once.
    old = ds.data["archiveOld"]
    archived = {**young["task"]["entities"], **old["task"]["entities"]}
    assert archived[sub["id"]]["doneOn"] == NOW and "dueDay" not in archived[parent["id"]]
    assert ds.data["timeTracking"]["project"][defaults.INBOX_ID] == {
        day: {"s": NOW - 60_000, "e": NOW}}
    assert "2026-05-01" in old["timeTracking"]["project"][defaults.INBOX_ID]
    # Time worked today still counts.
    assert tracking.day_total(ds, day) == 60_000
    valid(ds)


def test_young_archive_kept_until_flush_due(ds):
    from pensum.store import archive
    ds.data["archiveOld"]["lastTimeTrackingFlush"] = NOW - 86_400_000
    task = tasks.add_task(ds, "x", Context.today(), NOW)
    tasks.set_done(ds, task["id"], True, NOW)
    archive.archive_tasks(ds, [task["id"]], NOW)
    assert task["id"] in ds.data["archiveYoung"]["task"]["entities"]
    valid(ds)


def test_backlog(ds):
    project = contexts.add_project(ds, "B")
    ctx = Context("project", project["id"])
    a = tasks.add_task(ds, "a", ctx, NOW)
    b = tasks.add_task(ds, "b", ctx, NOW)
    assert tasks.set_backlog(ds, a["id"], True)
    assert project["isEnableBacklog"] and project["backlogTaskIds"] == [a["id"]]
    assert ds.top_level_ids(ctx) == [b["id"]]
    assert [t["id"] for t in ds.backlog_tasks(project["id"])] == [a["id"]]
    tasks.set_backlog(ds, b["id"], True)
    assert tasks.move(ds, a["id"], ctx, -1)
    assert project["backlogTaskIds"] == [a["id"], b["id"]]
    assert tasks.set_backlog(ds, a["id"], False)
    assert ds.top_level_ids(ctx) == [a["id"]]
    valid(ds)


def test_search_open_and_archived(ds):
    from pensum.store import archive
    from pensum.store.search import search
    a = tasks.add_task(ds, "Buy Tomato seeds", Context.today(), NOW)
    b = tasks.add_task(ds, "Water", Context.today(), NOW)
    tasks.update(ds, b["id"], notes="the tomatoes too")
    c = tasks.add_task(ds, "tomato soup", Context.today(), NOW)
    tasks.set_done(ds, c["id"], True, NOW)
    archive.archive_tasks(ds, [c["id"]], NOW)
    found = search(ds, "TOMATO")
    assert {t["id"] for t, archived in found if not archived} == {a["id"], b["id"]}
    assert [t["id"] for t, archived in found if archived] == [c["id"]]
    assert search(ds, "tomato seeds")[0][0]["id"] == a["id"]
    assert search(ds, "  ") == []


def test_deadline(ds):
    task = tasks.add_task(ds, "d", Context.today(), NOW)
    task["deadlineWithTime"] = NOW
    assert tasks.deadline_day(ds, task) == ds.today(NOW)
    tasks.set_deadline(ds, task["id"], "2026-06-01")
    assert tasks.deadline_day(ds, task) == "2026-06-01" and task["deadlineWithTime"] is None
    tasks.set_deadline(ds, task["id"], None)
    assert tasks.deadline_day(ds, task) is None
    valid(ds)


def test_schedule_time(ds):
    task = tasks.add_task(ds, "t", Context.today(), NOW)
    day = ds.today(NOW)
    tasks.schedule_time(ds, task["id"], day, 14, 30, NOW)
    assert "dueDay" not in task and task["hasPlannedTime"]
    assert ds.planned_day(task) == day and ds.is_due_today(task, day)
    assert task["id"] in ds.top_level_ids(Context.today(), day)
    tasks.clear_time(ds, task["id"], NOW)
    assert task["dueDay"] == day and "dueWithTime" not in task
    valid(ds)
