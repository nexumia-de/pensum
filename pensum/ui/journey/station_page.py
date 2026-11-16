"""A station's details (QuestArc docs/behaviour.md, screen 5): its
arrival story, plan, schedule and condition, when it was finished or
passed as already yours (with **Do This Station After All** while the
engine allows it), a station left to start smaller, the "Try this"
nugget, **Pair it with** for the current station and the user's plan for
the obstacle from the plan check."""
from gi.repository import Adw

from pensum.game.content import t
from pensum.game.sentences import (capitalise, condition_details, condition_text,
                                   plan_sentence, schedule_text, short_date)
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.pair_row import pair_group

CURRENT = ("current", "met", "unbound", "unsupported-repeat")


class StationPage(JourneySubpage):
    def __init__(self, window, index):
        run = self.model_run(window)
        journey = window.journeys.journey(run["journeyId"])
        stage = journey["stages"][index]
        super().__init__(window, capitalise(t(stage["plan"]["action"])),
                         f"journey-station-{index}")
        self.index = index
        self.listen(self.refresh)
        self.refresh()

    def refresh(self):
        self.clear()
        self.set_main(None, None)
        run = self.model.active()
        journey = self.model.journey(run["journeyId"]) if run else None
        if not journey or self.index >= len(run["stations"]):
            self.text(t("ui.error.gone"))
            return
        index = self.index
        stage, station = journey["stages"][index], run["stations"][index]
        state = station["state"]
        reached = state != "ahead"
        story = (stage.get("story") or {}).get("arrival")
        if story and reached:
            self.text(t(story), "title-4")
        group = self.group(t("ui.station.of", n=index + 1, total=len(run["stations"])))
        plan_row = Adw.ActionRow(title=plan_sentence(stage, station.get("pair"), run.get("anchor")),
                                 title_lines=0, subtitle=schedule_text(stage["schedule"]))
        group.add(plan_row)
        detail = condition_text(stage, station) if state in ("current", "met") \
            else condition_details(stage)
        group.add(Adw.ActionRow(title=detail, title_lines=0))
        if station.get("doneDay"):
            group.add(Adw.ActionRow(title=t("ui.details.finished",
                                            date=short_date(station["doneDay"]))))
        if station.get("skippedDay"):
            group.add(Adw.ActionRow(title=t("ui.details.skipped",
                                            date=short_date(station["skippedDay"])),
                                    title_lines=0))
            if station.get("undoable"):
                self.set_main(t("ui.details.skip-undo"), lambda: self._undo_skip(run, journey,
                                                                                 stage["id"]))
        if station.get("leftDay"):
            group.add(Adw.ActionRow(title=t("ui.details.left",
                                            date=short_date(station["leftDay"])),
                                    title_lines=0))
        plan = (run.get("planCheck") or {}).get("plan")
        if plan and reached:
            group.add(Adw.ActionRow(title=t("ui.check.yours", plan=plan), title_lines=0))
        if stage.get("nugget") and reached:
            self.text(t("ui.details.try"), "heading")
            self.text(t(stage["nugget"]))
        if index == run["position"]["stage"] and state in CURRENT:
            pair_group(self, run, stage["id"], station.get("pair"), lambda pair: plan_row.set_title(
                plan_sentence(stage, pair, run.get("anchor"))))

    def _undo_skip(self, run, journey, stage_id):
        if self.model.action("undoSkip", run, journey, stage_id):
            self.set_main(None, None)

    @staticmethod
    def model_run(window):
        return window.journeys.active()
