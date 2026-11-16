"""Journey states for screenshots and tests (PENSUM_DEMO_JOURNEY, never
real tasks): made-up runs of QuestArc's journeys whose records and task
completions put the engine into the state a page shows - a station that
is met, the card after a long break, a habit that can graduate, one that
graduated, a journey of a newer QuestArc. The records are written as
QuestArc stores them (docs/data-model.md §2); every day is counted back
from `today`. No GTK."""
import os
from datetime import date

from pensum.game import content, records
from pensum.store import dates, defaults
from pensum.store.repeat import rules
from pensum.store.repeat.instances import noon_ms

STATES = ("met", "come-back", "graduate", "graduated", "read-only")
JOURNEY = "gentle-morning"


def state():
    name = os.environ.get("PENSUM_DEMO_JOURNEY", "")
    return name if name in STATES else None


def _day(today, back):
    return dates.shift_day(today, -back)


def daily_rule(ds, cfg_id, title, start, today):
    cfg = defaults.get("taskRepeatCfg")
    cfg.update(rules.schedule_fields("DAILY", start))
    cfg.update(id=cfg_id, title=title, projectId=ds.default_project_id(),
               lastTaskCreationDay=today, lastTaskCreation=noon_ms(today))
    ds.data["taskRepeatCfg"]["ids"].append(cfg_id)
    ds.data["taskRepeatCfg"]["entities"][cfg_id] = cfg
    return cfg


def done_on(ds, cfg, day):
    """An instance of `cfg` done on `day`, archived as Super Productivity does."""
    task = defaults.get("task")
    task.update(id=f"rpt_{cfg['id']}_{day}", title=cfg["title"], created=noon_ms(day),
                repeatCfgId=cfg["id"], projectId=cfg["projectId"], isDone=True,
                doneOn=noon_ms(day) - 3 * 3_600_000)
    archive = ds.data["archiveYoung"]["task"]
    archive["ids"].append(task["id"])
    archive["entities"][task["id"]] = task


def iso_week(day):
    year, week, _ = date.fromisoformat(day).isocalendar()
    return f"{year}-W{week:02d}"


def walk(ds, today, run_id, plan, journey_id=JOURNEY, anchor_id=None, why=None):
    """A run of `journey_id` along `plan`, one entry per stage reached:
    (accepted, done_days, finished), days counted back from today;
    `done_days` get a completion of the stage's own daily task. Returns
    the records written."""
    journey = content.journey(journey_id)
    stages = journey["stages"]
    found = {f"run:{run_id}": {"journeyId": journey_id, "journeyVersion": journey["version"],
                               "startDay": _day(today, plan[0][0]),
                               **({"why": why} if why else {})}}
    for stage, (accepted, done_days, finished) in zip(stages, plan):
        key = f"{run_id}:{stage['id']}"
        found[f"stage:{key}"] = {"acceptedDay": _day(today, accepted)}
        cfg = daily_rule(ds, f"{run_id}-{stage['id']}",
                         f"{t_anchor(stage)}: {content.t(stage['plan']['action'])}",
                         _day(today, accepted), today)
        for back in done_days:
            done_on(ds, cfg, _day(today, back))
        found[f"binding:{key}"] = {"taskId": f"rpt_{cfg['id']}_{_day(today, accepted)}",
                                   "repeatCfgId": cfg["id"], "day": _day(today, accepted)}
        if finished is not None:
            found[f"stage-done:{key}"] = {"day": _day(today, finished), "dataFormat": 2}
    if len(plan) == len(stages) and plan[-1][2] is not None:
        found[f"run-end:{run_id}"] = {"day": _day(today, plan[-1][2]), "reason": "finished"}
    if anchor_id:
        found[f"run-anchor:{run_id}"] = {"anchorId": anchor_id}
    records.write(ds, found)
    return found


def t_anchor(stage):
    text = content.t(stage["plan"]["anchor"])
    return text[:1].upper() + text[1:]


def met(ds, today, run_id="walk", anchor_id=None):
    """The first station reached: done on each of the last seven days."""
    return walk(ds, today, run_id, [(8, range(1, 8), None)], anchor_id=anchor_id)


def come_back(ds, today, run_id="walk", anchor_id=None):
    """The first station finished, the second one without a completion for
    more than two weeks: the card after a long break, with Start Smaller."""
    return walk(ds, today, run_id, [(32, range(25, 32), 24), (24, (23, 22), None)],
                anchor_id=anchor_id, why="Calmer mornings")


def finished(ds, today, run_id="walk", anchor_id=None, ended=20):
    """A finished journey whose habit (the last stage's daily task) was
    done every day of the last four weeks; returns the habit's stage id."""
    stages = content.journey(JOURNEY)["stages"]
    plan = [(ended + 40 - 7 * i, (), ended + 33 - 7 * i) for i in range(len(stages) - 1)]
    plan.append((ended + 12, range(1, ended + 12), ended))
    walk(ds, today, run_id, plan, anchor_id=anchor_id)
    return stages[-1]["id"]


def graduate(ds, today, run_id="walk", anchor_id=None):
    """A habit that can graduate: done steadily and three weekly answers of 7."""
    stage_id = finished(ds, today, run_id, anchor_id)
    records.write(ds, {f"checkin:{run_id}:{stage_id}:{iso_week(_day(today, 7 * k))}": {"score": 7}
                       for k in range(3)})
    return stage_id


def graduated(ds, today, run_id="walk", anchor_id=None, back=20, choice="keep"):
    """A habit that graduated `back` days ago; the question after two
    weeks is due."""
    stage_id = finished(ds, today, run_id, anchor_id, ended=back + 10)
    records.write(ds, {f"graduation:{run_id}:{stage_id}:{_day(today, back)}": {"choice": choice}})
    return stage_id


def apply(ds, today, name):
    """The demo's journey in state `name` (the demo's growing run `demo`
    stays at the desk; these runs stand at "getting up")."""
    if name == "read-only":
        records.write(ds, {"stage-done:demo:focus-15": {"day": today, "dataFormat": 99}})
        return
    if name in ("met", "come-back"):
        # The demo's run waits, so this one is the active journey.
        records.write(ds, {f"pause:demo:{today}": {"action": "pause", "source": "user"}})
    {"met": met, "come-back": come_back, "graduate": graduate,
     "graduated": graduated}[name](ds, today, "walk", "getting-up")

