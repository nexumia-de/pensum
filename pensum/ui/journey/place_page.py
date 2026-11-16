"""The place (QuestArc docs/behaviour.md, screen 0b): a place without a
growing journey opens here, also where nothing stands yet. The place
piece, large; the versions that stand and the line of state, once for each
thing; one card "Your routine here" with the steps in words; **Extend
This Moment**. Back leads to the Valley."""
from gi.repository import Adw, Gtk

from pensum.game import content, moments
from pensum.game.content import t
from pensum.game.sentences import capitalise
from pensum.ui.journey import place_piece
from pensum.ui.journey.base import JourneySubpage


def routine_rows(view, anchor):
    """(words, note) per step in the order they stand: the habits finished
    journeys left (still followed, or running by itself), then what waits."""
    rows = []
    for step in anchor.get("steps", []):
        journey = content.journey(step["journeyId"])
        stage = next((s for s in (journey or {}).get("stages", [])
                      if s["id"] == step["stageId"]), None)
        if stage:
            rows.append((capitalise(t(stage["plan"]["action"])),
                         t("ui.routine.by-itself" if step["state"] == "graduated"
                           else "ui.routine.followed")))
    for step in anchor.get("resting", []):
        journey = content.journey(step["journeyId"])
        if journey:
            rows.append((t(journey["title"]), t("ui.routine.waiting")))
    return rows


def routine_card(view, anchor):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"])
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12,
                    margin_bottom=12, margin_start=12, margin_end=12)
    card.append(inner)
    inner.append(Gtk.Label(label=t("ui.routine.title"), xalign=0, css_classes=["heading"]))
    rows = routine_rows(view, anchor)
    if not rows:
        inner.append(Gtk.Label(label=t("ui.anchor.nothing"), xalign=0, wrap=True,
                               css_classes=["dimmed"]))
    for words, note in rows:
        line = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        line.append(Gtk.Label(label=words, xalign=0, wrap=True))
        line.append(Gtk.Label(label=note, xalign=0, css_classes=["caption", "dimmed"]))
        inner.append(line)
    if any(s["state"] == "graduated" for s in anchor.get("steps", [])):
        inner.append(Gtk.Label(label=t("ui.routine.nothing-ticked"), xalign=0, wrap=True,
                               css_classes=["caption", "dimmed"]))
    return card


class PlacePage(JourneySubpage):
    def __init__(self, window, anchor_id):
        view = window.journeys.view or {}
        found = next((p for p in view.get("valley", []) if p["anchorId"] == anchor_id), None)
        # No tag: pages of different places are pushed one after the other.
        super().__init__(window, moments.place_title(view, found) if found else "", None)
        self.anchor_id = anchor_id
        self.listen(self._show)
        self._show()

    def _show(self):
        self.clear()
        view = self.model.view or {}
        place = next((p for p in view.get("valley", []) if p["anchorId"] == self.anchor_id), None)
        anchor = moments.anchor(view, self.anchor_id)
        if place is None or anchor is None:
            return  # removed: the page goes with it
        self.set_title(moments.place_title(view, place))
        group = self.group()
        group.add(place_piece.section(self.window, view, place))
        group = self.group()
        group.add(routine_card(view, anchor))
        extend = Adw.ButtonRow(title=t("ui.anchor.extend")) if hasattr(Adw, "ButtonRow") \
            else Adw.ActionRow(title=t("ui.anchor.extend"), activatable=True)
        extend.connect("activated", lambda *_: self._extend())
        self.group().add(extend)

    def _extend(self):
        from pensum.ui.journey.choose_page import ChoosePage
        self.window.nav.push(ChoosePage(self.window, self.anchor_id))
