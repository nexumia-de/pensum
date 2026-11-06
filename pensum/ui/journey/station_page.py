"""A station's details (QuestArc docs/behaviour.md): its arrival story,
plan, schedule and condition, when it was finished, in the game its XP
and guardian, and its "Try this" nugget."""
from gi.repository import Adw

from pensum.game.content import t
from pensum.game.sentences import (capitalise, condition_details, condition_text,
                                   plan_sentence, schedule_text, short_date)
from pensum.ui.journey.base import JourneySubpage


class StationPage(JourneySubpage):
    def __init__(self, window, index):
        run = self.model_run(window)
        journey = window.journeys.journey(run["journeyId"])
        stage, station = journey["stages"][index], run["stations"][index]
        super().__init__(window, capitalise(t(stage["plan"]["action"])),
                         f"journey-station-{index}")
        story = (stage.get("story") or {}).get("arrival")
        if story and station["state"] != "ahead":
            self.text(t(story), "title-4")
        group = self.group(t("ui.station.of", n=index + 1, total=len(run["stations"])))
        group.add(Adw.ActionRow(title=plan_sentence(stage), title_lines=0,
                                subtitle=schedule_text(stage["schedule"])))
        detail = condition_text(stage, station) if station["state"] in ("current", "met") \
            else condition_details(stage)
        group.add(Adw.ActionRow(title=detail, title_lines=0))
        if station.get("doneDay"):
            group.add(Adw.ActionRow(title=t("ui.details.finished",
                                            date=short_date(station["doneDay"]))))
        rpg = window.journeys.mode() == "rpg"
        if rpg and station["xp"]:
            group.add(Adw.ActionRow(title=t("ui.details.xp", xp=station["xp"])))
        if rpg and stage.get("guardian"):
            group.add(Adw.ActionRow(title=t("ui.details.guardian", name=t(stage["guardian"]["name"]),
                                            hp=stage["guardian"]["hp"])))
        if stage.get("nugget") and station["state"] != "ahead":
            self.text(t("ui.details.try"), "heading")
            self.text(t(stage["nugget"]))

    @staticmethod
    def model_run(window):
        return window.journeys.active()
