"""Sections in a list, as Super Productivity's section reducers keep them
(docs/super-productivity-data.md)."""
import copy

import pytest

from pensum.store import archive, contexts, defaults, order, sections, tasks, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000  # 2026-05-28


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def valid(ds):
    assert validate.problems(ds.data) == []


def garden(ds, names="abcd"):
    project = contexts.add_project(ds, "Garden")
    ctx = Context("project", project["id"])
    ids = [tasks.add_task(ds, n, ctx, NOW, top=False)["id"] for n in names]
    return project, ctx, ids


def test_add_rename_collapse_delete(ds):
    project, ctx, ids = garden(ds)
    before = copy.deepcopy(ds.data)
    beds = sections.add(ds, ctx, "  Beds  ")
    assert beds == {"id": beds["id"], "contextId": project["id"], "contextType": "PROJECT",
                    "title": "Beds", "isExpanded": True, "taskIds": []}
    today = sections.add(ds, Context.today(), "x" * 300)
    assert (today["contextType"], today["contextId"]) == ("TAG", defaults.TODAY_ID)
    assert len(today["title"]) == 200
    assert ds.data["section"]["ids"] == [beds["id"], today["id"]]
    assert set(ds.data["section"]["entities"]) == {beds["id"], today["id"]}
    # Only projects and Today have sections.
    tag = contexts.add_tag(ds, "calls", NOW)
    assert sections.add(ds, Context("tag", tag["id"]), "No") is None
    assert sections.of_context(ds, Context("tag", tag["id"])) == []
    assert [s["id"] for s in sections.of_context(ds, ctx)] == [beds["id"]]

    sections.rename(ds, beds["id"], " Raised Beds ")
    sections.set_expanded(ds, beds["id"], False)
    assert beds["title"] == "Raised Beds" and beds["isExpanded"] is False
    assert not sections.is_expanded(beds) and sections.is_expanded({"taskIds": []})
    valid(ds)

    # Deleting a section leaves its tasks in the list, in no section.
    assert order.to_section(ds, ids[1], ctx, beds["id"])
    sections.delete(ds, beds["id"])
    assert ds.data["section"]["ids"] == [today["id"]]
    assert project["taskIds"] == ids and ids[1] in ds.tasks
    sections.delete(ds, today["id"])
    ds.data["tag"]["ids"].remove(tag["id"])
    del ds.data["tag"]["entities"][tag["id"]]
    ds.data["menuTree"] = before["menuTree"]
    assert ds.data == before
    valid(ds)


def test_tasks_move_into_inside_and_out_of_sections(ds):
    project, ctx, (a, b, c, d) = garden(ds)
    beds = sections.add(ds, ctx, "Beds")
    trees = sections.add(ds, ctx, "Trees")
    tasks_before = copy.deepcopy(ds.data["task"])

    # Into a section: last in it; the project's own order stays.
    assert order.to_section(ds, b, ctx, beds["id"])
    assert order.to_section(ds, d, ctx, beds["id"])
    assert beds["taskIds"] == [b, d] and project["taskIds"] == [a, b, c, d]
    assert order.to_section(ds, a, ctx, beds["id"], first=True)
    assert beds["taskIds"] == [a, b, d]
    assert not order.to_section(ds, a, ctx, beds["id"])

    # The list shows the tasks in no section first, then each section's.
    open_tasks = ds.list_tasks(ctx)[0]
    loose, groups = sections.group(ds, ctx, open_tasks)
    assert [t["id"] for t in loose] == [c]
    assert [(s["id"], [t["id"] for t in ts]) for s, ts in groups] == [
        (beds["id"], [a, b, d]), (trees["id"], [])]

    # A drop inside the section changes only the section's order.
    assert order.siblings(ds, a, ctx) == [a, b, d]
    assert order.move_to(ds, d, ctx, a)
    assert beds["taskIds"] == [d, a, b] and project["taskIds"] == [a, b, c, d]
    assert order.move_to(ds, d, ctx, b)
    assert beds["taskIds"] == [a, b, d]

    # A drop on a task of another section: out of the source, into the
    # target at that task's place.
    assert order.to_section(ds, c, ctx, trees["id"])
    assert order.move_to(ds, a, ctx, c)
    assert trees["taskIds"] == [a, c] and beds["taskIds"] == [b, d]
    assert project["taskIds"] == [a, b, c, d]

    # A drop on a task in no section: out of the section, and in the
    # project's order right after the task shown before the drop place.
    assert order.to_section(ds, c, ctx, None)
    assert trees["taskIds"] == [a] and project["taskIds"] == [a, b, c, d]
    assert order.siblings(ds, c, ctx) == [c]
    assert order.move_to(ds, d, ctx, c)
    assert beds["taskIds"] == [b] and project["taskIds"] == [d, a, b, c]
    assert order.siblings(ds, c, ctx) == [d, c]
    # And from no section onto a task in a section.
    assert order.move_to(ds, c, ctx, b)
    assert beds["taskIds"] == [c, b] and project["taskIds"] == [d, a, b, c]

    # The menu's Move Down inside a section keeps both orders in step.
    assert order.move(ds, c, ctx, 1)
    assert beds["taskIds"] == [b, c] and project["taskIds"] == [d, a, b, c]
    assert order.move(ds, c, ctx, -1)
    assert beds["taskIds"] == [c, b] and project["taskIds"] == [d, a, c, b]

    assert ds.data["task"] == tasks_before
    valid(ds)

    # Subtasks and backlog tasks are in no section.
    sub = tasks.add_subtask(ds, a, "sub", NOW)["id"]
    assert not order.to_section(ds, sub, ctx, beds["id"])
    tasks.set_backlog(ds, d, True)
    assert not order.to_section(ds, d, ctx, beds["id"])
    assert not order.move_to(ds, d, ctx, b)
    valid(ds)


def test_sections_let_go_of_tasks_that_leave(ds):
    project, ctx, (a, b, c, d) = garden(ds)
    other = contexts.add_project(ds, "Other")
    beds = sections.add(ds, ctx, "Beds")
    today = sections.add(ds, Context.today(), "Morning")
    day = ds.today(NOW)
    sub = tasks.add_subtask(ds, a, "sub", NOW)["id"]
    for task_id in (a, b, c, d):
        order.to_section(ds, task_id, ctx, beds["id"])
        tasks.schedule_day(ds, task_id, day, NOW)
        assert order.to_section(ds, task_id, Context.today(), today["id"], today=day)
    assert beds["taskIds"] == [a, b, c, d] == today["taskIds"]

    # Another project: out of the old project's sections, not of Today's.
    tasks.move_to_project(ds, a, other["id"], NOW)
    assert beds["taskIds"] == [b, c, d] and today["taskIds"] == [a, b, c, d]
    assert ds.tasks[sub]["projectId"] == other["id"]
    # Not planned for today any more: out of Today's sections only.
    tasks.schedule_day(ds, b, None, NOW)
    assert today["taskIds"] == [a, c, d] and beds["taskIds"] == [b, c, d]
    tasks.schedule_time(ds, c, dates_shift(day), 9, 0, NOW)
    assert today["taskIds"] == [a, d] and beds["taskIds"] == [b, c, d]
    # Deleted or archived: out of every section.
    tasks.delete(ds, d)
    assert today["taskIds"] == [a] and beds["taskIds"] == [b, c]
    tasks.set_done(ds, c, True, NOW)
    archive.archive_tasks(ds, [c])
    assert beds["taskIds"] == [b]
    valid(ds)
    # A deleted project takes its sections with it.
    contexts.delete_project(ds, project["id"])
    assert ds.data["section"]["ids"] == [today["id"]]
    assert set(ds.data["section"]["entities"]) == {today["id"]}
    valid(ds)


def dates_shift(day):
    from pensum.store import dates
    return dates.shift_day(day, 1)


def test_today_sections_and_timed_tasks(ds):
    day = ds.today(NOW)
    today = Context.today()
    a, b, c = (tasks.add_task(ds, n, today, NOW, top=False)["id"] for n in "abc")
    morning = sections.add(ds, today, "Morning")
    tasks.schedule_time(ds, c, day, 9, 0, NOW)
    tasks.schedule_time(ds, b, day, 8, 0, NOW)
    # Without a section the clock orders the timed tasks ...
    assert [t["id"] for t in ds.list_tasks(today, day)[0]] == [b, c, a]
    assert order.siblings(ds, b, today, day) == []
    # ... inside a section its own order does.
    assert order.to_section(ds, c, today, morning["id"], today=day)
    assert order.to_section(ds, b, today, morning["id"], today=day)
    assert order.siblings(ds, b, today, day) == [c, b]
    loose, groups = sections.group(ds, today, ds.list_tasks(today, day)[0])
    assert [t["id"] for t in loose] == [a]
    assert [t["id"] for t in groups[0][1]] == [c, b]
    valid(ds)


def test_sections_survive_reading_as_they_are(sp_backup):
    """Sections of lists that cannot have them, stale ids and a missing
    isExpanded are kept as read and shown without harm."""
    from pensum.store import backup
    ds = Dataset(backup.read(sp_backup))
    project_id = ds.data["project"]["ids"][0]
    ctx = Context("project", project_id)
    ds.data["section"]["ids"] += ["s1", "s2"]
    ds.data["section"]["entities"]["s1"] = {
        "id": "s1", "contextId": project_id, "contextType": "PROJECT",
        "title": "Kept", "taskIds": ["gone"]}
    ds.data["section"]["entities"]["s2"] = {
        "id": "s2", "contextId": "some-tag", "contextType": "TAG",
        "title": "Other", "taskIds": []}
    before = copy.deepcopy(ds.data["section"])
    loose, groups = sections.group(ds, ctx, ds.list_tasks(ctx)[0])
    assert [s["id"] for s, _ in groups] == ["s1"] and groups[0][1] == []
    assert sections.is_expanded(groups[0][0])
    assert ds.data["section"] == before
