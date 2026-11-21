"""Continuing after a met station (QuestArc docs/behaviour.md, flow C):
the acceptance story and the next plan, then two equal choices,
**Continue** and **Stay Here a While**; the latest weekly answer
suggests one (`offer.suggest`, game rules §4). Continue writes the
checkpoint and accepts the next stage (or ends the journey after the
last one); from a station walked again after a step back it takes up the
station that was left. Stay writes the `stay` record and leads back."""
from gi.repository import Adw

from pensum.game.content import t
from pensum.game.sentences import plan_sentence
from pensum.ui.journey.base import JourneySubpage
from pensum.i18n import _

SUGGESTIONS = {"continue": "ui.continue.suggest-continue", "stay": "ui.continue.suggest-stay"}


class ContinuePage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.continue.title"), "journey-continue")
        current = self.model.current()
        if not current or current[3]["state"] != "met":
            self.text(t("ui.error.gone"))
            return
        run, journey, index, station, stage = current
        again = station.get("stepBackDay") is not None
        story = (stage.get("story") or {}).get("accept")
        if story and not again:
            self.text(t(story), "title-4")
        following = journey["stages"][index + 1] if index + 1 < len(journey["stages"]) else None
        if following:
            group = self.group(t("ui.station.of", n=index + 2, total=len(journey["stages"])))
            # The station left keeps its own pairing; a new one inherits this one's.
            nxt = run["stations"][index + 1]
            pair = nxt.get("pair") or (None if again else station.get("pair"))
            group.add(Adw.ActionRow(title=plan_sentence(following, pair, run.get("anchor")),
                                    title_lines=0))
            self.text(t("ui.continue.again") if again else
                      _("Next you set up the task for this station. Your earlier task keeps "
                        "repeating as it is; you can stop it on its Repeat page."), "dimmed")
        else:
            self.text(t("ui.continue.last"))
        offer = run.get("offer") or {}
        suggest = offer.get("suggest", "none")
        if suggest == "stay" and offer.get("answer") is None:
            self.text(t("ui.continue.suggest-new"))
        elif suggest in SUGGESTIONS:
            self.text(t(SUGGESTIONS[suggest]))
        self.text(t("ui.continue.choice"), "dimmed")
        self.set_choices(
            (t("ui.action.continue") if following else t("ui.continue.finish"),
             lambda: self._go(run, journey, following, again), suggest == "continue"),
            (t("ui.action.stay"), lambda: self._stay(run), suggest == "stay"))

    def _go(self, run, journey, following, again):
        today = self.model.view["todayStr"]
        if not self.model.action("continueJourney", run, journey, today):
            return
        self.back_to_journey()
        if again:
            return
        if following:
            from pensum.ui.journey.setup_page import SetupPage
            self.window.nav.push(SetupPage(self.window))
        else:
            self.window.nav.push(FinishedPage(self.window, journey))

    def _stay(self, run):
        if self.model.action("stayHere", run, self.model.view["todayStr"]):
            self.back_to_journey()


class FinishedPage(JourneySubpage):
    def __init__(self, window, journey):
        super().__init__(window, t("ui.finished.title"), "journey-finished")
        if journey.get("ending"):
            self.text(t(journey["ending"]["story"]), "title-4")
        self.text(t("ui.finished.habit"))
        self.set_main(t("ui.finished.done"), self.window.show_journey)
