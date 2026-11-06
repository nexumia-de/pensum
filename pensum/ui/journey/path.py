"""The journey's path (QuestArc docs/journey-design.md): stations from
the goal at the top to the start at the bottom, each a button with its
node, its action and its state in words; in the game the guardian with
its HP. Pressing a station opens its details."""
from gi.repository import Gtk, Pango

from pensum.game.content import t
from pensum.game.sentences import capitalise, short_date
from pensum.ui.journey.drawing import node

STATE_KEYS = {"current": "ui.station.here", "met": "ui.station.met",
              "unbound": "ui.station.unbound", "unsupported-repeat": "ui.station.unsupported"}


def state_text(station, index, current_index):
    if station["state"] == "done":
        return t("ui.station.done", date=short_date(station["doneDay"])) \
            if station.get("doneDay") else ""
    if station["state"] in STATE_KEYS:
        return t(STATE_KEYS[station["state"]])
    return t("ui.station.next") if index == current_index + 1 else ""


def journey_path(run, journey, rpg, on_station):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.add_css_class("pensum-journey-path")
    stations = run["stations"]
    total = len(stations)
    current = run["position"]["stage"]
    for index in reversed(range(total)):
        station, stage = stations[index], journey["stages"][index]
        name = capitalise(t(stage["plan"]["action"]))
        state = state_text(station, index, current)
        row = Gtk.Box(spacing=12)
        row.append(node(station["state"], index < total - 1, index > 0,
                        done_below=index <= current and index > 0,
                        done_above=index < current))
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER,
                         margin_top=8, margin_bottom=8, hexpand=True)
        title = Gtk.Label(label=name, xalign=0, wrap=True, lines=2,
                          ellipsize=Pango.EllipsizeMode.END)
        if index == current:
            title.add_css_class("heading")
        labels.append(title)
        if state:
            sub = Gtk.Label(label=state, xalign=0, wrap=True)
            sub.add_css_class("dimmed")
            sub.add_css_class("caption")
            labels.append(sub)
        guardian = stage.get("guardian")
        if rpg and guardian and station.get("guardian") and station["state"] != "done":
            g = station["guardian"]
            left = max(0, g["hp"] - g["damage"])
            text = t("ui.guardian.defeated") if g["defeated"] else \
                t("ui.guardian.hp", left=left, hp=g["hp"])
            label = Gtk.Label(label=f"{t(guardian['name'])} · {text}", xalign=0, wrap=True)
            label.add_css_class("caption")
            labels.append(label)
            bar = Gtk.LevelBar(min_value=0, max_value=g["hp"], value=left)
            bar.update_property([Gtk.AccessibleProperty.LABEL], [t(guardian["name"])])
            labels.append(bar)
        row.append(labels)
        button = Gtk.Button(child=row)
        button.add_css_class("flat")
        button.set_size_request(-1, 44)
        button.update_property([Gtk.AccessibleProperty.LABEL], [t(
            "ui.station.a11y", n=index + 1, total=total, name=name, state=state)])
        button.connect("clicked", lambda _b, i=index: on_station(i))
        box.append(button)
    return box

