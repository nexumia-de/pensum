"""The weekly answers so far as a row, week by week (QuestArc docs/
behaviour.md, screen 6; design rule 9): one mark per week with its
number, an empty mark for a skipped week, every mark with its words for
screen readers, and under the row what the engine says about the trend
("Easier than four weeks ago."), nothing when the answer is lower. No
target line, no number to reach."""
from gi.repository import Gtk

from pensum.game.content import t

TRENDS = {"easier": "ui.answers.easier", "same": "ui.answers.same"}


def answers_box(answers):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    box.append(Gtk.Label(label=t("ui.answers.label"), xalign=0, wrap=True,
                         css_classes=["caption-heading", "dimmed"]))
    row = Gtk.Box(spacing=4, homogeneous=True)
    for week in answers.get("weeks") or ():
        number = week["week"].split("-W")[-1].lstrip("0")
        score = week.get("score")
        words = t("ui.answers.week", week=number, score=score) if score is not None \
            else t("ui.answers.none", week=number)
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        level = Gtk.LevelBar(min_value=0, max_value=7, value=score or 0,
                             orientation=Gtk.Orientation.VERTICAL, inverted=True,
                             height_request=28, halign=Gtk.Align.CENTER)
        cell.append(level)
        cell.append(Gtk.Label(label=str(score) if score is not None else "–",
                              css_classes=["caption", "dimmed"]))
        cell.set_tooltip_text(words)
        cell.update_property([Gtk.AccessibleProperty.LABEL], [words])
        row.append(cell)
    box.append(row)
    if answers.get("trend") in TRENDS:
        box.append(Gtk.Label(label=t(TRENDS[answers["trend"]]), xalign=0, wrap=True))
    return box
