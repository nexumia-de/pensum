"""Planning a task: for a day, at a time of day, or not at all, the way
Super Productivity's scheduling reducers keep it (dueDay or dueWithTime,
the reminder, Today's order, the planner's days, Today's sections).
No GTK."""
from pensum.store import dates, sections
from pensum.store.tasks import _drop, _insert, _today_order, _touch


def _leave_today(ds, task_id):
    """Out of Today's order, and with that out of Today's sections."""
    _drop(_today_order(ds), task_id)
    sections.strip(ds, [task_id], today=True)


def schedule_day(ds, task_id, day, now=None):
    """Plan a task for a day (None: unplanned). Today's order list holds
    it while it is due today; the planner holds later days."""
    now = now or dates.now_ms()
    task = ds.tasks[task_id]
    task.pop("dueWithTime", None)
    # A reminder belongs to a time: planning for a day alone drops it
    # (Super Productivity's planTaskForDay and unScheduleTask).
    task.pop("remindAt", None)
    for ids in ds.data["planner"]["days"].values():
        _drop(ids, task_id)
    if day is None:
        # Removed, not null, as Super Productivity's unscheduleTask leaves it.
        task.pop("dueDay", None)
        _leave_today(ds, task_id)
    else:
        task["dueDay"] = day
        if day == ds.today(now):
            if not task.get("parentId"):
                _insert(_today_order(ds), task_id, top=False)
        else:
            _leave_today(ds, task_id)
            if day > ds.today(now) and not task.get("parentId"):
                ds.data["planner"]["days"].setdefault(day, []).append(task_id)
    _touch(task, now)


def schedule_time(ds, task_id, day, hours, minutes, now=None):
    """Plan a task at a time of day, as Super Productivity's
    scheduleTaskWithTime does: dueWithTime replaces dueDay
    (ARCHITECTURE-DECISIONS #1), the planner's days let go of the task, and
    Today's order gets it on top when the time is today and it is not in
    there yet, or loses it when the time is on another day."""
    from datetime import datetime
    now = now or dates.now_ms()
    task = ds.tasks[task_id]
    # A reminder keeps its lead when the time moves.
    lead = task["dueWithTime"] - task["remindAt"] if isinstance(
        task.get("remindAt"), (int, float)) and task.get("dueWithTime") else None
    moment = datetime.combine(dates.parse_day(day), datetime.min.time()).replace(
        hour=hours, minute=minutes)
    task["dueWithTime"] = int(moment.timestamp() * 1000)
    task.pop("dueDay", None)
    if lead is not None and lead >= 0:
        task["remindAt"] = task["dueWithTime"] - lead
    else:
        task.pop("remindAt", None)
    for ids in ds.data["planner"]["days"].values():
        _drop(ids, task_id)
    order = _today_order(ds)
    if ds.today(task["dueWithTime"]) == ds.today(now):
        if task_id not in order:
            order.insert(0, task_id)
    else:
        _leave_today(ds, task_id)
    _touch(task, now)


def clear_time(ds, task_id, now=None):
    """Keep the planned day, drop the time (and with it the reminder): the
    task is planned for that day, as when a day without a time is chosen."""
    task = ds.tasks[task_id]
    if not task.get("dueWithTime"):
        return
    schedule_day(ds, task_id, ds.today(task["dueWithTime"]), now)
