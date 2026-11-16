"""What you build (QuestArc docs/behaviour.md, screen 3a), from the
journey's menu in the game: what grows (a ladder). The colour belongs to
the place (QuestArc 4.1) and flowers are the only marker (4.2): there is
nothing else to choose. Each change is written at once through the
engine's `chooseBuild`; only what the user picked is stored, the rest
follows the journey. Nothing built is lost by changing: the same progress
is drawn as the other thing."""
from gi.repository import Adw, Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.ui.journey import art
from pensum.ui.journey.base import JourneySubpage


class BuildPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.build.title"), "journey-build")
        self.listen(self._show)
        self._show()

    def _choice(self, run):
        return dict(self.model.records().get(f"build:{run['runId']}") or {})

    def _choose(self, run, field, name):
        choice = self._choice(run)
        if choice.get(field) == name:
            return
        choice[field] = name
        self.model.action("chooseBuild", run["runId"], choice)

    def _rows(self, group, run, field, options):
        """One radio row per option: (name, title, subtitle, picture, enabled)."""
        first = None
        for name, title, subtitle, picture, enabled in options:
            check = Gtk.CheckButton(active=run["build"][field] == name, group=first,
                                    valign=Gtk.Align.CENTER)
            first = first or check
            row = Adw.ActionRow(title=title, subtitle=subtitle or "", activatable_widget=check,
                                sensitive=enabled)
            row.add_prefix(check)
            row.add_suffix(picture)
            group.add(row)
            # Connected after `active` is set, so drawing the page writes nothing.
            check.connect("toggled", lambda c, n=name: c.get_active()
                          and self._choose(run, field, n))

    def _show(self):
        self.clear()
        current = self.model.current()
        run = current[0] if current else None
        if not run or not run.get("build"):
            return
        build, journey = run["build"], current[1]
        suggested = (journey.get("build") or {}).get("ladder")
        self._rows(self.group(t("ui.build.thing")), run, "ladder", [
            (name, ladder["title"], t("ui.build.suggested") if name == suggested else "",
             art.picture_area(ladder["versions"][0]["art"], 60, card=True, hue=build["hue"],
                              height=40, part=ladder.get("row")), True)
            for name, ladder in content.ladders().items()])
        group = self.group(description=t("ui.build.keeps"))
        if self._choice(run):
            row = Adw.ButtonRow(title=t("ui.build.suggestion")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.build.suggestion"), activatable=True)
            row.connect("activated", lambda *_: self.model.action("chooseBuild", run["runId"], {}))
            group.add(row)
