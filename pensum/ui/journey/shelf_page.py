"""The shelf (QuestArc docs/behaviour.md): waiting journeys to resume,
habits that stay, and finished journeys."""
from gi.repository import Adw, Gtk

from pensum.game.content import t
from pensum.game.sentences import capitalise, short_date
from pensum.ui.journey.base import JourneySubpage


class ShelfPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.shelf.title"), "journey-shelf")
        self.listen(self.refresh)
        self.refresh()

    def refresh(self):
        self.clear()
        view = self.model.view or {}
        paused, finished = view.get("paused") or [], view.get("finished") or []
        if not paused and not finished:
            self.text(t("ui.shelf.empty"), "dimmed")
            return
        if paused:
            group = self.group(t("ui.shelf.paused"))
            for run in paused:
                journey = self.model.journey(run["journeyId"])
                row = Adw.ActionRow(title=t(journey["title"]) if journey else run["journeyId"],
                                    subtitle=t("ui.shelf.waiting", n=run["position"]["stage"] + 1,
                                               total=len(run["stations"])))
                button = Gtk.Button(label=t("ui.action.resume"), valign=Gtk.Align.CENTER)
                button.connect("clicked", lambda _b, r=run: self._resume(r))
                row.add_suffix(button)
                group.add(row)
        if finished:
            habits = self.group(t("ui.shelf.habits"))
            journeys = self.group(t("ui.shelf.journeys"))
            for run in finished:
                journey = self.model.journey(run["journeyId"])
                if not journey:
                    continue
                done = [i for i, s in enumerate(run["stations"]) if s["state"] == "done"]
                if done:
                    stage = journey["stages"][done[-1]]
                    habits.add(Adw.ActionRow(title=capitalise(t(stage["plan"]["action"])),
                                             subtitle=t("ui.shelf.maintained")))
                end = run["stations"][done[-1]].get("doneDay") if done else None
                key = "ui.shelf.finished" if len(done) == len(run["stations"]) \
                    else "ui.shelf.ended"
                journeys.add(Adw.ActionRow(title=t(journey["title"]), subtitle=t(
                    key, start=short_date(run["startDay"]),
                    end=short_date(end) if end else "…")))

    def _resume(self, run):
        active = self.model.active()
        self.model.action("resumeJourney", run["runId"], self.model.view["todayStr"],
                          active["runId"] if active else None)
        self.back_to_journey()
