"""The current station's card (QuestArc docs/behaviour.md, screen 4): the
plan, the condition as a bar and in words, the last due days, the runs,
a hint and the user's own reason. A gap shows
as a gap, never as a loss."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import condition_text, plan_sentence, short_date
from pensum.store import dates
from pensum.ui.journey.drawing import day_mark

HINTS = {"current": "ui.card.hint", "met": "ui.card.met", "unbound": "ui.card.unbound",
         "unsupported-repeat": "ui.card.unsupported"}
PENSUM_HINTS = {"current": "Tick off the task in your task list as usual."}


def _label(text, *classes, **kwargs):
    label = Gtk.Label(label=text, xalign=0, wrap=True, **kwargs)
    for name in classes:
        label.add_css_class(name)
    return label


def last_days(marks):
    row = Gtk.Box(spacing=4, homogeneous=True)
    for item in marks:
        day = dates.parse_day(item["day"])
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cell.append(day_mark(item["mark"]))
        letters = Gtk.Label(label=day.strftime("%a")[:2])
        letters.add_css_class("caption")
        letters.add_css_class("dimmed")
        cell.append(letters)
        words = t(f"ui.mark.{item['mark']}")
        cell.set_tooltip_text(f"{short_date(item['day'])}: {words}")
        cell.update_property([Gtk.AccessibleProperty.LABEL],
                             [f"{day.strftime('%A')} {short_date(item['day'])}: {words}"])
        row.append(cell)
    row.update_property([Gtk.AccessibleProperty.LABEL], [t("ui.days.label")])
    return row


def card_hint(run, station, today):
    """The muted line under the card (QuestArc journey/card.ts): when the
    journey starts, staying a while, started smaller, or the state's hint."""
    state = station["state"]
    if station.get("acceptedDay") and station["acceptedDay"] > today:
        return t("ui.card.starts", date=short_date(station["acceptedDay"]))
    if state == "current" and station.get("stepBackDay"):
        return t("ui.card.smaller", date=short_date(station["stepBackDay"])).replace(
            t("ui.card.hint"), PENSUM_HINTS["current"])
    if state == "met" and (run.get("offer") or {}).get("quietUntil"):
        return t("ui.card.staying")
    return PENSUM_HINTS.get(state) or (t(HINTS[state]) if state in HINTS else "")


def station_card(run, stage, index, station, today):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=6,
                   margin_bottom=6)
    card.add_css_class("card")
    card.add_css_class("pensum-journey-card")
    card.append(_label(t("ui.station.of", n=index + 1, total=len(run["stations"])),
                       "caption-heading", "dimmed"))
    card.append(_label(plan_sentence(stage, station.get("pair"), run.get("anchor")), "title-4"))
    bound = station["state"] in ("current", "met")
    if bound:
        bar = Gtk.LevelBar(min_value=0, max_value=1, value=station["progress"])
        text = condition_text(stage, station)
        bar.update_property([Gtk.AccessibleProperty.LABEL], [text])
        card.append(bar)
        card.append(_label(text))
        if station.get("lastDays"):
            card.append(last_days(station["lastDays"]))
            r = station["run"]
            card.append(_label(t("ui.card.run", current=r["current"], best=r["best"],
                                 total=r["total"]), "caption", "dimmed"))
    hint = card_hint(run, station, today)
    if hint:
        card.append(_label(hint, "caption", "dimmed"))
    # The card after a long break shows the reason itself.
    if run.get("why") and not run.get("comeBack"):
        card.append(_label(t("ui.card.why", why=run["why"]), "pensum-journey-why"))
    return card
