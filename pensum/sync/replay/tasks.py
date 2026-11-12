"""Task ops, as Super Productivity 20.0.0 applies them on another device:
TaskSharedActions addTask, updateTask, deleteTask
(task-shared-crud.reducer.ts, section-shared.reducer.ts,
task-shared-deadline.reducer.ts) and addSubTask (task.reducer.ts), with
the helpers of task.reducer.util.ts and task-shared-helpers.ts.
Rules transcribed, not code copied. Cases not transcribed yet raise
Refused, so the replay stops instead of guessing."""
from pensum.store import dates

TODAY_ID = "TODAY"
IN_PROGRESS_ID = "KANBAN_IN_PROGRESS"
# DEFAULT_TASK of task.model.ts (`created` is the action's).
DEFAULT_TASK = {"id": "", "subTaskIds": [], "timeSpentOnDay": {}, "timeSpent": 0,
                "timeEstimate": 0, "isDone": False, "title": "", "tagIds": [],
                "attachments": []}


class Refused(Exception):
    """A case the transcribed rules do not cover."""


# --- helpers ----------------------------------------------------------------

def _today(data, now_ms):
    return dates.logical_day(data.get("globalConfig"), now_ms)


def _tasks(data):
    return data["task"]["entities"]


def total_time(time_spent_on_day):
    return sum(v for v in (time_spent_on_day or {}).values() if v)


def _add_to_list(ids, task_id, anchor_id, to_bottom):
    """addTaskToListAtAnchor: unchanged if present; above the anchor if
    the list holds it; else at the bottom or the top."""
    if task_id in ids:
        return ids
    if anchor_id and anchor_id in ids:
        i = ids.index(anchor_id)
        return ids[:i] + [task_id] + ids[i:]
    return ids + [task_id] if to_bottom else [task_id] + ids


def _previous_repeat_instance(data, task):
    """getPreviousRepeatInstanceId: the newest other main task of the
    same repeat config still in the state."""
    if not task.get("repeatCfgId") or task.get("parentId"):
        return None
    best = None
    for other in _tasks(data).values():
        if other["id"] == task["id"] or other.get("parentId") \
                or other.get("repeatCfgId") != task["repeatCfgId"]:
            continue
        if best is None or other.get("created", 0) > best.get("created", 0):
            best = other
    return best["id"] if best else None


def _children(data, parent_ids, extra=()):
    """collectTaskAndSubTaskIds: the parents, their subTaskIds, tasks
    whose parentId is one of them, and `extra`."""
    found = list(dict.fromkeys(list(parent_ids) + list(extra)))
    tasks = _tasks(data)
    for pid in parent_ids:
        for sid in (tasks.get(pid) or {}).get("subTaskIds", []):
            if sid not in found:
                found.append(sid)
    for tid in data["task"]["ids"]:
        if tasks[tid].get("parentId") in parent_ids and tid not in found:
            found.append(tid)
    return found


def _remove_from_tags(data, ids):
    gone = set(ids)
    for tag in data["tag"]["entities"].values():
        if any(i in gone for i in tag.get("taskIds", [])):
            tag["taskIds"] = [i for i in tag["taskIds"] if i not in gone]


def _remove_from_sections(data, ids):
    gone = set(ids)
    for section in (data.get("section") or {}).get("entities", {}).values():
        if any(i in gone for i in section.get("taskIds", [])):
            section["taskIds"] = [i for i in section["taskIds"] if i not in gone]


def _remove_from_planner(data, task_id):
    days = (data.get("planner") or {}).get("days") or {}
    for day, ids in days.items():
        if task_id in ids:
            days[day] = [i for i in ids if i != task_id]


def _add_to_planner_day(data, task_id, day):
    """addTaskToPlannerDay at the end (index Infinity): out of every other
    day first."""
    _remove_from_planner(data, task_id)
    days = data.setdefault("planner", {}).setdefault("days", {})
    ids = days.get(day, [])
    if task_id not in ids:
        days[day] = ids + [task_id]


def _recalc_estimate(tasks, parent_id, override=None):
    """reCalcTimeEstimateForParentIfParent: open time left of the subtasks
    (done ones count 0, overrun clamps at 0)."""
    parent = tasks.get(parent_id)
    if not parent:
        return
    total = 0
    for sid in parent.get("subTaskIds", []):
        sub = tasks.get(sid)
        if not sub:
            continue
        if override and override[0] == sid:
            sub = {**sub, **override[1]}
        if not sub.get("isDone"):
            total += max(0, sub.get("timeEstimate", 0) - sub.get("timeSpent", 0))
    parent["timeEstimate"] = total


def _recalc_time_spent(tasks, parent_id):
    """reCalcTimeSpentForParentIfParent: per-day sums of the subtasks."""
    parent = tasks.get(parent_id)
    if not parent:
        return
    per_day = {}
    for sid in parent.get("subTaskIds", []):
        for day, ms in ((tasks.get(sid) or {}).get("timeSpentOnDay") or {}).items():
            if ms:
                per_day[day] = per_day.get(day, 0) + ms
    parent["timeSpentOnDay"] = per_day
    parent["timeSpent"] = total_time(per_day)


# --- addTask ------------------------------------------------------------------

def add_task(data, fields, now_ms):
    task = dict(fields.get("task") or {})
    if not task.get("id"):
        raise Refused("task without id")
    if task.get("deadlineDay") or "deadlineWithTime" in task:
        raise Refused("task with a deadline (auto planning)")
    if task.get("parentId"):
        raise Refused("subtask through addTask")
    to_bottom = bool(fields.get("isAddToBottom"))
    to_backlog = bool(fields.get("isAddToBacklog"))
    today = _today(data, now_ms)
    tag_ids = [t for t in task.get("tagIds") or [] if t != TODAY_ID]
    anchor = _previous_repeat_instance(data, task)
    new = {**DEFAULT_TASK, "created": now_ms, **task, "tagIds": tag_ids,
           "timeSpent": total_time(task.get("timeSpentOnDay")),
           "projectId": task.get("projectId") or ""}
    tasks = data["task"]
    if new["id"] not in tasks["entities"]:
        tasks["ids"].append(new["id"])
        tasks["entities"][new["id"]] = new
    project = data["project"]["entities"].get(task.get("projectId") or "")
    if project:
        key = ("backlogTaskIds" if to_backlog and project.get("isEnableBacklog")
               else "taskIds")
        project[key] = _add_to_list(project.get(key, []), new["id"], anchor, to_bottom)
    tags = data["tag"]["entities"]
    for tag_id in tag_ids + ([TODAY_ID] if task.get("dueDay") == today else []):
        if tag_id in tags:
            tags[tag_id]["taskIds"] = _add_to_list(tags[tag_id].get("taskIds", []),
                                                   new["id"], anchor, to_bottom)
    due = task.get("dueDay")
    if due and due != today:
        days = data.setdefault("planner", {}).setdefault("days", {})
        ids = [i for i in days.get(due, []) if i != new["id"]]
        days[due] = ids + [new["id"]] if to_bottom else [new["id"]] + ids


# --- addSubTask --------------------------------------------------------------

def add_subtask(data, fields, now_ms):
    task = dict(fields.get("task") or {})
    parent_id = fields.get("parentId")
    tasks = _tasks(data)
    parent = tasks.get(parent_id)
    if not parent or not task.get("id"):
        return  # the reducer leaves the state as it is
    first = not parent.get("subTaskIds")
    sub = {**task, "parentId": parent_id, "tagIds": [],
           "projectId": parent.get("projectId")}
    if first and not (task.get("timeSpentOnDay") or {}):
        sub["timeSpentOnDay"] = parent.get("timeSpentOnDay") or {}
        sub["timeSpent"] = total_time(parent.get("timeSpentOnDay"))
    if first and not task.get("timeEstimate"):
        sub["timeEstimate"] = parent.get("timeEstimate", 0)
    if sub["id"] not in tasks:
        data["task"]["ids"].append(sub["id"])
    tasks[sub["id"]] = sub
    if sub["id"] not in parent.get("subTaskIds", []):
        parent["subTaskIds"] = parent.get("subTaskIds", []) + [sub["id"]]
    if data["task"].get("currentTaskId") == parent_id:
        data["task"]["currentTaskId"] = sub["id"]
    _recalc_estimate(tasks, parent_id)
    _recalc_time_spent(tasks, parent_id)


# --- updateTask ------------------------------------------------------------

def update_task(data, fields, now_ms):
    update = fields.get("task") or {}
    task_id = update.get("id")
    changes = dict(update.get("changes") or {})
    tasks = _tasks(data)
    current = tasks.get(task_id)
    if not current:
        return
    if "projectId" in changes:
        raise Refused("moving a task to another project")
    today = _today(data, now_ms)
    # sanitizeDoneScheduleChanges: drop a dueDay that only marks the
    # completion day of a scheduled task or a subtask.
    if changes.get("isDone") is True and isinstance(changes.get("dueDay"), str):
        scheduled = isinstance(current.get("dueDay"), str) \
            or isinstance(current.get("dueWithTime"), (int, float))
        if scheduled or current.get("parentId"):
            done_day = dates.day_str(changes["doneOn"]) \
                if isinstance(changes.get("doneOn"), (int, float)) else today
            if changes["dueDay"] == done_day and (
                    changes["dueDay"] != current.get("dueDay") or current.get("parentId")):
                del changes["dueDay"]
    # removeInProgressTagOnCompletion
    if changes.get("isDone") is True:
        tag_ids = changes["tagIds"] if isinstance(changes.get("tagIds"), list) \
            else current.get("tagIds", [])
        if IN_PROGRESS_ID in tag_ids:
            changes["tagIds"] = [t for t in tag_ids if t != IN_PROGRESS_ID]
    # JavaScript truthiness: an empty list or object counts as given.
    if isinstance(changes.get("tagIds"), list):
        _update_tags(data, task_id, current.get("tagIds", []), changes["tagIds"])
    old = dict(current)
    if isinstance(changes.get("timeSpentOnDay"), dict):
        _set_time_spent(tasks, task_id, changes["timeSpentOnDay"])
    if isinstance(changes.get("timeEstimate"), (int, float)) or "isDone" in changes:
        if isinstance(changes.get("timeEstimate"), (int, float)):
            current["timeEstimate"] = changes["timeEstimate"]
        if current.get("parentId"):
            _recalc_estimate(tasks, current["parentId"], (task_id, changes))
    # updateDoneOnForTask
    if changes.get("isDone") is True:
        current["doneOn"] = changes["doneOn"] if isinstance(changes.get("doneOn"),
                                                            (int, float)) else now_ms
    elif changes.get("isDone") is False:
        current.pop("doneOn", None)
    for key, value in changes.items():
        if key == "doneOn" and changes.get("isDone") is False:
            continue
        if value is None:
            current.pop(key, None)  # an undefined value in the action
        else:
            current[key] = value
    current["modified"] = now_ms
    to_done = changes.get("isDone") is True
    if to_done and not old.get("parentId") and old.get("dueDay") == today:
        today_tag = data["tag"]["entities"].get(TODAY_ID)
        if today_tag and task_id not in today_tag["taskIds"]:
            today_tag["taskIds"] = today_tag["taskIds"] + [task_id]
    if "dueDay" in changes:
        new_due = changes["dueDay"]
    elif to_done and current.get("dueDay") != old.get("dueDay"):
        new_due = current.get("dueDay")
    else:
        new_due = None
    if new_due is not None and new_due != old.get("dueDay"):
        _move_due_day(data, current, old.get("dueDay"), new_due, today, to_done)


def _update_tags(data, task_id, old_ids, new_ids):
    """handleTagUpdates: out of tags it left, on top of tags it joined."""
    tags = data["tag"]["entities"]
    for tag_id in old_ids:
        if tag_id not in new_ids and tag_id != TODAY_ID and tag_id in tags:
            tags[tag_id]["taskIds"] = [i for i in tags[tag_id]["taskIds"] if i != task_id]
    for tag_id in new_ids:
        if tag_id not in old_ids and tag_id != TODAY_ID and tag_id in tags:
            rest = [i for i in tags[tag_id]["taskIds"] if i != task_id]
            tags[tag_id]["taskIds"] = [task_id] + rest


def _set_time_spent(tasks, task_id, per_day):
    """updateTimeSpentForTask, with the parent changed by the difference."""
    task = tasks[task_id]
    before = task.get("timeSpentOnDay") or {}
    task["timeSpentOnDay"] = per_day
    task["timeSpent"] = total_time(per_day)
    parent = tasks.get(task.get("parentId") or "")
    if not parent:
        return
    parent_days = dict(parent.get("timeSpentOnDay") or {})
    delta_total = 0
    for day in set(before) | set(per_day):
        delta = (per_day.get(day) or 0) - (before.get(day) or 0)
        if delta:
            delta_total += delta
            value = parent_days.get(day, 0) + delta
            if value > 0:
                parent_days[day] = value
            else:
                parent_days.pop(day, None)
    parent["timeSpentOnDay"] = parent_days
    parent["timeSpent"] = parent.get("timeSpent", 0) + delta_total


def _move_due_day(data, task, old_due, new_due, today, to_done):
    task_id = task["id"]
    _remove_from_planner(data, task_id)
    if new_due and new_due != today and not to_done:
        _add_to_planner_day(data, task_id, new_due)
    today_tag = data["tag"]["entities"].get(TODAY_ID)
    if not today_tag:
        return
    if old_due == today and new_due != today:
        today_tag["taskIds"] = [i for i in today_tag["taskIds"] if i != task_id]
        if TODAY_ID in task.get("tagIds", []):
            task["tagIds"] = [t for t in task["tagIds"] if t != TODAY_ID]
    elif old_due != today and new_due == today and task_id not in today_tag["taskIds"]:
        today_tag["taskIds"] = today_tag["taskIds"] + [task_id]


# --- deleteTask --------------------------------------------------------------

def delete_task(data, fields, now_ms):
    task = fields.get("task") or {}
    task_id = task.get("id")
    if not task_id:
        return
    for one in [task] + list(task.get("subTasks") or []):
        if one.get("issueType") == "ICAL":
            raise Refused("deleting a calendar task")
    state = data["task"]
    tasks = state["entities"]
    # Subtasks (and section cleanup) from the state before the delete.
    section_ids = _children(data, [task_id])
    stored = tasks.get(task_id)
    payload_subs = list(task.get("subTaskIds") or [])
    state_subs = [i for i in state["ids"] if tasks[i].get("parentId") == task_id]
    all_subs = list(dict.fromkeys(payload_subs + state_subs))
    if stored is not None:
        del tasks[task_id]
    parent_id = task.get("parentId")
    if parent_id and parent_id in tasks:
        _remove_from_parent(tasks, parent_id, task)
    for sid in all_subs:
        tasks.pop(sid, None)
    state["ids"] = [i for i in state["ids"] if i in tasks]
    if state.get("currentTaskId") in [task_id] + all_subs:
        state["currentTaskId"] = None
    project = data["project"]["entities"].get(task.get("projectId") or "")
    if project:
        project["taskIds"] = [i for i in project.get("taskIds", []) if i != task_id]
        project["backlogTaskIds"] = [i for i in project.get("backlogTaskIds", [])
                                     if i != task_id]
    _remove_from_tags(data, [task_id] + list(task.get("subTaskIds") or []))
    _remove_from_sections(data, section_ids)


def _remove_from_parent(tasks, parent_id, child):
    """removeTaskFromParentSideEffects with the times of the last subtask
    copied to the parent."""
    parent = tasks[parent_id]
    last = len(parent.get("subTaskIds", [])) == 1
    parent["subTaskIds"] = [i for i in parent.get("subTaskIds", []) if i != child["id"]]
    if last:
        parent["timeSpentOnDay"] = child.get("timeSpentOnDay") or {}
        parent["timeEstimate"] = child.get("timeEstimate", 0)
    else:
        _recalc_time_spent(tasks, parent_id)
        _recalc_estimate(tasks, parent_id)
