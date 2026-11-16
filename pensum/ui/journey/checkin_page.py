"""The weekly look back (QuestArc docs/behaviour.md, screen 6; design
rule 9): the last due days and the run, the answers so far week by week,
and one question, the validated automaticity item with the user's habit
filled in, answered 1–7 or skipped for the week. The same page asks
about the habit a finished journey left (`run_id`), every four weeks
after eight weeks ("Look back")."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import habit_name
from pensum.ui.journey.answers_row import answers_box
from pensum.ui.journey.banners import iso_week
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.card import last_days
from pensum.ui.journey.habits import habit_of


class CheckinPage(JourneySubpage):
    def __init__(self, window, run_id=None):
        super().__init__(window, t("ui.checkin.title"), "journey-checkin")
        model = self.model
        if run_id is not None:
            found = habit_of(model, run_id)
            if not found:
                self.text(t("ui.error.gone"))
                return
            run, _journey, stage, habit = found
            if habit.get("fourWeekly"):
                self.set_title(t("ui.checkin.title-4"))
            marks, runs, answers = habit.get("lastDays"), habit.get("run"), habit.get("answers")
        else:
            run, _journey, index, station, stage = model.current()
            marks, runs, answers = station.get("lastDays"), station.get("run"), run.get("answers")
        self.run_id, self.stage_id = run["runId"], stage["id"]
        self.week = iso_week(model.view["todayStr"])
        if marks:
            group = self.group()
            group.add(last_days(marks))
            if runs:
                group.add(Gtk.Label(label=t("ui.card.run", current=runs["current"],
                                            best=runs["best"], total=runs["total"]),
                                    xalign=0, wrap=True, css_classes=["caption", "dimmed"]))
        if answers:
            self.group().add(answers_box(answers))
        self.text(t("ui.checkin.question", habit=habit_name(stage, run.get("anchor"))), "title-4")
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
        if self.model.action("answerCheckin", self.run_id, self.stage_id, self.week, score):
            self.window.nav.pop()

    def _skip(self):
        self._seen()
        self.window.nav.pop()
        self.model._notify()
