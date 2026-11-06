"""A journey stage's recurring task in Pensum: which repeat rules a
journey can follow (QuestArc game rules §2, due days) and setting up a
stage, which in Pensum creates the task and its repeat rule in one go
and binds it. No GTK."""
from pensum.game import engine, records
from pensum.game.content import t
from pensum.game.sentences import capitalise
from pensum.store import dates, tasks
from pensum.store.dataset import Context
from pensum.store.repeat import instances, rules, schedule

DAY_IDS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def supported(cfg):
    """Daily, every 2–7 days, or chosen weekdays every week; nothing that
    repeats from completion or waits for it."""
    if not cfg or cfg.get("repeatFromCompletionDate") or cfg.get("waitForCompletion"):
        return False
    every, cycle = cfg.get("repeatEvery"), cfg.get("repeatCycle")
    if cycle == "DAILY":
        return isinstance(every, int) and 1 <= every <= 7
    if cycle == "WEEKLY":
        return every == 1 and any(cfg.get(d) for d in schedule.WEEKDAYS)
    return False


def supported_rules(ds):
    return [c for c in instances.rules(ds) if supported(c)]


def rule_fields(stage_schedule, start):
    """Repeat rule fields for a stage's suggested schedule."""
    kind = stage_schedule["type"]
    if kind == "daily":
        return rules.schedule_fields("DAILY", start)
    if kind == "everyNDays":
        return rules.schedule_fields("CUSTOM", start, every=stage_schedule["n"], cycle="DAILY")
    days = tuple(schedule.WEEKDAYS[DAY_IDS.index(d)] for d in stage_schedule["days"])
    if days == schedule.WEEKDAYS[:5]:
        return rules.schedule_fields("MONDAY_TO_FRIDAY", start)
    return rules.schedule_fields("CUSTOM", start, cycle="WEEKLY", weekdays=days)


def task_title(stage):
    return t("ui.setup.task-title", anchor=capitalise(t(stage["plan"]["anchor"])),
             action=t(stage["plan"]["action"]))


def create_stage_task(ds, run_id, stage, start, now=None):
    """Create the stage's task with its repeat rule and bind it; returns
    the task. The rule starts on the stage's first day."""
    now = now or dates.now_ms()
    today = ds.today(now)
    task = tasks.add_task(ds, task_title(stage), Context.today(), now)
    cfg = rules.make_recurring(ds, task["id"], rule_fields(stage["schedule"], max(start, today)),
                               now)
    bind(ds, run_id, stage["id"], task["id"], cfg["id"], today)
    return task


def bind(ds, run_id, stage_id, task_id, cfg_id, day):
    records.write(ds, engine.action("bindStage", {"runId": run_id, "stageId": stage_id,
                                                  "taskId": task_id, "repeatCfgId": cfg_id,
                                                  "day": day}))


def bind_existing(ds, run_id, stage_id, cfg_id, now=None):
    """Bind a recurring task the user already has: its newest live
    instance, else the rule alone through any task id of it."""
    today = ds.today(now or dates.now_ms())
    live = sorted(instances.live_instances(ds, cfg_id), key=lambda x: x.get("created", 0))
    task_id = live[-1]["id"] if live else instances.instance_id(cfg_id, today)
    bind(ds, run_id, stage_id, task_id, cfg_id, today)


def bound_rule(ds, view):
    """The repeat rule bound to the active journey's current stage."""
    run = (view or {}).get("active")
    if not run:
        return None
    station = run["stations"][run["position"]["stage"]]
    binding = records.load(ds).get(f"binding:{run['runId']}:{station['stageId']}")
    if not isinstance(binding, dict):
        return None
    cfg_id = binding.get("repeatCfgId") or (ds.task(binding.get("taskId")) or {}).get("repeatCfgId")
    return ds.data["taskRepeatCfg"]["entities"].get(cfg_id)
