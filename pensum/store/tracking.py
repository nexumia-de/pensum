"""Time tracking: the current task, time spent per day, and the work
start and end of a project per day. No GTK."""
from pensum.store import dates, tasks


def set_current(ds, task_id):
    """Start tracking a task (None stops). A parent can't be tracked
    itself; its time is the sum of its subtasks'."""
    state = ds.data["task"]
    if task_id is not None:
        task = ds.tasks[task_id]
        if task.get("subTaskIds") or task.get("isDone"):
            return False
    if state.get("currentTaskId"):
        state["lastCurrentTaskId"] = state["currentTaskId"]
    state["currentTaskId"] = task_id
    return True


def add_time(ds, task_id, ms, now=None):
    """Book `ms` of work, ending at `now`, on the task's logical day."""
    now = now or dates.now_ms()
    task = ds.tasks.get(task_id)
    if not task or ms <= 0:
        return
    ms = int(ms)
    day = ds.today(now)
    per_day = dict(task.get("timeSpentOnDay") or {})
    per_day[day] = per_day.get(day, 0) + ms
    task["timeSpentOnDay"] = per_day
    task["timeSpent"] = sum(per_day.values())
    if task.get("parentId"):
        tasks.recalc_parent(ds, task["parentId"])
    _work_span(ds, "project", task.get("projectId"), day, now - ms, now)
    for tag_id in task.get("tagIds", ()):
        _work_span(ds, "tag", tag_id, day, now - ms, now)
    if (ds.config.get("tasks") or {}).get("isAutoAddWorkedOnToToday", True):
        top = ds.tasks.get(task.get("parentId")) or task
        if not ds.is_due_today(top, day):
            tasks.schedule_day(ds, top["id"], day, now)


def _work_span(ds, kind, context_id, day, start, end):
    if not context_id:
        return
    days = ds.data["timeTracking"].setdefault(kind, {}).setdefault(context_id, {})
    entry = days.setdefault(day, {})
    entry["s"] = min(entry.get("s", start), start)
    entry["e"] = max(entry.get("e", end), end)


def time_on_day(ds, task, day):
    return (task.get("timeSpentOnDay") or {}).get(day, 0)


def day_total(ds, day):
    """Time worked on a day over all top-level tasks, archive included."""
    total = 0
    for source in (ds.data["task"]["entities"],
                   ds.data["archiveYoung"]["task"]["entities"],
                   ds.data["archiveOld"]["task"]["entities"]):
        for task in source.values():
            if not task.get("parentId"):
                total += (task.get("timeSpentOnDay") or {}).get(day, 0)
    return total
