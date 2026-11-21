"""Task, project, tag and time changes keep the dataset one that Super
Productivity's import checks accept."""
import pytest

from pensum.store import (backup, contexts, dates, defaults, order, planning, tasks,
                          tracking, validate)
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


def test_new_tag_joins_the_tag_tree_like_super_productivity(ds):
    # addTag in menu-tree.reducer.ts appends to the tree, also an empty
    # one; found by the round trip through a real Super Productivity.
    assert ds.data["menuTree"]["tagTree"] == []
    first = contexts.add_tag(ds, "calls", NOW)
    second = contexts.add_tag(ds, "errands", NOW)
    assert ds.data["menuTree"]["tagTree"] == [{"id": first["id"], "k": "t"},
                                              {"id": second["id"], "k": "t"}]
    assert [t["id"] for t in ds.tags()] == [first["id"], second["id"]]
    valid(ds)


def test_schedule_move_and_tags(ds):
    task = tasks.add_task(ds, "Plan", Context.today(), NOW)
    tomorrow = dates.shift_day(ds.today(NOW), 1)
    planning.schedule_day(ds, task["id"], tomorrow, NOW)
    assert task["id"] not in ds.tag_entities[defaults.TODAY_ID]["taskIds"]
    assert ds.data["planner"]["days"][tomorrow] == [task["id"]]
    planning.schedule_day(ds, task["id"], None, NOW)
    assert "dueDay" not in task and ds.data["planner"]["days"][tomorrow] == []

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
    order.move(ds, b["id"], Context.today(), -1, ds.today(NOW))
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
    assert order.move(ds, c["id"], Context.today(), -100, day)
    assert ds.top_level_ids(Context.today(), day) == [c["id"], a["id"], b["id"]]
    assert order.move(ds, c["id"], Context.today(), 100, day)
    assert ds.top_level_ids(Context.today(), day) == [a["id"], b["id"], c["id"]]
    assert not order.move(ds, c["id"], Context.today(), 1, day)
    s1 = tasks.add_subtask(ds, a["id"], "s1", NOW)
    s2 = tasks.add_subtask(ds, a["id"], "s2", NOW)
    assert order.move(ds, s2["id"], None, -1)
    assert a["subTaskIds"] == [s2["id"], s1["id"]]
    project = Context("project", defaults.INBOX_ID)
    assert order.move(ds, a["id"], project, 1, day)
    valid(ds)


def test_overdue_tasks(ds):
    day = ds.today(NOW)
    old = tasks.add_task(ds, "old", Context.today(), NOW)
    planning.schedule_day(ds, old["id"], dates.shift_day(day, -2), NOW)
    done = tasks.add_task(ds, "done", Context.today(), NOW)
    planning.schedule_day(ds, done["id"], dates.shift_day(day, -1), NOW)
    tasks.set_done(ds, done["id"], True, NOW)
    assert [t["id"] for t in ds.overdue_tasks(day)] == [old["id"]]
    planning.schedule_day(ds, old["id"], day, NOW)
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
    assert order.move(ds, a["id"], ctx, -1)
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
    planning.schedule_time(ds, task["id"], day, 14, 30, NOW)
    assert "dueDay" not in task
    assert ds.planned_day(task) == day and ds.is_due_today(task, day)
    assert task["id"] in ds.top_level_ids(Context.today(), day)
    planning.clear_time(ds, task["id"], NOW)
    assert task["dueDay"] == day and "dueWithTime" not in task
    valid(ds)


def _at(day, hours, minutes):
    from datetime import datetime
    return int(datetime.combine(dates.parse_day(day), datetime.min.time()).replace(
        hour=hours, minute=minutes).timestamp() * 1000)


def test_schedule_time_writes_what_super_productivity_writes(ds):
    """scheduleTaskWithTime: dueWithTime set, dueDay and (without a
    reminder) remindAt removed, the planner's days without the task,
    Today's order with it on top or without it; nothing else."""
    import copy
    day = ds.today(NOW)
    tomorrow = dates.shift_day(day, 1)
    inbox = Context("project", defaults.INBOX_ID)
    first = tasks.add_task(ds, "first", Context.today(), NOW)
    task = tasks.add_task(ds, "t", inbox, NOW)
    planning.schedule_day(ds, task["id"], tomorrow, NOW)
    assert ds.data["planner"]["days"][tomorrow] == [task["id"]]
    before = copy.deepcopy(ds.data)
    today_order = ds.tag_entities[defaults.TODAY_ID]["taskIds"]

    # A time today: on top of Today's order, out of the planner.
    planning.schedule_time(ds, task["id"], day, 14, 30, NOW + 1)
    assert task["dueWithTime"] == _at(day, 14, 30)
    assert "dueDay" not in task and "remindAt" not in task
    assert today_order == [task["id"], first["id"]]
    assert ds.data["planner"]["days"][tomorrow] == []
    changed = {k for k in set(task) | set(before["task"]["entities"][task["id"]])
               if task.get(k, "-") != before["task"]["entities"][task["id"]].get(k, "-")}
    assert changed == {"dueWithTime", "dueDay", "modified"}
    for name in ds.data:
        if name not in ("task", "tag", "planner"):
            assert ds.data[name] == before[name], name
    assert ds.data["project"] == before["project"]
    assert before["task"]["entities"][first["id"]] == ds.tasks[first["id"]]
    valid(ds)

    # Another time the same day: the place in Today's order stays.
    today_order.remove(task["id"])
    today_order.append(task["id"])
    planning.schedule_time(ds, task["id"], day, 16, 0, NOW + 2)
    assert today_order == [first["id"], task["id"]]

    # A time on another day: out of Today's order, and not in the
    # planner's days (the time alone says the day).
    planning.schedule_time(ds, task["id"], tomorrow, 9, 0, NOW + 3)
    assert today_order == [first["id"]]
    assert ds.data["planner"]["days"][tomorrow] == []
    assert ds.planned_day(task) == tomorrow and "dueDay" not in task
    assert not ds.is_due_today(task, day)
    valid(ds)

    # A subtask at a time goes into Today's order as well.
    sub = tasks.add_subtask(ds, first["id"], "sub", NOW)
    planning.schedule_time(ds, sub["id"], day, 8, 0, NOW + 4)
    assert today_order == [sub["id"], first["id"]]
    assert "hasPlannedTime" not in task and "hasPlannedTime" not in sub
    valid(ds)


def test_unplan_and_clear_time_remove_the_optional_fields(ds):
    """unscheduleTask and planning for a day alone: dueWithTime and
    remindAt are removed, never null."""
    from pensum.store import reminders
    day = ds.today(NOW)
    task = tasks.add_task(ds, "t", Context("project", defaults.INBOX_ID), NOW)
    planning.schedule_time(ds, task["id"], day, 14, 30, NOW)
    reminders.set_option(ds, task["id"], "m15", NOW)
    assert task["remindAt"] == task["dueWithTime"] - 15 * 60_000
    # The reminder keeps its lead when the time moves.
    planning.schedule_time(ds, task["id"], day, 15, 0, NOW)
    assert task["remindAt"] == _at(day, 15, 0) - 15 * 60_000
    planning.clear_time(ds, task["id"], NOW)
    assert task["dueDay"] == day
    assert "dueWithTime" not in task and "remindAt" not in task
    assert task["id"] in ds.tag_entities[defaults.TODAY_ID]["taskIds"]
    valid(ds)
    planning.schedule_time(ds, task["id"], day, 14, 30, NOW)
    reminders.set_option(ds, task["id"], "m15", NOW)
    planning.schedule_day(ds, task["id"], None, NOW)
    assert "dueWithTime" not in task and "remindAt" not in task
    assert "dueDay" not in task
    assert task["id"] not in ds.tag_entities[defaults.TODAY_ID]["taskIds"]
    assert all(task["id"] not in ids for ids in ds.data["planner"]["days"].values())
    valid(ds)


def test_today_lists_timed_tasks_first_by_time(ds):
    day = ds.today(NOW)
    today = Context.today()
    a, b, c, d = (tasks.add_task(ds, n, today, NOW, top=False) for n in "abcd")
    stored = list(ds.tag_entities[defaults.TODAY_ID]["taskIds"])
    planning.schedule_time(ds, d["id"], day, 9, 0, NOW)
    planning.schedule_time(ds, b["id"], day, 16, 0, NOW)
    # The stored order is untouched: both were in Today already.
    assert ds.tag_entities[defaults.TODAY_ID]["taskIds"] == stored
    assert ds.top_level_ids(today, day) == stored
    shown = [t["id"] for t in ds.list_tasks(today, day)[0]]
    assert shown == [d["id"], b["id"], a["id"], c["id"]]
    # Tasks with a time follow the clock, the others move among themselves.
    assert order.siblings(ds, b["id"], today, day) == []
    assert not order.move(ds, b["id"], today, -1, day)
    assert order.siblings(ds, a["id"], today, day) == [a["id"], c["id"]]
    assert order.move_to(ds, c["id"], today, a["id"], day)
    assert [t["id"] for t in ds.list_tasks(today, day)[0]] == [
        d["id"], b["id"], c["id"], a["id"]]
    # A project's list keeps its own order.
    inbox = Context("project", defaults.INBOX_ID)
    assert [t["id"] for t in ds.list_tasks(inbox, day)[0]] == ds.top_level_ids(inbox, day)
    # Done, a task is no appointment any more.
    tasks.set_done(ds, d["id"], True, NOW)
    assert [t["id"] for t in ds.list_tasks(today, day)[0]] == [b["id"], c["id"], a["id"]]
    valid(ds)


def test_drop_writes_only_the_list_shown(ds):
    """Dropping a task on another one changes the one id list Super
    Productivity keeps for that list, and no task."""
    import copy
    day = ds.today(NOW)
    project = contexts.add_project(ds, "Garden")
    tag = contexts.add_tag(ds, "Outside", NOW)
    ctx = Context("project", project["id"])
    a, b, c, d = (tasks.add_task(ds, n, ctx, NOW, top=False) for n in "abcd")
    ids = [t["id"] for t in (a, b, c, d)]
    for task in (a, b, c):
        tasks.set_tags(ds, task["id"], [tag["id"]], NOW)
        planning.schedule_day(ds, task["id"], day, NOW)
    before = copy.deepcopy(ds.data)
    today_order = ds.tag_entities[defaults.TODAY_ID]["taskIds"]

    # Down: the task lands after the one it was dropped on.
    assert order.move_to(ds, ids[0], ctx, ids[2], day)
    assert project["taskIds"] == [ids[1], ids[2], ids[0], ids[3]]
    assert ds.tag_entities[tag["id"]]["taskIds"] == ids[:3]
    assert today_order == ids[:3]
    # Up: before it.
    assert order.move_to(ds, ids[3], ctx, ids[1], day)
    assert project["taskIds"] == [ids[3], ids[1], ids[2], ids[0]]
    assert order.move_to(ds, ids[2], Context("tag", tag["id"]), ids[0], day)
    assert ds.tag_entities[tag["id"]]["taskIds"] == [ids[2], ids[0], ids[1]]
    assert order.move_to(ds, ids[1], Context.today(), ids[0], day)
    assert today_order == [ids[1], ids[0], ids[2]]
    assert project["taskIds"] == [ids[3], ids[1], ids[2], ids[0]]
    assert ds.data["task"] == before["task"]
    valid(ds)

    # Not on itself, not on a task of another list.
    assert not order.move_to(ds, ids[0], ctx, ids[0], day)
    assert not order.move_to(ds, ids[3], Context.today(), ids[0], day)
    assert not order.move_to(ds, ids[0], Context.today(), ids[3], day)
    assert order.siblings(ds, ids[3], Context.today(), day) == []


def test_drop_among_subtasks_backlog_and_past_hidden_tasks(ds):
    project = contexts.add_project(ds, "Garden")
    ctx = Context("project", project["id"])
    a, b, c = (tasks.add_task(ds, n, ctx, NOW, top=False) for n in "abc")
    subs = [tasks.add_subtask(ds, a["id"], n, NOW)["id"] for n in ("s1", "s2", "s3")]
    assert order.move_to(ds, subs[2], None, subs[0])
    assert a["subTaskIds"] == [subs[2], subs[0], subs[1]]
    assert project["taskIds"] == [a["id"], b["id"], c["id"]]
    # A subtask is not dropped on a top-level task, nor the other way.
    assert not order.move_to(ds, subs[0], ctx, b["id"])
    assert not order.move_to(ds, b["id"], ctx, subs[0])
    tasks.set_backlog(ds, c["id"], True)
    tasks.set_backlog(ds, b["id"], True)
    assert project["backlogTaskIds"] == [b["id"], c["id"]]
    assert order.move_to(ds, c["id"], ctx, b["id"])
    assert project["backlogTaskIds"] == [c["id"], b["id"]]
    assert not order.move_to(ds, a["id"], ctx, b["id"])
    assert project["taskIds"] == [a["id"]]
    # Ids the list does not show (stale ones in Today's order) stay.
    day = ds.today(NOW)
    x, y, z = (tasks.add_task(ds, n, Context.today(), NOW, top=False) for n in "xyz")
    today_order = ds.tag_entities[defaults.TODAY_ID]["taskIds"]
    today_order.insert(1, "stale")
    assert order.move_to(ds, z["id"], Context.today(), x["id"], day)
    assert today_order == [z["id"], x["id"], "stale", y["id"]]
    # Super Productivity's rule: right after the task shown before it.
    assert order.move_to(ds, y["id"], Context.today(), x["id"], day)
    assert today_order == [z["id"], y["id"], x["id"], "stale"]
    assert order.move_to(ds, z["id"], Context.today(), x["id"], day)
    assert today_order == [y["id"], x["id"], z["id"], "stale"]
    today_order.remove("stale")
    valid(ds)


def _project(ds, names):
    project = contexts.add_project(ds, "P")
    ctx = Context("project", project["id"])
    ids = {n: tasks.add_task(ds, n, ctx, NOW, top=False)["id"] for n in names}
    return project, ctx, ids


def test_menu_moves_follow_super_productivity(ds):
    """Move Up and Down pass the done tasks and stop at the nearest task
    that is not done (arrayMoveLeftUntil, arrayMoveRightUntil); to the top
    and to the bottom go to the very start and end of the id list."""
    project, ctx, t = _project(ds, "aDbc")
    tasks.set_done(ds, t["D"], True, NOW)
    order_of = lambda: "".join(n for i in project["taskIds"]  # noqa: E731
                               for n, v in t.items() if v == i)
    assert order.move(ds, t["c"], ctx, -1) and order_of() == "aDcb"
    # Up past a done task: before the task that is not done above it.
    assert order.move(ds, t["c"], ctx, -1) and order_of() == "caDb"
    assert not order.move(ds, t["c"], ctx, -1) and order_of() == "caDb"
    # Down past a done task: after the next task that is not done.
    assert order.move(ds, t["a"], ctx, 1) and order_of() == "cDba"
    assert not order.move(ds, t["a"], ctx, 1) and order_of() == "cDba"
    assert order.move(ds, t["a"], ctx, -100) and order_of() == "acDb"
    assert order.move(ds, t["a"], ctx, 100) and order_of() == "cDba"
    assert not order.move(ds, t["a"], ctx, 100)
    # Only done tasks above: Super Productivity's step would move the id
    # without changing what is shown; Pensum writes nothing then.
    project["taskIds"][:] = [t["D"], t["c"], t["b"], t["a"]]
    assert not order.move(ds, t["c"], ctx, -1) and order_of() == "Dcba"
    assert order.siblings(ds, t["c"], ctx) == [t["c"], t["b"], t["a"]]
    assert order.siblings(ds, t["D"], ctx) == [t["D"]]
    valid(ds)


def test_menu_moves_of_subtasks_and_backlog(ds):
    project, ctx, t = _project(ds, "abc")
    subs = [tasks.add_subtask(ds, t["a"], n, NOW)["id"] for n in ("s1", "s2", "s3")]
    parent = ds.tasks[t["a"]]
    # Subtasks swap with their neighbour, done or not (arrayMoveLeft/Right).
    tasks.set_done(ds, subs[1], True, NOW)
    assert order.move(ds, subs[2], None, -1)
    assert parent["subTaskIds"] == [subs[0], subs[2], subs[1]]
    assert order.move(ds, subs[0], None, 100)
    assert parent["subTaskIds"] == [subs[2], subs[1], subs[0]]
    assert order.move(ds, subs[0], None, -100)
    assert parent["subTaskIds"] == [subs[0], subs[2], subs[1]]
    assert not order.move(ds, subs[0], None, -1)
    # The backlog passes its done tasks like the list does.
    for name in "cba":
        tasks.set_backlog(ds, t[name], True)
    assert project["backlogTaskIds"] == [t["a"], t["b"], t["c"]]
    tasks.set_done(ds, t["b"], True, NOW)
    assert order.move(ds, t["c"], ctx, -1)
    assert project["backlogTaskIds"] == [t["c"], t["a"], t["b"]]
    assert order.move(ds, t["c"], ctx, 1)
    assert project["backlogTaskIds"] == [t["a"], t["c"], t["b"]]
    valid(ds)


def test_list_moves_rules():
    """The helpers on plain id lists, with ids the list does not show."""
    from pensum.store import list_moves as lm
    kept = {"a", "b", "c"}
    assert lm.left_until(list("axxb"), "b", kept) == list("baxx")
    assert lm.left_until(list("xxb"), "b", kept) == list("bxx")  # none kept: first
    assert lm.left_until(list("bxa"), "b", kept) == list("bxa")
    assert lm.right_until(list("bxxa"), "b", kept) == list("xxab")
    assert lm.right_until(list("bxx"), "b", kept) == list("bxx")  # none kept: stays
    assert lm.to_start(list("xab"), "b") == list("bxa")
    assert lm.to_end(list("bax"), "b") == list("axb")
    assert lm.swap(list("abc"), "b", -1) == list("bac")
    assert lm.swap(list("abc"), "a", -1) == list("abc")
    # moveUndoneTaskUpInList: the not-done task right above (n) is gone
    # from the list, so the task takes its slot after the earlier one.
    assert lm.undone_up(list("axt"), "t", list("ant")) == list("atx")
    assert lm.undone_up(list("at"), "t", list("ant")) == list("at")
    assert lm.undone_up(list("axt"), "t", list("at")) == list("tax")
    assert lm.undone_down(list("txa"), "t", list("tna")) == list("xta")
    assert lm.undone_down(list("txa"), "t", list("ta")) == list("xat")
    ids = list("abc")
    lm.after_anchor(ids, "c", None)
    assert ids == list("cab")
    lm.after_anchor(ids, "c", "a")
    assert ids == list("acb")
    lm.after_anchor(ids, "c", "gone")
    assert ids == list("acb")
    lm.after_anchor(ids, "n", "gone")
    assert ids == list("acbn")
