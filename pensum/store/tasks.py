"""Changes to tasks, keeping every list Super Productivity derives from
them consistent: project and tag order, subtask ids, the Today order and
the parent's estimate and time. No GTK."""
from pensum.store import dates, defaults
from pensum.store.defaults import TODAY_ID
from pensum.store.ids import new_id


def _drop(values, value):
    while value in values:
        values.remove(value)


def _insert(values, value, top):
    _drop(values, value)
    if top:
        values.insert(0, value)
    else:
        values.append(value)


def _touch(task, now):
    task["modified"] = now


def recalc_parent(ds, parent_id):
    """A parent's time spent is the sum of its subtasks' and its estimate
    the time they have left (reCalcTimesForParentIfParent)."""
    parent = ds.tasks.get(parent_id)
    if not parent or not parent.get("subTaskIds"):
        return
    subs = ds.subtasks(parent)
    per_day = {}
    for sub in subs:
        for day, ms in (sub.get("timeSpentOnDay") or {}).items():
            if ms:
                per_day[day] = per_day.get(day, 0) + ms
    parent["timeSpentOnDay"] = per_day
    parent["timeSpent"] = sum(per_day.values())
    parent["timeEstimate"] = sum(
        0 if s.get("isDone") else max(0, s.get("timeEstimate", 0) - s.get("timeSpent", 0))
        for s in subs)


def _today_order(ds):
    return ds.tag_entities[TODAY_ID]["taskIds"] if TODAY_ID in ds.tag_entities else []


def add_task(ds, title, context, now=None, top=True):
    """A new top-level task in a list: in Today it is due today and lives
    in the default project; in a tag list it carries the tag."""
    now = now or dates.now_ms()
    task = defaults.get("task")
    task.update(id=new_id(), title=title.strip(), created=now)
    if context.kind == "project":
        task["projectId"] = context.id
    else:
        task["projectId"] = ds.default_project_id()
    if context.kind == "tag":
        task["tagIds"] = [context.id]
        _insert(ds.tag_entities[context.id]["taskIds"], task["id"], top)
    if context.kind == "today":
        task["dueDay"] = ds.today(now)
        _insert(_today_order(ds), task["id"], top)
    _touch(task, now)
    ds.tasks[task["id"]] = task
    ds.data["task"]["ids"].append(task["id"])
    project = ds.project_entities[task["projectId"]]
    _insert(project["taskIds"], task["id"], top)
    return task


def add_subtask(ds, parent_id, title, now=None):
    now = now or dates.now_ms()
    parent = ds.tasks[parent_id]
    task = defaults.get("task")
    task.update(id=new_id(), title=title.strip(), created=now,
                parentId=parent_id, projectId=parent["projectId"])
    _touch(task, now)
    ds.tasks[task["id"]] = task
    ds.data["task"]["ids"].append(task["id"])
    parent["subTaskIds"].append(task["id"])
    recalc_parent(ds, parent_id)
    return task


def update(ds, task_id, now=None, **changes):
    """Title, notes and other plain fields."""
    task = ds.tasks[task_id]
    for key, value in changes.items():
        if value is None:
            task.pop(key, None)
        else:
            task[key] = value
    _touch(task, now or dates.now_ms())
    return task


def set_estimate(ds, task_id, ms, now=None):
    task = ds.tasks[task_id]
    task["timeEstimate"] = max(0, int(ms))
    _touch(task, now or dates.now_ms())
    if task.get("parentId"):
        recalc_parent(ds, task["parentId"])


def set_done(ds, task_id, done, now=None):
    now = now or dates.now_ms()
    task = ds.tasks[task_id]
    task["isDone"] = bool(done)
    if done:
        task["doneOn"] = now
        if ds.data["task"].get("currentTaskId") == task_id:
            ds.data["task"]["currentTaskId"] = None
    else:
        task.pop("doneOn", None)
    _touch(task, now)
    if task.get("parentId"):
        recalc_parent(ds, task["parentId"])


def schedule_day(ds, task_id, day, now=None):
    """Plan a task for a day (None: unplanned). Today's order list holds
    it while it is due today; the planner holds later days."""
    now = now or dates.now_ms()
    task = ds.tasks[task_id]
    task.pop("dueWithTime", None)
    for ids in ds.data["planner"]["days"].values():
        _drop(ids, task_id)
    if day is None:
        task["dueDay"] = None
        _drop(_today_order(ds), task_id)
    else:
        task["dueDay"] = day
        if day == ds.today(now):
            if not task.get("parentId"):
                _insert(_today_order(ds), task_id, top=False)
        else:
            _drop(_today_order(ds), task_id)
            if day > ds.today(now) and not task.get("parentId"):
                ds.data["planner"]["days"].setdefault(day, []).append(task_id)
    _touch(task, now)


def move_to_project(ds, task_id, project_id, now=None):
    task = ds.tasks[task_id]
    if task.get("parentId") or task.get("projectId") == project_id:
        return
    old = ds.project_entities.get(task.get("projectId"))
    if old:
        _drop(old["taskIds"], task_id)
        _drop(old["backlogTaskIds"], task_id)
    ds.project_entities[project_id]["taskIds"].append(task_id)
    for sub in [task] + ds.subtasks(task):
        sub["projectId"] = project_id
        _touch(sub, now or dates.now_ms())


def set_backlog(ds, task_id, in_backlog, now=None):
    """Move a project's top-level task between its list and its backlog."""
    task = ds.tasks[task_id]
    project = ds.project_entities.get(task.get("projectId"))
    if not project or task.get("parentId"):
        return False
    source, target = (("taskIds", "backlogTaskIds") if in_backlog
                      else ("backlogTaskIds", "taskIds"))
    if task_id not in project.get(source, []):
        return False
    _drop(project[source], task_id)
    project.setdefault(target, []).insert(0, task_id)
    if in_backlog:
        project["isEnableBacklog"] = True
    _touch(task, now or dates.now_ms())
    return True


def set_tags(ds, task_id, tag_ids, now=None):
    task = ds.tasks[task_id]
    tag_ids = [t for t in tag_ids if t in ds.tag_entities and t != TODAY_ID]
    for tag_id in task.get("tagIds", ()):
        if tag_id not in tag_ids and tag_id in ds.tag_entities:
            _drop(ds.tag_entities[tag_id]["taskIds"], task_id)
    if not task.get("parentId"):
        for tag_id in tag_ids:
            if task_id not in ds.tag_entities[tag_id]["taskIds"]:
                ds.tag_entities[tag_id]["taskIds"].append(task_id)
    task["tagIds"] = tag_ids
    _touch(task, now or dates.now_ms())


def _order_list(ds, context, today):
    """The stored order a list's moves change, with every shown task in it."""
    if context.kind == "project":
        return ds.project_entities[context.id]["taskIds"]
    if context.kind == "tag":
        order = ds.tag_entities[context.id]["taskIds"]
    else:
        order = _today_order(ds)
    for i in ds.top_level_ids(context, today):
        if i not in order:
            order.append(i)
    return order


def move(ds, task_id, context, offset, today=None):
    """Move a task by `offset` places among the tasks a list shows (or, for
    a subtask, among its parent's subtasks); a large offset moves it to the
    top or the bottom. Returns True when it moved."""
    task = ds.tasks.get(task_id)
    if not task:
        return False
    parent = ds.tasks.get(task.get("parentId"))
    backlog = (ds.project_entities.get(context.id, {}).get("backlogTaskIds", [])
               if context is not None and context.kind == "project" else [])
    if parent:
        order = parent["subTaskIds"]
        visible = list(order)
    elif task_id in backlog:
        order = backlog
        visible = list(order)
    else:
        order = _order_list(ds, context, today)
        visible = ds.top_level_ids(context, today)
    if task_id not in visible:
        return False
    index = visible.index(task_id)
    target = max(0, min(len(visible) - 1, index + offset))
    if target == index:
        return False
    neighbour = visible[target]
    order.remove(task_id)
    position = order.index(neighbour)
    order.insert(position + (1 if offset > 0 else 0), task_id)
    return True


def delete(ds, task_id):
    """Remove a task with its subtasks from every list that names it."""
    task = ds.tasks.get(task_id)
    if not task:
        return
    for sub_id in list(task.get("subTaskIds", ())):
        delete(ds, sub_id)
    ds.tasks.pop(task_id)
    _drop(ds.data["task"]["ids"], task_id)
    if ds.data["task"].get("currentTaskId") == task_id:
        ds.data["task"]["currentTaskId"] = None
    for project in ds.project_entities.values():
        _drop(project.get("taskIds", []), task_id)
        _drop(project.get("backlogTaskIds", []), task_id)
    for tag in ds.tag_entities.values():
        _drop(tag.get("taskIds", []), task_id)
    for ids in ds.data["planner"]["days"].values():
        _drop(ids, task_id)
    for section in ds.data["section"]["entities"].values():
        _drop(section.get("taskIds", []), task_id)
    ds.data["reminders"] = [r for r in ds.data["reminders"]
                            if r.get("relatedId") != task_id]
    parent = ds.tasks.get(task.get("parentId"))
    if parent:
        _drop(parent["subTaskIds"], task_id)
        recalc_parent(ds, parent["id"])


# Priority: 3 high, 2 medium, 1 low; older data has the words. Writes are
# numbers, null clears (Super Productivity's task-priority-compatibility).
_PRIORITY_WORDS = {"high": 3, "medium": 2, "low": 1}


def priority_level(task):
    value = task.get("priority")
    if isinstance(value, str):
        return _PRIORITY_WORDS.get(value, 0)
    return value if value in (1, 2, 3) else 0


def set_priority(ds, task_id, level, now=None):
    task = ds.tasks[task_id]
    if priority_level(task) == level:
        return  # same meaning: keep the stored form
    task["priority"] = level if level in (1, 2, 3) else None
    _touch(task, now or dates.now_ms())


def deadline_day(ds, task):
    """The deadline's day: deadlineWithTime's day wins over deadlineDay."""
    if task.get("deadlineWithTime"):
        return ds.today(task["deadlineWithTime"])
    return task.get("deadlineDay") or None


def set_deadline(ds, task_id, day, now=None):
    """A deadline on a day (None clears it); a day replaces a time."""
    task = ds.tasks[task_id]
    task["deadlineDay"] = day
    task["deadlineWithTime"] = None
    if day is None:
        task["deadlineRemindAt"] = None
    _touch(task, now or dates.now_ms())
