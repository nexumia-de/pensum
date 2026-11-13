"""Sentences built from QuestArc's texts and a journey's stage, as the
plugin shows them (QuestArc docs/behaviour.md): the plan "After X, I
will Y", the condition in words, the schedule, and one message for the
events of an evaluation. No GTK."""
from datetime import date

from pensum.game.content import t
from pensum.store import dates

DAY_IDS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def capitalise(text):
    return text[:1].upper() + text[1:]


def short_date(day):
    """'9 Nov'"""
    value = dates.parse_day(day)
    return f"{value.day} {value.strftime('%b')}"


def find_stage(journey, stage_id):
    return next((s for s in (journey or {}).get("stages", ()) if s["id"] == stage_id), None)


def plan_sentence(stage):
    plan = stage["plan"]
    parts = {"anchor": t(plan["anchor"]), "action": t(plan["action"])}
    if plan.get("place"):
        return t("ui.plan.sentence-place", place=t(plan["place"]), **parts)
    return t("ui.plan.sentence", **parts)


def _target(condition):
    return condition["minutes"] if condition["type"] == "time_spent" else condition["n"]


def progress_text(stage, station):
    """'4 of 5 days'"""
    condition = stage["condition"]
    target = _target(condition)
    done = min(target, round(station["progress"] * target))
    key = {"days": "ui.progress.days", "count": "ui.progress.count",
           "time_spent": "ui.progress.time"}[condition["type"]]
    return t(key, done=done, n=target)


def condition_text(stage, station):
    """'3 of 5 days in the last 7 due days'"""
    condition = stage["condition"]
    target = _target(condition)
    done = min(target, round(station["progress"] * target))
    if condition["type"] == "days":
        return t("ui.condition.days", done=done, n=target, of=condition["of"])
    key = "ui.condition.count" if condition["type"] == "count" else "ui.condition.time"
    return t(key, done=done, n=target)


def condition_details(stage):
    condition = stage["condition"]
    if condition["type"] == "days":
        return t("ui.details.condition.days", n=condition["n"], of=condition["of"])
    if condition["type"] == "count":
        return t("ui.details.condition.count", n=condition["n"])
    return t("ui.details.condition.time", n=condition["minutes"])


def schedule_text(schedule):
    if schedule["type"] == "daily":
        return t("ui.schedule.daily")
    if schedule["type"] == "everyNDays":
        return t("ui.schedule.every-n", n=schedule["n"])
    names = [DAY_NAMES[DAY_IDS.index(d)] for d in DAY_IDS if d in schedule["days"]]
    if names == list(DAY_NAMES[:5]):
        return "Monday to Friday"
    return t("ui.schedule.weekdays", days=", ".join(names))


def message_for(events, view, journeys):
    """One short message for the events of an evaluation: the real
    progress in words, never what was added to the build; events without
    a text (the build events) add nothing."""
    run = view.get("active")
    station = run["stations"][run["position"]["stage"]] if run else None
    journey = next((j for j in journeys if run and j["id"] == run["journeyId"]), None)
    stage = find_stage(journey, station["stageId"]) if station else None
    shared = {
        "action": capitalise(t(stage["plan"]["action"])) if stage else "",
        "progress": progress_text(stage, station) if stage else "",
    }
    parts = []
    for event in events:
        key = event["key"]
        if t(key) == key:
            continue
        parts.append(t(key, **{**shared, **(event.get("params") or {})}))
    return " ".join(parts) or None


def next_monday(day):
    value = dates.parse_day(day)
    return dates.shift_day(day, (7 - value.weekday()) % 7 or 7)


def first_of_next_month(day):
    value = dates.parse_day(day)
    year, month = (value.year + 1, 1) if value.month == 12 else (value.year, value.month + 1)
    return date(year, month, 1).strftime("%Y-%m-%d")
