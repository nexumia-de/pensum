"""The growing step as a card below the Valley (QuestArc docs/behaviour.md,
screen 0): "Growing here · Station 2 of 4", the plan sentence, the
condition in words and one line of state. A tap opens the journey. In
Super Productivity the tick itself stays in the task list."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import condition_text, plan_sentence

STATE = {"met": "ui.card.met", "unbound": "ui.card.unbound",
         "unsupported-repeat": "ui.card.unsupported"}


def state_line(run, station, today):
    """One line of state in words, or ''."""
    if run["paused"]:
        return t("ui.anchor.paused")
    if station["state"] in STATE:
        return t(STATE[station["state"]])
    last = (station.get("lastDays") or [{}])[-1]
    if last.get("day") == today and last.get("mark") == "done":
        return t("ui.anchor.today.done")
    if last.get("day") == today and last.get("mark") == "open":
        return t("ui.anchor.today.open")
    return ""


def growing_card(run, stage, index, station, today, on_open):
    lines = [t("ui.anchor.growing") + " · " + t("ui.station.of", n=index + 1,
                                                total=len(run["stations"]))]
    lines.append(plan_sentence(stage, station.get("pair"), run.get("anchor")))
    if station["state"] in ("current", "met"):
        lines.append(condition_text(stage, station))
    state = state_line(run, station, today)
    if state:
        lines.append(state)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["pensum-journey-card"])
    for n, text in enumerate(lines):
        classes = ["caption-heading", "dimmed"] if n == 0 else ["title-4"] if n == 1 else \
            ["caption", "dimmed"] if n == len(lines) - 1 and state else []
        box.append(Gtk.Label(label=text, xalign=0, wrap=True, css_classes=classes))
    button = Gtk.Button(child=box, css_classes=["card", "pensum-growing-card"])
    button.update_property([Gtk.AccessibleProperty.LABEL], [" ".join(lines)])
    button.connect("clicked", lambda *_: on_open())
    return button
