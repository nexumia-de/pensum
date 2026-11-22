"""The planner: the next days and their open tasks, as Super Productivity's
planner shows them (read at commit 9980fd76, `planner.reducer.ts`,
`planner-shared.reducer.ts`): a later day's tasks are those planned for
it (`dueWithTime`'s day wins over `dueDay`), ordered by
`planner.days[day]` and then by `task.ids`; today's are Today's list.
Tasks with a time come first, by time. The estimate of a day is what
is left of its tasks' estimates. Moving a task to another day plans it
there (`planning.schedule_day`). No GTK."""
from pensum.store import dates, planning
from pensum.store.dataset import Context

DAYS = 7


def _later_day(ds, day):
    member = [t for t in ds.tasks.values()
              if not t.get("isDone") and not t.get("parentId") and ds.planned_day(t) == day]
    ids = {t["id"] for t in member}
    order = [i for i in ds.data["planner"]["days"].get(day, ()) if i in ids]
    order += [i for i in ds.data["task"]["ids"] if i in ids and i not in order]
    found = [ds.tasks[i] for i in order]
    return (sorted((t for t in found if ds.has_time(t)), key=lambda t: t["dueWithTime"])
            + [t for t in found if not ds.has_time(t)])


def left_estimate(task):
    return max(0, (task.get("timeEstimate") or 0) - (task.get("timeSpent") or 0))


def days(ds, today=None, count=DAYS):
    """[(day, open top-level tasks, ms of estimate left)] from today on."""
    today = today or ds.today()
    found = []
    for offset in range(count):
        day = dates.shift_day(today, offset)
        tasks = ds.list_tasks(Context.today(), today)[0] if offset == 0 else _later_day(ds, day)
        found.append((day, tasks, sum(left_estimate(t) for t in tasks)))
    return found


def move(ds, task_id, day, now=None):
    """Plan a task for another day (its time of day is dropped, as
    Super Productivity's planTaskForDay does)."""
    if task_id not in ds.tasks or ds.planned_day(ds.tasks[task_id]) == day:
        return False
    planning.schedule_day(ds, task_id, day, now)
    return True
