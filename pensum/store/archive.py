"""Finish the day: move done tasks into the archive and older time
tracking with them, the way Super Productivity's ArchiveService does
(src/app/features/archive/archive.service.ts, util/sort-data-to-flush.ts).
No GTK."""
from pensum.store import dates

# Archive flush thresholds of Super Productivity.
ALL_YOUNG_TO_OLD_MS = 14 * 86_400_000
TASK_YOUNG_TO_OLD_MS = 21 * 86_400_000
_ARCHIVE_DROP = ("reminderId", "dueWithTime", "dueDay", "_hideSubTasksMode")


def _drop(values, value):
    while value in values:
        values.remove(value)


def finishable(ds, context, today=None):
    """Done top-level tasks of a list: what Finish Day archives."""
    return ds.list_tasks(context, today)[1]


def archive_tasks(ds, task_ids, now=None):
    """Move top-level tasks with their subtasks into archiveYoung. Returns
    the number of tasks moved (subtasks included)."""
    now = now or dates.now_ms()
    young = ds.data["archiveYoung"]
    moved = []
    for task_id in task_ids:
        task = ds.tasks.get(task_id)
        if not task or task.get("parentId"):
            continue
        parent_done = task.get("doneOn") or now
        for item in [task] + ds.subtasks(task):
            archived = dict(item)
            for key in _ARCHIVE_DROP:
                archived.pop(key, None)
            archived["isDone"] = True
            archived["doneOn"] = item.get("doneOn") or (
                parent_done if item.get("parentId") else now)
            young["task"]["entities"][item["id"]] = archived
            moved.append(item["id"])
    if not moved:
        return 0
    young["task"]["ids"] = sorted(set(young["task"]["ids"]) | set(moved))
    gone = set(moved)
    for task_id in moved:
        ds.tasks.pop(task_id, None)
    ds.data["task"]["ids"] = [i for i in ds.data["task"]["ids"] if i not in gone]
    if ds.data["task"].get("currentTaskId") in gone:
        ds.data["task"]["currentTaskId"] = None
    for entity in list(ds.project_entities.values()) + list(ds.tag_entities.values()):
        for key in ("taskIds", "backlogTaskIds"):
            if key in entity:
                entity[key] = [i for i in entity[key] if i not in gone]
    for section in ds.data["section"]["entities"].values():
        section["taskIds"] = [i for i in section.get("taskIds", []) if i not in gone]
    for day, ids in ds.data["planner"]["days"].items():
        ds.data["planner"]["days"][day] = [i for i in ids if i not in gone]
    ds.data["reminders"] = [r for r in ds.data["reminders"]
                            if r.get("relatedId") not in gone]
    _time_tracking_to_young(ds, dates.day_str(now))
    young["lastFlush"] = now
    _flush_young_to_old_if_due(ds, now)
    return len(moved)


def _time_tracking_to_young(ds, today):
    """Every work span except today's moves into archiveYoung."""
    current = ds.data["timeTracking"]
    archive = ds.data["archiveYoung"].setdefault("timeTracking", {})
    for category in ("project", "tag"):
        current.setdefault(category, {})
        target = archive.setdefault(category, {})
        for context_id, days in current[category].items():
            bucket = target.setdefault(context_id, {})
            for day in [d for d in days if d != today]:
                bucket[day] = days.pop(day)


def _flush_young_to_old_if_due(ds, now):
    young, old = ds.data["archiveYoung"], ds.data["archiveOld"]
    last = old.get("lastTimeTrackingFlush")
    if last is not None and now - last <= ALL_YOUNG_TO_OLD_MS:
        return
    young_tasks, old_tasks = young["task"]["entities"], old["task"]["entities"]
    for task in [t for t in young_tasks.values() if not t.get("parentId")
                 and (not t.get("doneOn") or now - t["doneOn"] > TASK_YOUNG_TO_OLD_MS)]:
        for item_id in [task["id"]] + list(task.get("subTaskIds", ())):
            if item_id in young_tasks:
                old_tasks[item_id] = young_tasks.pop(item_id)
    young["task"]["ids"] = [i for i in young["task"]["ids"] if i in young_tasks]
    old["task"]["ids"] = sorted(set(old["task"]["ids"]) | set(old_tasks))
    old_tt = old.setdefault("timeTracking", {"project": {}, "tag": {}})
    for category in ("project", "tag"):
        target = old_tt.setdefault(category, {})
        for context_id, days in (young.get("timeTracking") or {}).get(category, {}).items():
            target.setdefault(context_id, {}).update(days)
    young["timeTracking"] = {"project": {}, "tag": {}}
    young["lastTimeTrackingFlush"] = now
    old["lastTimeTrackingFlush"] = now
