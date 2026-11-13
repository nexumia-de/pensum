"""Continuing after a met station (QuestArc docs/behaviour.md, flow C):
the acceptance story and the next plan, then the checkpoint and the next
stage; after the last station the journey ends and its ending shows."""
from pensum.game.content import t
from pensum.game.sentences import plan_sentence
from pensum.ui.journey.base import JourneySubpage


class ContinuePage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.continue.title"), "journey-continue")
        current = self.model.current()
        if not current:
            return
        run, journey, index, _station, stage = current
        story = (stage.get("story") or {}).get("accept")
        if story:
            self.text(t(story), "title-4")
        following = journey["stages"][index + 1] if index + 1 < len(journey["stages"]) else None
        if following:
            group = self.group("Next Station")
            from gi.repository import Adw
            group.add(Adw.ActionRow(title=plan_sentence(following), title_lines=0))
            self.text("Next you set up the task for this station. Your earlier task keeps "
                      "repeating as it is; you can stop it on its Repeat page.", "dimmed")
            self.set_main(t("ui.action.continue"), lambda: self._go(run, journey, True))
        else:
            self.text(t("ui.continue.last"))
            self.set_main(t("ui.continue.finish"), lambda: self._go(run, journey, False))

    def _go(self, run, journey, more):
        today = self.model.view["todayStr"]
        self.model.action("continueJourney", run, journey, today)
        if more:
            from pensum.ui.journey.setup_page import SetupPage
            self.back_to_journey()
            self.window.nav.push(SetupPage(self.window))
        else:
            self.back_to_journey()
            self.window.nav.push(FinishedPage(self.window, journey))


class FinishedPage(JourneySubpage):
    def __init__(self, window, journey):
        super().__init__(window, t("ui.finished.title"), "journey-finished")
        if journey.get("ending"):
            self.text(t(journey["ending"]["story"]), "title-4")
        self.text("Your habit stays: the recurring task keeps running as it is.")
        self.set_main(t("ui.finished.done"), self.back_to_journey)
