"""A graduated habit (QuestArc docs/behaviour.md, flow F): while the
question "does it still run by itself?" is due, the question with
**Yes, It Does**, **Not Really** and **Not Now** (put aside on this
device); otherwise the offer to bring the habit back, which the shelf
also opens. "Not really" changes nothing by itself. Bringing back takes
nothing away (`bringBack`); it is a page, not a one-tap button, because
it cannot be undone with one tap."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import habit_name, plan_sentence, short_date
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.habits import habit_of


class StillPage(JourneySubpage):
    def __init__(self, window, run_id):
        super().__init__(window, t("ui.still.title"), None)
        self.run_id = run_id
        self.listen(self.refresh)
        self.refresh()

    def refresh(self):
        self.clear()
        self.set_main(None, None)
        found = habit_of(self.model, self.run_id)
        graduated = found[3].get("graduated") if found else None
        if not graduated:
            self.text(t("ui.error.gone"))
            return
        run, _journey, stage, _habit = found
        today = self.model.view["todayStr"]
        plan = self.group()
        plan.add(Gtk.Label(label=plan_sentence(stage, run["stations"][-1].get("pair"),
                                               run.get("anchor")),
                           xalign=0, wrap=True, css_classes=["title-4"]))
        plan.add(Gtk.Label(label=t("ui.shelf.since", date=short_date(graduated["day"])),
                           xalign=0, wrap=True, css_classes=["caption", "dimmed"]))
        due = graduated.get("checkDue")
        if due:
            self.set_title(t("ui.still.title"))
            self.text(t("ui.still.question", habit=habit_name(stage, run.get("anchor"))),
                      "heading")
            self.text(t("ui.still.text"), "dimmed")
            later = Gtk.Button(label=t("ui.action.not-now"), halign=Gtk.Align.START,
                               css_classes=["flat"])
            later.set_size_request(-1, 44)
            later.connect("clicked", lambda *_: self._not_now(f"still:{run['runId']}:"
                                                              f"{stage['id']}:{due}"))
            self.group().add(later)
            self.set_choices(
                (t("ui.still.yes"), lambda: self._answer(run, today, True), True),
                (t("ui.still.no"), lambda: self._answer(run, today, False), False))
            return
        self.set_title(t("ui.still.back.title"))
        if graduated.get("suggestBack"):
            self.text(t("ui.still.back.said"))
        self.text(t("ui.still.back.text"))
        self.text(t("ui.still.back.task"), "dimmed")
        self.set_choices((t("ui.action.bring-back"), lambda: self._bring_back(run, today), True),
                         (t("ui.still.leave"), self.window.nav.pop, False))

    def _answer(self, run, today, still):
        if self.model.action("answerStill", run, today, still) and still:
            self.window.nav.pop()

    def _not_now(self, key):
        if key not in self.window.settings.seen:
            self.window.settings.seen.append(key)
            self.window.save_settings()
        self.window.nav.pop()
        self.model._notify()

    def _bring_back(self, run, today):
        if self.model.action("bringBack", run, today):
            from pensum.ui.journey.shelf_page import ShelfPage
            self.window.show_journey()
            self.window.nav.push(ShelfPage(self.window))
