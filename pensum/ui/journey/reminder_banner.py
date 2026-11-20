"""QuestArc's words about the reminder of a followed task (QuestArc
docs/behaviour.md, flow H): in a station's first two weeks without one,
whether a reminder would help; once the weekly answers have risen, that
it may not be needed any more. Day Planner never sets or removes a
reminder here: **Open the task** leads to the task, whose Repeat page
holds the time and the reminder. Both are put away with **Not Now** on
this device, the second for the week."""
from pensum.game import stages
from pensum.game.content import t

SUGGEST_DAYS = 14  # days after a stage was accepted in which one is suggested


def question(run, key):
    """"Would a reminder at 21:30 help …": a fixed-time moment names its time."""
    anchor = run.get("anchor") or {}
    if anchor.get("kind") == "time" and anchor.get("time"):
        return t(f"{key}-at", time=anchor["time"])
    return t(key)


def reminder_banner(page, run_id, stage_id, reminder, week, fade, suggest=None, age=None):
    """At most one banner; [] when nothing is to be said."""
    from pensum.ui.journey.habits import banner_box
    if not reminder:
        return []
    window = page.window
    seen = window.settings.seen
    ident = f"{run_id}:{stage_id}"
    key = f"fade:{ident}:{week}" if reminder.get("fade") else f"reminder:{ident}"
    if reminder.get("fade"):
        text = fade
    elif not reminder.get("set") and suggest and (SUGGEST_DAYS if age is None else age) \
            < SUGGEST_DAYS:
        text = suggest
    else:
        text = None
    if not text or key in seen:
        return []

    def not_now():
        seen.append(key)
        window.save_settings()
        page.refresh()

    choices = [(t("ui.action.not-now"), not_now)]
    cfg = stages.rule_of_binding(window.ds, run_id, stage_id)
    task_id = stages.task_of_rule(window.ds, cfg)
    if task_id:
        choices.append((t("ui.setup.open"), lambda: window.show_task(task_id)))
    return [banner_box(text, *choices)]
