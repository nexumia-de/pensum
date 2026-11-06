"""A made-up dataset for screenshots and trying Pensum (PENSUM_DEMO=1):
recorded values, never live data. No GTK."""
from datetime import datetime, timedelta

from pensum.game import records
from pensum.store import contexts, dates, defaults, tasks, tracking
from pensum.store.dataset import Context, Dataset
from pensum.store.repeat import instances
from pensum.store.repeat.instances import noon_ms

def demo_now():
    """10:30 today: the made-up day always is the current one, so Today is
    filled whenever the demo starts."""
    moment = datetime.now().replace(hour=10, minute=30, second=0, microsecond=0)
    return int(moment.timestamp() * 1000)


def create(now=None):
    now = now or demo_now()
    ds = Dataset(defaults.fresh_dataset(now - 86_400_000 * 30))
    ms = lambda minutes: minutes * 60_000  # noqa: E731
    # Fixed ids, so the screenshots can open a list (release.toml).
    garden = contexts.add_project(ds, "Garden", entity_id="demo-garden")
    work = contexts.add_project(ds, "Website Relaunch", entity_id="demo-website")
    calls = contexts.add_tag(ds, "calls", now, entity_id="demo-calls")
    errands = contexts.add_tag(ds, "errands", now, entity_id="demo-errands")
    today = Context.today()

    review = tasks.add_task(ds, "Review the new start page", today, now, top=False)
    tasks.move_to_project(ds, review["id"], work["id"], now)
    for title, estimate, spent in (("Check texts on 360 px", 30, 25),
                                   ("Compare loading times", 20, 0),
                                   ("Write feedback for the team", 15, 0)):
        sub = tasks.add_subtask(ds, review["id"], title, now)
        tasks.set_estimate(ds, sub["id"], ms(estimate), now)
        if spent:
            tracking.add_time(ds, sub["id"], ms(spent), now - ms(40))
    first = ds.tasks[review["subTaskIds"][0]]
    tasks.set_done(ds, first["id"], True, now - ms(10))

    call = tasks.add_task(ds, "Call the plumber about the boiler", today, now, top=False)
    tasks.set_tags(ds, call["id"], [calls["id"]], now)
    tasks.set_estimate(ds, call["id"], ms(10), now)
    tasks.set_priority(ds, call["id"], 3, now)

    seeds = tasks.add_task(ds, "Buy tomato seeds", today, now, top=False)
    tasks.move_to_project(ds, seeds["id"], garden["id"], now)
    tasks.set_tags(ds, seeds["id"], [errands["id"]], now)

    mail = tasks.add_task(ds, "Answer emails", today, now, top=False)
    tasks.set_estimate(ds, mail["id"], ms(30), now)
    tracking.add_time(ds, mail["id"], ms(35), now - ms(90))
    tasks.set_done(ds, mail["id"], True, now - ms(55))

    tasks.set_deadline(ds, review["id"], (datetime.fromtimestamp(now / 1000)
                                          + timedelta(days=3)).strftime("%Y-%m-%d"), now)
    tasks.update(ds, review["id"], now,
                 notes="Focus on the phone layout first; the desktop "
                       "version was reviewed last week.")
    tasks.set_estimate(ds, call["id"], ms(10), now)

    for title in ("Prune the apple tree", "Order compost"):
        tasks.add_task(ds, title, Context("project", garden["id"]), now, top=False)
    plan = tasks.add_task(ds, "Plan the launch date", Context("project", work["id"]), now,
                          top=False)
    tasks.schedule_day(ds, plan["id"], (datetime.fromtimestamp(now / 1000)
                                        + timedelta(days=2)).strftime("%Y-%m-%d"), now)
    books = tasks.add_task(ds, "Return the library books", today, now, top=False)
    tasks.set_tags(ds, books["id"], [errands["id"]], now)
    tasks.schedule_day(ds, books["id"], (datetime.fromtimestamp(now / 1000)
                                         - timedelta(days=1)).strftime("%Y-%m-%d"), now)
    tracking.set_current(ds, review["subTaskIds"][1])
    _journey(ds, now)
    return ds


WORKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday")


def _rule(ds, cfg_id, title, start, today):
    cfg = defaults.get("taskRepeatCfg")
    cfg.update(id=cfg_id, title=title, projectId=ds.default_project_id(), startDate=start,
               quickSetting="MONDAY_TO_FRIDAY", repeatCycle="WEEKLY",
               lastTaskCreationDay=today, lastTaskCreation=noon_ms(today))
    ds.data["taskRepeatCfg"]["ids"].append(cfg_id)
    ds.data["taskRepeatCfg"]["entities"][cfg_id] = cfg
    return cfg


def _archived_instance(ds, cfg, day):
    task = defaults.get("task")
    task.update(id=f"rpt_{cfg['id']}_{day}", title=cfg["title"], created=noon_ms(day),
                repeatCfgId=cfg["id"], projectId=cfg["projectId"], isDone=True,
                doneOn=noon_ms(day) - 3 * 3_600_000)
    archive = ds.data["archiveYoung"]["task"]
    archive["ids"].append(task["id"])
    archive["entities"][task["id"]] = task
    return task


def _journey(ds, now):
    """Journey "First Things First" with game: the first station done
    after a week, the second one on its way with one gap. The choice
    records are written as QuestArc stores them (recorded values)."""
    today = ds.today(now)
    workdays = [dates.shift_day(today, -back) for back in range(16, 0, -1)
                if dates.parse_day(dates.shift_day(today, -back)).weekday() < 5]
    first, second = workdays[:5], workdays[5:]
    stage_done = second[0]
    one = _rule(ds, "demo-one-thing", "Sitting down at my desk: write down the one task "
                "that matters most today", first[0], stage_done)
    for day in first:
        _archived_instance(ds, one, day)
    focus = _rule(ds, "demo-focus-15", "Sitting down at my desk: write down my one task "
                  "and give it 15 quiet minutes, notifications off", stage_done, today)
    for day in second:
        if day != second[-2]:  # one gap, never a loss
            _archived_instance(ds, focus, day)
    task = instances.create_for(ds, dict(focus, lastTaskCreationDay=second[-1]), today, now)
    if task:
        focus["lastTaskCreationDay"] = today
    records.write(ds, {
        "settings": {"mode": "rpg"},
        "run:demo": {"journeyId": "first-things-first", "journeyVersion": 1,
                     "startDay": first[0], "why": "Fewer scattered mornings at work"},
        "stage:demo:one-thing": {"acceptedDay": first[0]},
        "binding:demo:one-thing": {"taskId": f"rpt_demo-one-thing_{first[-1]}",
                                   "repeatCfgId": "demo-one-thing", "day": first[0]},
        "stage-done:demo:one-thing": {"day": stage_done, "xp": 50, "damage": 0},
        "stage:demo:focus-15": {"acceptedDay": stage_done},
        "binding:demo:focus-15": {"taskId": f"rpt_demo-focus-15_{today}",
                                  "repeatCfgId": "demo-focus-15", "day": stage_done},
    })
    # The first stage's task was replaced by the next stage's; paused so it
    # makes no more instances in the demo.
    one["isPaused"] = True
