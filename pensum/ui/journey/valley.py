"""The Valley (QuestArc docs/behaviour.md, screens 0 and 0b): one path
through the day with a place for every moment, drawn from the engine's
`valley` view and the layout the engine computes (`engine.valley_layout`);
nothing is placed by hand here. Back to front: ground, path and bays,
the things (the second and third behind the first), the flowers of the
growing thing, the lantern, the names. The pictures are QuestArc's, drawn
by `art.py` in libadwaita's colours and each place's hue. Every place is
one button over the picture, named in words for screen readers."""
import math

import cairo

import gi

gi.require_version("PangoCairo", "1.0")
from gi.repository import Adw, GLib, Gtk, Pango, PangoCairo  # noqa: E402

from pensum.game import content  # noqa: E402
from pensum.game.content import t  # noqa: E402
from pensum.ui.journey import art  # noqa: E402

MAX_WIDTH = 440  # the scene is as wide as the page up to this many pixels


def _ladder_art(thing):
    """The picture of the version that stands (the last for versions
    past it), or None where the ladder is not here."""
    ladder = content.ladder(thing["ladder"])
    if not ladder:
        return None
    versions = ladder["versions"]
    return versions[min(max(thing["version"], 1), len(versions)) - 1]["art"]


def flowers(thing):
    """The pictures of the flowers in front of a growing thing (QuestArc
    #152): the first ceil(p × E) in bud, all of them open while the stage
    is met; none after the last version."""
    ladder = content.ladder(thing["ladder"])
    if not ladder or thing["version"] >= thing["versions"]:
        return []
    scene = art.ladder_scene(ladder, thing["version"], thing.get("markerProgress", 0),
                             bool(thing.get("ready")), thing["versions"])
    return [p["art"] for p in scene["pictures"] if p.get("slot") == "marker"]


def place_label(place, title, journeys_title=None):
    """The place in words for screen readers: name, thing and version,
    the growing step and the sign (QuestArc `ui.valley.*`)."""
    things = place["things"]
    ladder = content.ladder(things[0]["ladder"]) if things else None
    if ladder:
        thing = things[0]
        version = ladder["versions"][min(max(thing["version"], 1), len(ladder["versions"])) - 1]
        parts = [t("ui.valley.place", name=title, thing=version["title"],
                   version=thing["version"], total=thing["versions"])]
    else:
        parts = [t("ui.valley.place.free", name=title)]
    if place["growing"]:
        parts.append(t("ui.valley.growing"))
    if place.get("sign"):
        parts.append(t(f"ui.valley.sign.{place['sign']}"))
    return " ".join(parts)


class _Picture(Gtk.DrawingArea):
    """The drawing: as wide as its parent, its height following the width
    in the layout's proportions."""

    def __init__(self, layout, draw):
        super().__init__(hexpand=True, accessible_role=Gtk.AccessibleRole.PRESENTATION,
                         content_height=layout["height"])
        self.layout = layout
        self.set_draw_func(draw)
        self.connect("resize", self._on_resize)

    def _on_resize(self, _area, width, _height):
        wanted = round(width * self.layout["height"] / self.layout["width"])
        if wanted != self.get_content_height():
            # Not during the allocation itself: GTK drops a resize queued there.
            GLib.idle_add(self.set_content_height, wanted)


class ValleyScene(Gtk.Overlay):
    """`places`: the engine's valley places, in the order of the day;
    `titles`: their names; `layout`: the engine's geometry for them;
    `on_open(i)`: called with the place's index when it is tapped, or
    None for a plain picture (the place's own page); `edit(i)` adds a
    pencil on place i's free side (the page of one place)."""

    def __init__(self, places, titles, layout, on_open=None, growing_flowers=False,
                 growth=None):
        super().__init__(css_classes=["pensum-valley", "card"], overflow=Gtk.Overflow.HIDDEN)
        self.places, self.titles, self.layout = places, titles, layout
        self.flowers = growing_flowers
        # The moment of the tick (`tick.Growth`): new flowers grow in.
        self.growth = growth
        self.picture = _Picture(layout, self._draw)
        if growth:
            growth.attach(self.picture)
        self.set_child(self.picture)
        self.labels = [place_label(p, ti) for p, ti in zip(places, titles)]
        label = t("ui.valley.label")
        self.update_property([Gtk.AccessibleProperty.LABEL], [label])
        self.taps = Gtk.Fixed()
        self.add_overlay(self.taps)
        self.set_measure_overlay(self.taps, False)
        self.buttons = []
        if on_open:
            for i, text in enumerate(self.labels):
                button = Gtk.Button(css_classes=["flat", "pensum-valley-tap"])
                button.update_property([Gtk.AccessibleProperty.LABEL], [text])
                button.set_tooltip_text(self.titles[i])
                button.connect("clicked", lambda _b, n=i: on_open(n))
                self.taps.put(button, 0, 0)
                self.buttons.append(button)
        self.picture.connect("resize", self._place_taps)

    def _place_taps(self, _area, width, height):
        scale = width / self.layout["width"]
        for piece, button in zip(self.layout["places"], self.buttons):
            band = piece["piece"]
            button.set_size_request(width, max(44, round(band["height"] * scale)))
            self.taps.move(button, 0, round(band["y"] * scale))

    # --- drawing -----------------------------------------------------------

    def _roles(self, widget, cache, hue):
        if hue not in cache:
            cache[hue] = art.colours(widget, True, hue)
        return cache[hue]

    def _draw(self, area, cr, width, height):
        if width <= 0 or height <= 0:
            return  # not laid out yet; a zero scale is an invalid matrix
        layout, scale = self.layout, width / self.layout["width"]
        dark = Adw.StyleManager.get_default().get_dark()
        cache = {}
        plain = self._roles(area, cache, None)
        pieces = list(zip(self.places, self.layout["places"], self.titles))
        cr.save()
        cr.scale(scale, scale)
        self._ground(cr, pieces, plain, cache, area)
        self._way(cr, pieces, plain, cache, area, dark)
        for place, piece, _title in pieces:
            roles = self._roles(area, cache, place["hue"])
            self._things(cr, place, piece, roles)
        cr.restore()
        for place, piece, title in pieces:
            self._name(area, cr, scale, place, piece, title, self._roles(area, cache, None))

    @staticmethod
    def _gradient(cr, height, stops, flat):
        if not stops:
            cr.set_source_rgb(*flat)
            return
        gradient = cairo.LinearGradient(0, 0, 0, height)
        for at, colour in stops:
            gradient.add_color_stop_rgb(min(max(at / height, 0.0), 1.0), *colour)
        cr.set_source(gradient)

    def _ground(self, cr, pieces, plain, cache, area):
        stops = []
        for place, piece, _title in pieces:
            band = piece["piece"]
            tint = self._roles(area, cache, place["hue"])["tint"]
            stops += [(band["y"] + band["height"] * 0.3, tint),
                      (band["y"] + band["height"] * 0.7, tint)]
        self._gradient(cr, self.layout["height"], stops, plain["bg"])
        cr.rectangle(0, 0, self.layout["width"], self.layout["height"])
        cr.fill()

    def _way(self, cr, pieces, plain, cache, area, dark):
        """Path and bays in one colour, so a bay reads as the path
        widening: the surface in the light style, the hue's tint-strong
        in the dark one (so the path is not a hole in the tinted ground)."""
        def way(place):
            roles = self._roles(area, cache, place["hue"])
            return roles["tint-strong"] if dark else roles["bg"]
        stops = []
        for place, piece, _title in pieces:
            band = piece["piece"]
            stops += [(band["y"] + band["height"] * 0.2, way(place)),
                      (band["y"] + band["height"] * 0.8, way(place))]
        self._gradient(cr, self.layout["height"], stops, plain["bg"])
        cr.set_line_width(self.layout["pathWidth"])
        path = self.layout["path"]
        if path:
            cr.move_to(path[0]["from"]["x"], path[0]["from"]["y"])
            for seg in path:
                cr.curve_to(seg["c1"]["x"], seg["c1"]["y"], seg["c2"]["x"], seg["c2"]["y"],
                            seg["to"]["x"], seg["to"]["y"])
            cr.stroke()
        for place, piece, _title in pieces:
            cr.set_source_rgb(*way(place))
            for ground in [piece["bay"], *piece.get("patches", [])]:
                cr.save()
                cr.translate(ground["cx"], ground["cy"])
                cr.scale(ground["rx"], ground["ry"])
                cr.arc(0, 0, 1, 0, 2 * math.pi)
                cr.restore()
                cr.fill()

    def _things(self, cr, place, piece, roles):
        css = art.stylesheet(roles) + "svg{overflow:visible}"
        for thing, box in reversed(list(zip(place["things"], piece["things"]))):
            name = _ladder_art(thing)
            if name:
                art.draw(cr, name, box["x"], box["y"], box["width"], box["height"], css)
        if self.flowers and place["things"]:
            grows = next((th for th in place["things"] if th["state"] == "growing"), None)
            if grows:
                box = piece["things"][place["things"].index(grows)]
                for index, name in enumerate(flowers(grows)):
                    art.draw_growing(cr, name, box["x"], box["y"], box["width"], box["height"],
                                     css, self.growth.factor(index) if self.growth else 1.0)
        if place.get("sign") == "lantern":
            slot = piece["slot"]
            art.draw(cr, f"place-lantern-{piece['side']}", slot["x"], slot["y"],
                     slot["width"], slot["height"], css)

    def _name(self, area, cr, scale, place, piece, title, roles):
        box = piece["name"]
        font = area.get_pango_context().get_font_description().copy()
        font.set_absolute_size(box["size"] * scale * Pango.SCALE)
        font.set_weight(Pango.Weight.BOLD if place["growing"] else Pango.Weight.NORMAL)
        text = PangoCairo.create_layout(cr)
        text.set_font_description(font)
        text.set_text(title, -1)
        text.set_width(round(box["width"] * scale * Pango.SCALE))
        text.set_height(-2)  # two lines, then an ellipsis
        text.set_ellipsize(Pango.EllipsizeMode.END)
        text.set_wrap(Pango.WrapMode.WORD_CHAR)
        text.set_spacing(round((box["lineHeight"] - box["size"]) * scale * Pango.SCALE))
        used_w, used_h = text.get_pixel_size()
        x = box["x"] * scale
        if box["align"] == "right":
            x += box["width"] * scale - used_w
        y = (box["y"] + box["height"] / 2) * scale - used_h / 2
        cr.set_source_rgb(*roles["fg"])
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, text)
