"""The stations of the active journey as their own page (QuestArc
docs/behaviour.md, screen 4): in the game the journey page shows the
build instead of the path, so the path is reached from the menu."""
from pensum.game.content import t
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.path import journey_path


class StationsPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.build.stations"), "journey-stations")
        self.listen(self._show)
        self._show()

    def _show(self):
        self.clear()
        current = self.model.current()
        if not current:
            return
        run, journey = current[0], current[1]
        self.group().add(journey_path(run, journey, self.model.mode() == "rpg",
                                      self.window.journey_page.show_station))
