"""The habits finished journeys leave (QuestArc docs/behaviour.md, flow
F and screen 7) and their banners: at most one per habit, the question
after graduation, the offer to graduate (with **Not Now**, a choice
written through `graduateLater`), or its weekly look back. Each is put
aside on this device when closed; the shelf keeps the quiet way to all.
The banner about a reminder that may not be needed waits for Day
Planner's reminders (pensum#13)."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import habit_name
from pensum.ui.journey.banners import iso_week


def habits_of(model):
    """(run, journey, stage, habit) of every finished journey with a habit."""
    found = []
    for run in (model.view or {}).get("finished") or ():
        habit = run.get("habit")
        journey = model.journey(run["journeyId"])
        stage = next((s for s in (journey or {}).get("stages", ())
                      if habit and s["id"] == habit["stageId"]), None)
        if habit and stage:
            found.append((run, journey, stage, habit))
    return found


def habit_of(model, run_id):
    return next((h for h in habits_of(model) if h[0]["runId"] == run_id), None)


def banner_box(text, *choices):
    """A banner with one or two text buttons, each (label, on_click)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                  css_classes=["card", "pensum-journey-banner"])
    label = Gtk.Label(label=text, xalign=0, wrap=True, margin_top=12, margin_start=12,
                      margin_end=12)
    box.append(label)
    row = Gtk.Box(spacing=6, halign=Gtk.Align.END, margin_bottom=6, margin_end=6)
    for name, on_click in choices:
        button = Gtk.Button(label=name, css_classes=["flat"])
        button.set_size_request(-1, 44)
        button.connect("clicked", lambda *_a, c=on_click: c())
        row.append(button)
    box.append(row)
    box.update_property([Gtk.AccessibleProperty.LABEL], [text])
    return box


def habit_banners(page, anchor_id=None):
    model, window = page.model, page.window
    today = model.view["todayStr"]
    seen = window.settings.seen
    out = []
    for run, _journey, stage, habit in habits_of(model):
        if anchor_id is not None and (run.get("anchor") or {}).get("id") != anchor_id:
            continue
        name = habit_name(stage, run.get("anchor"))
        run_id = run["runId"]
        due = (habit.get("graduated") or {}).get("checkDue")
        if due and f"still:{run_id}:{stage['id']}:{due}" not in seen:
            out.append(banner_box(t("ui.banner.still", habit=name),
                                  (t("ui.action.answer"), lambda r=run_id: page.show_still(r))))
        elif habit.get("canGraduate") and not habit.get("offerQuietUntil"):
            out.append(banner_box(
                t("ui.banner.graduate", habit=name),
                (t("ui.action.not-now"), lambda r=run: model.action("graduateLater", r, today)),
                (t("ui.action.look"), lambda r=run_id: page.show_graduate(r))))
        elif habit.get("checkinDue") and \
                f"checkin:{run_id}:{stage['id']}:{iso_week(today)}" not in seen:
            text = "ui.banner.habit-checkin-4" if habit.get("fourWeekly") \
                else "ui.banner.habit-checkin"
            out.append(banner_box(t(text, habit=name),
                                  (t("ui.action.answer"),
                                   lambda r=run_id: page.show_checkin(r))))
    return out
