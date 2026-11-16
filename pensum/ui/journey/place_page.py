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
from pensum.ui.journey.habits import habit_banners


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
    """At 720 px and wider the piece stands on the left and the card on
    the right (QuestArc screen 0b); narrower, one column."""

    def __init__(self, window, anchor_id):
        view = window.journeys.view or {}
        found = next((p for p in view.get("valley", []) if p["anchorId"] == anchor_id), None)
        # No tag: pages of different places are pushed one after the other.
        super().__init__(window, moments.place_title(view, found) if found else "", None)
        self.anchor_id = anchor_id
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12,
                           margin_bottom=24, margin_start=12, margin_end=12)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
                                    child=self.box)
        wide = Adw.BreakpointBin(child=scroll, width_request=360, height_request=294)
        point = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 720sp"))
        point.add_setter(self.box, "orientation", Gtk.Orientation.HORIZONTAL)
        point.add_setter(self.box, "spacing", 24)
        wide.add_breakpoint(point)
        self.get_child().set_content(wide)
        self.listen(self._show)
        self._show()

    def _show(self):
        while (child := self.box.get_first_child()) is not None:
            self.box.remove(child)
        view = self.model.view or {}
        place = next((p for p in view.get("valley", []) if p["anchorId"] == self.anchor_id), None)
        anchor = moments.anchor(view, self.anchor_id)
        if place is None or anchor is None:
            return  # removed: the page goes with it
        self.set_title(moments.place_title(view, place))
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.START, hexpand=True)
        left.append(place_piece.section(self.window, view, place))
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True,
                        valign=Gtk.Align.START)
        right.append(routine_card(view, anchor))
        for banner in habit_banners(self, self.anchor_id):
            right.append(banner)
        extend = Gtk.Button(label=t("ui.anchor.extend"), css_classes=["pensum-bar-button"])
        extend.connect("clicked", lambda *_: self._extend())
        right.append(extend)
        self.box.append(left)
        self.box.append(right)

    def _extend(self):
        from pensum.ui.journey.choose_page import ChoosePage
        self.window.nav.push(ChoosePage(self.window, self.anchor_id))
