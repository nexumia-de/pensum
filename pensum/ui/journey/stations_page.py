"""The stations of the active journey as a list in journey order
(QuestArc docs/behaviour.md, screen 4): number, action and state in
words; a row opens the station's details."""
from gi.repository import Adw, Gtk

from pensum.game.content import t
from pensum.game.sentences import capitalise
from pensum.ui.journey.base import JourneySubpage


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
        group = self.group()
        total = len(run["stations"])
        for index, (station, stage) in enumerate(zip(run["stations"], journey["stages"])):
            row = Adw.ActionRow(
                title=capitalise(t(stage["plan"]["action"])), title_lines=2,
                subtitle=f"{t('ui.station.of', n=index + 1, total=total)} · "
                         f"{t('ui.build.station.' + station['state'])}",
                activatable=True)
            row.add_css_class("pensum-journey-station")
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated",
                        lambda _r, i=index: self.window.journey_page.show_station(i))
            group.add(row)
