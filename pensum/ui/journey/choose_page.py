"""Choosing a journey (QuestArc docs/behaviour.md, screen 2): the
journeys with their first step, then a preview with every station as a
plan sentence, its author, and Start This Journey."""
from gi.repository import Adw, Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.game.sentences import plan_sentence
from pensum.ui.journey.base import JourneySubpage


class ChoosePage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.choose.title"), "journey-choose")
        group = self.group()
        for journey in content.journeys():
            first = journey["stages"][0]
            lines = [t("ui.choose.stations", n=len(journey["stages"]))]
            if journey.get("author"):
                lines.append(t("ui.journey.author", name=journey["author"]))
            lines.append(plan_sentence(first))
            row = Adw.ActionRow(title=t(journey["title"]),
                                subtitle=t(journey["description"]) + "\n" + " · ".join(lines[:-1])
                                + "\n" + lines[-1], activatable=True, subtitle_lines=0)
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, j=journey: window.nav.push(
                PreviewPage(window, j["id"])))
            group.add(row)


class PreviewPage(JourneySubpage):
    def __init__(self, window, journey_id):
        journey = content.journey(journey_id)
        super().__init__(window, t(journey["title"]), f"journey-preview-{journey_id}")
        self.text(t(journey["description"]))
        if journey.get("author"):
            self.text(t("ui.journey.author", name=journey["author"]), "dimmed", "caption")
        group = self.group(t("ui.preview.stations"))
        for index, stage in enumerate(journey["stages"], 1):
            row = Adw.ActionRow(title=plan_sentence(stage), title_lines=0)
            number = Gtk.Label(label=str(index))
            number.add_css_class("numeric")
            number.add_css_class("dimmed")
            row.add_prefix(number)
            group.add(row)
        self.set_main(t("ui.preview.start"), lambda: self._start(journey_id))

    def _start(self, journey_id):
        from pensum.ui.journey.start_page import StartPage
        self.window.nav.push(StartPage(self.window, journey_id))
