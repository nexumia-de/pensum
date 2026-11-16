"""Change this moment (QuestArc docs/behaviour.md, screen 0a): the moment's
words and name (`nameAnchor`, written when editing ends: Enter, leaving
the field or going back; no Save button), and where it stands in the day:
the places in order, **Move Earlier** and **Move Later**, the side of the
path and the colour (the eight hues, each a swatch with its name), where
a thing stands **What grows** (the kind of every thing at the place,
also after it has grown; the version reached is kept) and, once a
ladder lists more than one marker kind, **What hangs**, **Use the
suggestion** (only while something was chosen; it also withdraws the
kind chosen when the first journey started), and **Remove This Moment**
where nothing stands. Each change of the place is written at
once, as the engine's `movePlace`, `choosePlaceSide`, `choosePlaceHue`
and `withdrawPlace` make it (`place:<anchorId>` records); the fields
above keep what was typed. Undo, not confirm: only removing a moment
offers Undo."""
import math

from gi.repository import Adw, Gtk

from pensum.game import content, moments, records
from pensum.game.content import t
from pensum.ui.journey import art
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.moment_rows import MAX_WORDS, MomentRows, limit


def swatch(hue):
    """A dot in the hue (light or dark as the style is). It only helps:
    the name beside it carries the information."""
    area = Gtk.DrawingArea(content_width=24, content_height=24, valign=Gtk.Align.CENTER,
                           accessible_role=Gtk.AccessibleRole.PRESENTATION)

    def draw(area, cr, width, height):
        colour = art.colours(area, False, hue)["accent"]
        cr.set_source_rgb(*colour)
        cr.arc(width / 2, height / 2, 10, 0, 2 * math.pi)
        cr.fill()

    area.set_draw_func(draw)
    return area


def _radio(group, title, active, on_pick, suffix=None):
    check = Gtk.CheckButton(active=active, group=group["first"], valign=Gtk.Align.CENTER)
    group["first"] = group["first"] or check
    row = Adw.ActionRow(title=title, activatable_widget=check)
    row.add_prefix(check)
    if suffix:
        row.add_suffix(suffix)
    # Connected after `active` is set, so drawing the page writes nothing.
    check.connect("toggled", lambda c: c.get_active() and on_pick())
    return row


class ChangeMomentPage(JourneySubpage):
    def __init__(self, window, anchor_id):
        super().__init__(window, t("ui.moment.change"), None)
        self.anchor_id = anchor_id
        view = self.model.view or {}
        anchor = moments.anchor(view, anchor_id) or {}
        when = self.group(t("ui.moment.when"), t("ui.moment.private"))
        self.rows = MomentRows(when, words=anchor.get("words", ""), time=anchor.get("time", ""))
        naming = self.group(t("ui.moment.name"), t("ui.moment.name.hint"))
        self.name_row = limit(Adw.EntryRow(title=t("ui.moment.name"),
                                           text=anchor.get("name", "")), MAX_WORDS)
        naming.add(self.name_row)
        self.text(t("ui.moment.tasks"), "dimmed", "caption")
        self.fixed = len(self._groups)
        self._saved = self._typed()
        for row in (self.rows.routine, self.rows.time, self.name_row):
            row.connect("entry-activated", lambda *_: self._commit())
            focus = Gtk.EventControllerFocus()
            focus.connect("leave", lambda *_: self._commit())
            row.add_controller(focus)
        # Going back writes what was typed last.
        self.connect("hiding", lambda *_: self._commit())
        self.listen(self._show)
        self._show()

    def _show(self):
        """The groups about the place; the fields above are left as typed."""
        for group in self._groups[self.fixed:]:
            self.page.remove(group)
        del self._groups[self.fixed:]
        view = self.model.view or {}
        places = view.get("valley", [])
        place = next((p for p in places if p["anchorId"] == self.anchor_id), None)
        if place is None:
            return
        self._order(places, place, view)
        self._side(place)
        self._colour(place)
        if place["things"]:
            self._kind(place)
            self._marker(place)
        self._more(place, view)

    def _act(self, name, *args):
        self.model.action(name, self.model.view, self.anchor_id, *args)

    def _order(self, places, place, view):
        group = self.group(t("ui.place.day"))
        for number, each in enumerate(places, start=1):
            here = each["anchorId"] == self.anchor_id
            row = Adw.ActionRow(title=f"{number}. {moments.place_title(view, each)}",
                                subtitle=t("ui.place.here") if here else "")
            if here:
                row.add_css_class("heading")
            group.add(row)
        index = places.index(place)
        for key, direction, enabled in (("ui.place.earlier", "earlier", index > 0),
                                        ("ui.place.later", "later", index < len(places) - 1)):
            row = Adw.ActionRow(title=t(key), activatable=enabled, sensitive=enabled)
            row.add_suffix(Gtk.Image(icon_name="go-up-symbolic" if direction == "earlier"
                                     else "go-down-symbolic"))
            row.connect("activated", lambda _r, d=direction: self._act("movePlace", d))
            group.add(row)

    def _side(self, place):
        group, first = self.group(t("ui.place.side")), {"first": None}
        for side in ("left", "right"):
            group.add(_radio(first, t(f"ui.place.side.{side}"), place["side"] == side,
                             lambda s=side: self._act("choosePlaceSide", s)))

    def _colour(self, place):
        group, first = self.group(t("ui.build.colour")), {"first": None}
        for hue, entry in content.palette().items():
            group.add(_radio(first, entry["title"], place["hue"] == hue,
                             lambda h=hue: self._act("choosePlaceHue", h), swatch(hue)))

    def _kind(self, place):
        """What grows: one option per ladder with its first version as a
        small picture; the journey's own is "Suggested by the journey"."""
        group, first = self.group(t("ui.build.thing"), t("ui.place.kind.keeps")), {"first": None}
        journey = content.journey(place["things"][0]["journeyId"]) or {}
        suggested = (journey.get("build") or {}).get("ladder")
        standing = place["things"][0]["ladder"]
        for name, ladder in content.ladders().items():
            row = _radio(first, ladder["title"], standing == name,
                         lambda n=name: self._act("choosePlaceKind", n),
                         art.picture_area(ladder["versions"][0]["art"], 60, card=True,
                                          hue=place["hue"], height=40, part=ladder.get("row")))
            if name == suggested:
                row.set_subtitle(t("ui.build.suggested"))
            group.add(row)

    def _marker(self, place):
        """What hangs: only where the place's kind draws more than one kind
        of marker (flowers are the only one now, so nothing is shown)."""
        kinds = (content.ladder(place["things"][0]["ladder"]) or {}).get("markers") or []
        if len(kinds) < 2:
            return
        group, first = self.group(t("ui.place.marker")), {"first": None}
        for index, kind in enumerate(kinds):
            group.add(_radio(first, t("ui.place.marker.default") if index == 0
                             else kind.capitalize(), place.get("marker", kinds[0]) == kind,
                             lambda k=None if index == 0 else kind:
                             self._act("choosePlaceMarker", k)))

    def _more(self, place, view):
        group = self.group()
        # What the user picked: the place's record, and the kind chosen
        # before the first journey's first version (`build:<run>`).
        first = place["things"][0]["runId"] if place["things"] else None
        picked = bool(place["chosen"]) or bool(
            first and (records.load(self.window.ds).get(f"build:{first}") or {}).get("ladder"))
        if picked:
            row = Adw.ButtonRow(title=t("ui.place.suggestion")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.place.suggestion"), activatable=True)
            row.connect("activated", lambda *_: self.model.action(
                "withdrawPlace", self.anchor_id, self.model.view))
            group.add(row)
        anchor = moments.anchor(view, self.anchor_id) or {}
        if not (place["things"] or place["unbuilt"] or anchor.get("growing")
                or anchor.get("resting") or anchor.get("steps")):
            self.text(t("ui.moment.remove.text"), "dimmed", "caption")
            row = Adw.ButtonRow(title=t("ui.moment.remove")) if hasattr(Adw, "ButtonRow") \
                else Adw.ActionRow(title=t("ui.moment.remove"), activatable=True)
            row.add_css_class("destructive-action")
            row.connect("activated", lambda *_: self._remove())
            group.add(row)

    def _typed(self):
        return (self.rows.anchor(), self.name_row.get_text().strip())

    def _commit(self):
        """Write the words, time and name when they changed. Without words
        or a time nothing is written and the fields go back to what stands."""
        typed = self._typed()
        if typed == self._saved:
            return
        anchor, name = typed
        if anchor is None:
            self.window.toast(t("ui.moment.missing"))
            current = moments.anchor(self.model.view or {}, self.anchor_id) or {}
            self.rows.routine.set_text(current.get("words", ""))
            self.rows.time.set_text(current.get("time", ""))
            return
        self._saved = typed
        self.model.action("nameAnchor", {"anchorId": self.anchor_id, "anchor": anchor,
                                         "name": name})

    def _remove(self):
        """Nothing stands here, so nothing is lost; Undo brings the records
        back."""
        self._saved = self._typed()  # going back must not write the moment again
        before = {key: value for key, value in records.load(self.window.ds).items()
                  if key in (f"anchor:{self.anchor_id}", f"place:{self.anchor_id}")}
        self.window.nav.pop()
        self.model.action("removeAnchor", self.model.view, self.anchor_id)
        toast = Adw.Toast(title="Moment removed", button_label=t("ui.action.undo"))
        toast.connect("button-clicked", lambda *_: self.model.write(before))
        self.window.toasts.add_toast(toast)
