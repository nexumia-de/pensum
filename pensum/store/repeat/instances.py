"""Creating the instances of repeat rules, as Super Productivity does
when the app starts and when the day changes (task-repeat-cfg.service,
_getActionsForTaskRepeatCfg): one instance per rule for its newest due
occurrence, with the deterministic id rpt_<rule>_<day>. Completing an
instance moves a repeat-from-completion series on, or lets a
wait-for-completion series make its next instance. No GTK."""
from datetime import datetime

from pensum.store import dates, defaults
from pensum.store.defaults import TODAY_ID
from pensum.store.repeat import schedule

REMIND_MINUTES = {"AtStart": 0, "m5": 5, "m10": 10, "m15": 15, "m30": 30, "h1": 60,
                  "d1": 1440, "d3": 4320, "w1": 10080}
PRIORITIES = {"high": 3, 3: 3, "medium": 2, 2: 2, "low": 1, 1: 1}


def instance_id(cfg_id, day):
    return f"rpt_{cfg_id}_{day}"


def noon_ms(day):
    """Instances are 'created' at local noon of their occurrence day."""
    return int(datetime.combine(dates.parse_day(day), datetime.min.time())
               .replace(hour=12).timestamp() * 1000)


def rules(ds):
    slice_ = ds.data["taskRepeatCfg"]
    return [slice_["entities"][i] for i in slice_["ids"] if i in slice_["entities"]]


def live_instances(ds, cfg_id):
    return [t for t in ds.tasks.values()
            if t.get("repeatCfgId") == cfg_id and not t.get("parentId")]


def archived_instances(ds, cfg_id):
    found = []
    for name in ("archiveYoung", "archiveOld"):
        entities = ((ds.data.get(name) or {}).get("task") or {}).get("entities") or {}
        found += [t for t in entities.values() if t.get("repeatCfgId") == cfg_id]
    return found


def _advance(cfg, day):
    cfg["lastTaskCreation"] = noon_ms(day)
    cfg["lastTaskCreationDay"] = day


def due_with_time(start_time, day, offset_ms):
    """The rule's clock time on its logical day; a time before the start
    of the next day belongs to that day's late night (getRepeatDueWithTime)."""
    hours, _, minutes = start_time.partition(":")
    moment = datetime.combine(dates.parse_day(day), datetime.min.time())
    if (int(hours) * 60 + int(minutes)) * 60_000 < offset_ms:
        moment = datetime.combine(dates.parse_day(dates.shift_day(day, 1)),
                                  datetime.min.time())
    return int(moment.replace(hour=int(hours), minute=int(minutes)).timestamp() * 1000)


def _valid_time(text):
    if not isinstance(text, str) or ":" not in text:
        return False
    hours, _, minutes = text.partition(":")
    return hours.isdigit() and minutes.isdigit() and int(hours) < 24 and int(minutes) < 60


def create_for(ds, cfg, today, now):
    """Process one rule for `today`; returns the new instance or None."""
    if cfg.get("isPaused") or not cfg.get("id"):
        return None
    day = schedule.newest_due_day(cfg, today)
    if day is None:
        return None
    task_id = instance_id(cfg["id"], day)
    existing = live_instances(ds, cfg["id"])
    if any(t["id"] == task_id or dates.day_str(t.get("created", 0)) == day for t in existing):
        _advance(cfg, day)
        return None
    if day in (cfg.get("deletedInstanceDates") or ()):
        return None
    if cfg.get("waitForCompletion") and any(
            not t.get("isDone") for t in existing + archived_instances(ds, cfg["id"])):
        return None
    if cfg.get("skipOverdue") and day < today:
        _advance(cfg, day)
        return None
    task = _new_instance(ds, cfg, task_id, day, now)
    _advance(cfg, day)
    if _valid_time(cfg.get("startTime")) and cfg.get("remindAt"):
        task.pop("dueDay", None)
        task["dueWithTime"] = due_with_time(cfg["startTime"], day,
                                            dates.day_offset_ms(ds.config))
        if cfg["remindAt"] in REMIND_MINUTES:
            task["remindAt"] = task["dueWithTime"] - REMIND_MINUTES[cfg["remindAt"]] * 60_000
    if cfg.get("shouldInheritSubtasks"):
        _add_subtasks(ds, cfg, task, now)
    return task


def _new_instance(ds, cfg, task_id, day, now):
    task = defaults.get("task")
    task.update(id=task_id, title=cfg.get("title") or "", created=noon_ms(day),
                repeatCfgId=cfg["id"], timeEstimate=cfg.get("defaultEstimate") or 0,
                notes=cfg.get("notes") or "", dueDay=day, modified=now,
                tagIds=[t for t in cfg.get("tagIds") or () if t != TODAY_ID],
                projectId=cfg.get("projectId") or ds.default_project_id())
    if cfg.get("priority") in PRIORITIES:
        task["priority"] = PRIORITIES[cfg["priority"]]
    top = not (cfg.get("order") or 0) > 0
    ds.tasks[task_id] = task
    ds.data["task"]["ids"].append(task_id)
    _place(ds.project_entities[task["projectId"]]["taskIds"], task_id, top)
    for tag_id in task["tagIds"]:
        if tag_id in ds.tag_entities:
            _place(ds.tag_entities[tag_id]["taskIds"], task_id, top)
    if day == ds.today(now) and TODAY_ID in ds.tag_entities:
        _place(ds.tag_entities[TODAY_ID]["taskIds"], task_id, top)
    return task


def _place(order, task_id, top):
    if task_id in order:
        return
    if top:
        order.insert(0, task_id)
    else:
        order.append(task_id)


def _add_subtasks(ds, cfg, parent, now):
    from pensum.store.tasks import recalc_parent
    for index, template in enumerate(cfg.get("subTaskTemplates") or ()):
        sub = defaults.get("task")
        sub.update(id=f"{parent['id']}_sub_{index}", title=template.get("title") or "",
                   notes=template.get("notes") or "",
                   timeEstimate=template.get("timeEstimate") or 0,
                   parentId=parent["id"], projectId=parent["projectId"],
                   created=now, modified=now)
        if sub["id"] in ds.tasks:
            continue
        ds.tasks[sub["id"]] = sub
        ds.data["task"]["ids"].append(sub["id"])
        parent["subTaskIds"].append(sub["id"])
    recalc_parent(ds, parent["id"])


def create_due(ds, now=None):
    """Make every due instance for the logical today; returns the new
    tasks. Runs at start and when the day changes."""
    now = now or dates.now_ms()
    today = ds.today(now)
    created = []
    for cfg in rules(ds):
        if cfg.get("isPaused") or (schedule.last_creation_day(cfg) or "") >= today \
                or today in (cfg.get("deletedInstanceDates") or ()):
            continue
        task = create_for(ds, cfg, today, now)
        if task:
            created.append(task)
    return created


def on_done(ds, task, now=None):
    """After an instance is ticked off (updateStartDateOnComplete$)."""
    cfg = ds.data["taskRepeatCfg"]["entities"].get(task.get("repeatCfgId"))
    if not cfg:
        return None
    now = now or dates.now_ms()
    today = ds.today(now)
    if cfg.get("repeatFromCompletionDate") and _is_latest(task, cfg):
        cfg["startDate"] = today
        cfg["lastTaskCreationDay"] = today
        return None
    if cfg.get("waitForCompletion"):
        return create_for(ds, cfg, today, now)
    return None


def _is_latest(task, cfg):
    last = schedule.last_creation_day(cfg)
    if not last:
        return True
    created = dates.day_str(task.get("created", 0))
    if created == last:
        return True
    due = task.get("dueDay") or (dates.day_str(task["dueWithTime"])
                                 if task.get("dueWithTime") else None)
    return bool(due) and due == last and created < last
