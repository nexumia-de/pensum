"""What you build (QuestArc docs/behaviour.md, screen 3a), from the
journey's menu in the game: what grows (a ladder). The colour belongs to
the place (QuestArc 4.1) and flowers are the only marker for now (4.2);
what hangs shows only where a ladder lists more than one kind. At a place
the kind belongs to the place (QuestArc 4.3, #158): each change is
written at once to the place's record through the engine's
`choosePlaceKind`, covers every thing there and keeps the version
reached; **Use the journey's suggestion** is `withdrawPlaceKind`. A run
without a moment keeps the run's own `chooseBuild`. Only what the user
picked is stored, the rest follows the journey."""
from gi.repository import Adw, Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.ui.journey import art
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.place_piece import place_of_run


class BuildPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.build.title"), "journey-build")
        self.listen(self._show)
        self._show()

    def _choice(self, run):
        return dict(self.model.records().get(f"build:{run['runId']}") or {})

    def _place(self, run):
        return place_of_run(self.model.view, run["runId"])

    def _standing(self, run, field):
        """The kind that stands: the place's (every thing there), else the run's."""
        place = self._place(run)
        return place["things"][0][field] if place and field == "ladder" else run["build"][field]

    def _choose(self, run, field, name):
        place = self._place(run)
        if place and field == "ladder":
            if self._standing(run, field) != name:
                self.model.action("choosePlaceKind", self.model.view, place["anchorId"], name)
            return
        choice = self._choice(run)
        if choice.get(field) == name:
            return
        choice[field] = name
        self.model.action("chooseBuild", run["runId"], choice)

    def _picked(self, run):
        """Whether anything was chosen for the kind: the place's record, or
        the run's own `build` record."""
        place = self._place(run)
        return bool(self._choice(run)) or bool(place and place["chosen"].get("ladder"))

    def _suggest(self, run):
        place = self._place(run)
        if place:
            self.model.action("withdrawPlaceKind", self.model.view, place["anchorId"])
        else:
            self.model.action("chooseBuild", run["runId"], {})

    def _rows(self, group, run, field, options):
        """One radio row per option: (name, title, subtitle, picture, enabled)."""
        first = None
        for name, title, subtitle, picture, enabled in options:
            check = Gtk.CheckButton(active=self._standing(run, field) == name, group=first,
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
        if self._picked(run):
            row = Adw.ButtonRow(title=t("ui.build.suggestion")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.build.suggestion"), activatable=True)
            row.connect("activated", lambda *_: self._suggest(run))
            group.add(row)
