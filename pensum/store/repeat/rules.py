"""Making a task recurring, pausing a rule and removing it, with the
effects Super Productivity runs (addTaskRepeatCfgToTask,
updateTaskAfterMakingItRepeatable$, deleteTaskRepeatCfg). No GTK."""
from pensum.store import dates, defaults
from pensum.store.defaults import TODAY_ID
from pensum.store.ids import new_id
from pensum.store.repeat import schedule
from pensum.store.repeat.instances import noon_ms

WORKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")

# The schedules Pensum offers; each is a quickSetting with its fields.
PRESETS = ("DAILY", "MONDAY_TO_FRIDAY", "WEEKLY_CURRENT_WEEKDAY",
           "MONTHLY_CURRENT_DATE", "YEARLY_CURRENT_DATE", "CUSTOM")


def schedule_fields(preset, start, every=1, cycle="DAILY", weekdays=()):
    """The rule fields for a preset, the way the repeat dialog fills them.
    `start` is the first day; CUSTOM takes `every`, `cycle` and, for
    WEEKLY, `weekdays`."""
    flags = dict.fromkeys(schedule.WEEKDAYS, False)
    fields = {"quickSetting": preset, "startDate": start, "repeatEvery": 1}
    if preset == "DAILY":
        fields["repeatCycle"] = "DAILY"
    elif preset == "MONDAY_TO_FRIDAY":
        fields["repeatCycle"] = "WEEKLY"
        flags.update(dict.fromkeys(WORKDAYS, True))
    elif preset == "WEEKLY_CURRENT_WEEKDAY":
        fields["repeatCycle"] = "WEEKLY"
        flags[schedule.WEEKDAYS[dates.parse_day(start).weekday()]] = True
    elif preset == "MONTHLY_CURRENT_DATE":
        fields["repeatCycle"] = "MONTHLY"
    elif preset == "YEARLY_CURRENT_DATE":
        fields["repeatCycle"] = "YEARLY"
    else:
        fields.update(quickSetting="CUSTOM", repeatCycle=cycle, repeatEvery=max(1, int(every)))
        if cycle == "WEEKLY":
            flags.update({day: day in weekdays for day in schedule.WEEKDAYS})
    fields.update(flags)
    # "Don't let overdue instances pile up": on only for every single day.
    fields["skipOverdue"] = preset == "DAILY" or (
        fields["quickSetting"] == "CUSTOM" and fields["repeatCycle"] == "DAILY"
        and fields["repeatEvery"] == 1)
    return fields


def make_recurring(ds, task_id, fields, now=None):
    """Turn a task into the first instance of a new rule; returns the rule."""
    now = now or dates.now_ms()
    today = ds.today(now)
    task = ds.tasks[task_id]
    cfg = defaults.get("taskRepeatCfg")
    cfg.update(id=new_id(), title=task.get("title") or "",
               projectId=task.get("projectId") or None,
               tagIds=[t for t in task.get("tagIds", ()) if t != TODAY_ID],
               lastTaskCreation=now, lastTaskCreationDay=today)
    if task.get("timeEstimate"):
        cfg["defaultEstimate"] = task["timeEstimate"]
    cfg.update(fields)
    cfg["subTaskTemplates"] = [
        {"title": s.get("title", ""), "notes": s.get("notes", ""),
         "timeEstimate": s.get("timeEstimate", 0)} for s in ds.subtasks(task)]
    ds.data["taskRepeatCfg"]["ids"].append(cfg["id"])
    ds.data["taskRepeatCfg"]["entities"][cfg["id"]] = cfg
    task["repeatCfgId"] = cfg["id"]
    found = schedule.first_day(cfg)
    if found is None and _empty_window(cfg):
        task["modified"] = now
        return cfg
    first = found or today
    cfg["lastTaskCreationDay"] = first
    cfg["lastTaskCreation"] = noon_ms(found) if found else now
    if first != today:
        task["created"] = noon_ms(first)
        if not task.get("dueWithTime"):
            task["dueDay"] = first
        order = (ds.tag_entities.get(TODAY_ID) or {}).get("taskIds", [])
        if task_id in order and task.get("dueDay") != today:
            order.remove(task_id)
    else:
        if dates.day_str(task.get("created", 0)) != first:
            task["created"] = noon_ms(first)
        if not task.get("dueWithTime") and task.get("dueDay") != first:
            task["dueDay"] = first
    task["modified"] = now
    return cfg


def _empty_window(cfg):
    probe = dict(cfg)
    probe.pop("repeatUntilDay", None)
    return schedule.first_day(probe) is not None


def rule_of(ds, task):
    return ds.data["taskRepeatCfg"]["entities"].get(task.get("repeatCfgId"))


def set_paused(ds, cfg_id, paused):
    ds.data["taskRepeatCfg"]["entities"][cfg_id]["isPaused"] = bool(paused)


def update(ds, cfg_id, **changes):
    """Plain fields such as the title; the existing instances stay."""
    cfg = ds.data["taskRepeatCfg"]["entities"][cfg_id]
    for key, value in changes.items():
        if value is None:
            cfg.pop(key, None)
        else:
            cfg[key] = value
    return cfg


def delete(ds, cfg_id, now=None):
    """Remove a rule; its tasks, live and archived, stay as normal tasks
    (repeatCfgId removed, never set to null)."""
    slice_ = ds.data["taskRepeatCfg"]
    slice_["entities"].pop(cfg_id, None)
    if cfg_id in slice_["ids"]:
        slice_["ids"].remove(cfg_id)
    now = now or dates.now_ms()
    for task in ds.tasks.values():
        if task.get("repeatCfgId") == cfg_id:
            del task["repeatCfgId"]
            task["modified"] = now
    for name in ("archiveYoung", "archiveOld"):
        entities = ((ds.data.get(name) or {}).get("task") or {}).get("entities") or {}
        for task in entities.values():
            if task.get("repeatCfgId") == cfg_id:
                del task["repeatCfgId"]


def snapshot(ds, cfg_id):
    """What delete() changes, so Undo can put it back."""
    import copy
    tagged = [t["id"] for t in ds.tasks.values() if t.get("repeatCfgId") == cfg_id]
    archived = {name: [t["id"] for t in
                       (((ds.data.get(name) or {}).get("task") or {}).get("entities") or {}).values()
                       if t.get("repeatCfgId") == cfg_id]
                for name in ("archiveYoung", "archiveOld")}
    slice_ = ds.data["taskRepeatCfg"]
    return {"cfg": copy.deepcopy(slice_["entities"][cfg_id]),
            "index": slice_["ids"].index(cfg_id), "tasks": tagged, "archived": archived}


def restore(ds, saved):
    cfg = saved["cfg"]
    slice_ = ds.data["taskRepeatCfg"]
    if cfg["id"] not in slice_["entities"]:
        slice_["ids"].insert(saved["index"], cfg["id"])
        slice_["entities"][cfg["id"]] = cfg
    for task_id in saved["tasks"]:
        if task_id in ds.tasks:
            ds.tasks[task_id]["repeatCfgId"] = cfg["id"]
    for name, ids in saved["archived"].items():
        entities = ds.data[name]["task"]["entities"]
        for task_id in ids:
            if task_id in entities:
                entities[task_id]["repeatCfgId"] = cfg["id"]
