"""Start smaller after a long break (QuestArc docs/behaviour.md, flow D):
the finished station before the current one is walked again. The page
says what stays and which task counts, and lets the user also call the
gap a pause; **Start Smaller** writes `stepBack`, then the task is set up
(flow B) when the earlier one no longer repeats. Back changes nothing."""
from gi.repository import Adw, Gtk

from pensum.game import stages
from pensum.game.content import t
from pensum.game.sentences import plan_sentence, short_date
from pensum.ui.journey.base import JourneySubpage

# QuestArc's sentence names Super Productivity; Day Planner's repeat is on
# the task's Repeat page.
CURRENT_TASK = ("The task of the larger step stays as it is. Afterwards you could pause or "
                "end its repeat on its Repeat page so you don't keep both.")


class SmallerPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.comeback.smaller"), "journey-smaller")
        current = self.model.current()
        run = current[0] if current else None
        index = (run["position"]["stage"] - 1) if run else -1
        journey = current[1] if current else None
        if not run or index < 0 or (run.get("comeBack") or {}).get("smaller") != \
                journey["stages"][index]["id"]:
            self.text(t("ui.error.gone"))
            return
        stage = journey["stages"][index]
        today = self.model.view["todayStr"]
        group = self.group(t("ui.station.of", n=index + 1, total=len(journey["stages"])))
        group.add(Adw.ActionRow(title=plan_sentence(stage, run["stations"][index].get("pair"),
                                                    run.get("anchor")), title_lines=0))
        self.text(t("ui.smaller.text"))
        self.earlier = stages.rule_of_stage(window.ds, run["runId"], stage["id"], today)
        self.text(t("ui.smaller.task-earlier" if self.earlier else "ui.smaller.task-new"))
        self.text(CURRENT_TASK, "dimmed")
        pause = self.group()
        self.pause = Gtk.Switch(valign=Gtk.Align.CENTER)
        row = Adw.ActionRow(title=t("ui.smaller.pause",
                                    date=short_date(run["comeBack"]["from"])),
                            title_lines=0, activatable_widget=self.pause)
        row.add_suffix(self.pause)
        pause.add(row)
        self.set_main(t("ui.comeback.smaller"), lambda: self._start(run))

    def _start(self, run):
        today = self.model.view["todayStr"]
        if not self.model.action("stepBack", run, today, {"pause": self.pause.get_active()}):
            return
        self.back_to_journey()
        if not self.earlier:
            from pensum.ui.journey.setup_page import SetupPage
            self.window.nav.push(SetupPage(self.window))
