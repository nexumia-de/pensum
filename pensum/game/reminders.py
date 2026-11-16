"""What Day Planner records about the reminders of followed tasks
(QuestArc game rules §9, its adapter reminder-seen.ts): a reminder
carries no dates, so the host records what it sees - "on" with today
when a followed stage's (or a maintained habit's) task has a reminder
and no record says so, "off" since today when the record says "on" and
the reminder is gone. Graduation waits for 14 days without one. The
records come from the engine's `reminderSeen`; this only decides when.
No GTK."""


def followed(view):
    """(runId, stageId, reminder) of the active stage and of every
    maintained habit the engine reports a reminder view for."""
    found = []
    run = (view or {}).get("active")
    if run and run.get("reminder"):
        station = run["stations"][run["position"]["stage"]]
        found.append((run["runId"], station["stageId"], run["reminder"]))
    for done in (view or {}).get("finished") or ():
        habit = done.get("habit") or {}
        if habit.get("reminder"):
            found.append((done["runId"], habit["stageId"], habit["reminder"]))
    return found


def due(view, records):
    """[(runId, stageId, on)] whose `reminder-seen` record is to be written."""
    out = []
    for run_id, stage_id, reminder in followed(view):
        record = records.get(f"reminder-seen:{run_id}:{stage_id}")
        on = isinstance(record, dict) and record.get("on") is True
        is_set = bool(reminder.get("set"))
        if is_set != on and (is_set or record is not None):
            out.append((run_id, stage_id, is_set))
    return out
