"""What you build (QuestArc docs/behaviour.md, screen 3a), from the
journey's menu in the game: what grows (a ladder), what hangs on the
marker and the colour. Each change is written at once through the
engine's `chooseBuild`; only what the user picked is stored, the rest
follows the journey. Nothing built is lost by changing: the same progress
is drawn as the other thing."""
import math

from gi.repository import Adw, Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.ui.journey import art
from pensum.ui.journey.base import JourneySubpage


def _swatch(hue, title):
    """A disc in the hue's accent; the row's title carries the name."""
    area = Gtk.DrawingArea(content_width=28, content_height=28, valign=Gtk.Align.CENTER,
                           accessible_role=Gtk.AccessibleRole.IMG)
    area.update_property([Gtk.AccessibleProperty.LABEL], [title])

    def draw(area, cr, width, height):
        cr.set_source_rgb(*art.colours(area, True, hue)["accent"])
        cr.arc(width / 2, height / 2, min(width, height) / 2 - 2, 0, 2 * math.pi)
        cr.fill()

    area.set_draw_func(draw)
    return area


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
        ladder = content.ladder(choice.get("ladder") or run["build"]["ladder"]) or {}
        kind = content.markers().get(choice.get("marker")) or {}
        if kind.get("landOnly") and ladder.get("water"):
            del choice["marker"]  # no longer fits: the ladder's own applies
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
        water = (content.ladder(build["ladder"]) or {}).get("water")
        self._rows(self.group(t("ui.build.thing")), run, "ladder", [
            (name, ladder["title"], t("ui.build.suggested") if name == suggested else "",
             art.picture_area(ladder["versions"][0]["art"], 60, card=True, hue=build["hue"],
                              height=40, part=ladder.get("row")), True)
            for name, ladder in content.ladders().items()])
        self._rows(self.group(t("ui.build.hangs")), run, "marker", [
            (name, kind["title"], t("ui.build.land-only") if kind.get("landOnly") and water else "",
             art.picture_area(f"marker-{name}-bead", 28, card=True, hue=build["hue"]),
             not (kind.get("landOnly") and water))
            for name, kind in content.markers().items()])
        self._rows(self.group(t("ui.build.colour")), run, "hue", [
            (name, hue["title"], "", _swatch(name, hue["title"]), True)
            for name, hue in content.palette().items()])
        group = self.group(description=t("ui.build.keeps"))
        if self._choice(run):
            row = Adw.ButtonRow(title=t("ui.build.suggestion")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.build.suggestion"), activatable=True)
            row.connect("activated", lambda *_: self.model.action("chooseBuild", run["runId"], {}))
            group.add(row)
