"""The weekly look back (QuestArc design rule 9): one question, the
validated automaticity item with the user's habit filled in, answered
1–7, or skipped for the week."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import capitalise
from pensum.ui.journey.banners import iso_week
from pensum.ui.journey.base import JourneySubpage


class CheckinPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.checkin.title"), "journey-checkin")
        run, _journey, _index, _station, stage = self.model.current()
        self.run_id, self.stage_id = run["runId"], stage["id"]
        self.week = iso_week(self.model.view["todayStr"])
        habit = t("ui.checkin.habit", action=capitalise(t(stage["plan"]["action"])),
                  anchor=t(stage["plan"]["anchor"]))
        self.text(t("ui.checkin.question", habit=habit), "title-4")
        group = self.group()
        scale = Gtk.Box(spacing=4, homogeneous=True, margin_top=6)
        for score in range(1, 8):
            button = Gtk.Button(label=str(score))
            button.set_size_request(44, 44)
            button.update_property([Gtk.AccessibleProperty.LABEL],
                                   [t("ui.checkin.score", score=score)])
            button.connect("clicked", lambda _b, s=score: self._answer(s))
            scale.append(button)
        group.add(scale)
        ends = Gtk.Box(margin_top=6)
        for text, align in ((t("ui.checkin.low"), 0), (t("ui.checkin.high"), 1)):
            label = Gtk.Label(label=text, xalign=align, hexpand=True)
            label.add_css_class("caption")
            label.add_css_class("dimmed")
            ends.append(label)
        group.add(ends)
        self.set_main(t("ui.action.skip"), self._skip)

    def _seen(self):
        key = f"checkin:{self.run_id}:{self.stage_id}:{self.week}"
        if key not in self.window.settings.seen:
            self.window.settings.seen.append(key)
            self.window.save_settings()

    def _answer(self, score):
        self._seen()
        self.model.action("answerCheckin", self.run_id, self.stage_id, self.week, score)
        self.back_to_journey()

    def _skip(self):
        self._seen()
        self.back_to_journey()
        self.model._notify()
