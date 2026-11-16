"""What a new journey builds, on the start page (QuestArc docs/behaviour.md,
screen 3): at a moment that already has its thing, a further journey
builds another of the same kind and there is nothing to choose; else
"You build: …" with the first version, and the kinds to change it in
place. Only a choice other than the suggestion is written, with the
start, through the engine's `chooseBuild`."""
from gi.repository import Adw, Gtk

from pensum.game import content, engine
from pensum.game.content import t
from pensum.ui.journey import art

DEFAULT_LADDER = "home"  # QuestArc's LADDERS.defaultLadder
THINGS_PER_PLACE = 3


def suggested_ladder(journey, ladders):
    """QuestArc's resolveBuild without a choice: the journey's, else the default."""
    name = (journey.get("build") or {}).get("ladder")
    return name if name in ladders else DEFAULT_LADDER


class BuildPart:
    def __init__(self, page, journey, anchor_id):
        self.page, self.journey, self.anchor_id = page, journey, anchor_id
        self.group = page.group(t("ui.build.title"))
        self.ladders = content.ladders()
        self.suggested = suggested_ladder(journey, self.ladders)
        self.chosen = self.suggested
        self._rows = []
        self.refresh()

    def _things_here(self):
        anchor_id = self.anchor_id()
        place = next((p for p in (self.page.model.view or {}).get("valley", ())
                      if anchor_id and p.get("anchorId") == anchor_id), None)
        return len((place or {}).get("things") or ())

    def further(self):
        return self._things_here() > 0

    def refresh(self):
        for row in self._rows:
            self.group.remove(row)
        self._rows = []
        things = self._things_here()
        self.group.set_description("")
        if things:
            self.group.set_description(t("ui.start.full" if things >= THINGS_PER_PLACE
                                         else "ui.start.grows-on"))
            return
        if self.suggested not in self.ladders:
            self.group.set_visible(False)
            return
        self.group.set_description(t("ui.build.one-thing"))
        self.expander = Adw.ExpanderRow(subtitle=t("ui.build.change"))
        self.picture = Gtk.Box(valign=Gtk.Align.CENTER)
        self.expander.add_prefix(self.picture)
        first = None
        for name, ladder in self.ladders.items():
            check = Gtk.CheckButton(active=name == self.chosen, group=first,
                                    valign=Gtk.Align.CENTER)
            first = first or check
            row = Adw.ActionRow(title=ladder["title"], activatable_widget=check,
                                subtitle=t("ui.build.suggested") if name == self.suggested else "")
            row.add_prefix(check)
            row.add_suffix(self._first_version(ladder))
            check.connect("toggled", lambda c, n=name: c.get_active() and self._choose(n))
            self.expander.add_row(row)
        self.group.add(self.expander)
        self._rows.append(self.expander)
        self._show_choice()

    @staticmethod
    def _first_version(ladder):
        return art.picture_area(ladder["versions"][0]["art"], 60, card=True,
                                hue=ladder.get("hue"), height=40, part=ladder.get("row"))

    def _choose(self, name):
        self.chosen = name
        self._show_choice()

    def _show_choice(self):
        ladder = self.ladders[self.chosen]
        self.expander.set_title(t("ui.build.start", summary=ladder["title"]))
        child = self.picture.get_first_child()
        if child:
            self.picture.remove(child)
        self.picture.append(self._first_version(ladder))

    def changes(self, run_id):
        """The run's `build` record when the user chose another kind."""
        if self.further() or self.chosen == self.suggested:
            return {}
        return engine.action("chooseBuild", run_id, {"ladder": self.chosen})
