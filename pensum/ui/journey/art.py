"""QuestArc's pictures (content/art/, QuestArc decision "shared pictures")
drawn with librsvg into Cairo. A picture has no colours of its own: its
shapes carry the roles in ROLES, which a stylesheet fills from
libadwaita's colours, so light and dark follow the system: fg the text
colour, accent as libadwaita's `.accent` class shows it (the app's own
accent, made readable on dark surfaces since libadwaita 1.6), dim the
text colour mixed into the surface the picture stands on, bg that
surface, tint and tint-strong the accent mixed into it, as in the
plugin. Every role is opaque, so overlaps show no seams. A scene's far
band is drawn as one silhouette in tint.
Every picture and scene has its title as the accessible label."""
import html
import re
import warnings
from functools import lru_cache

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Rsvg", "2.0")
from gi.repository import GLib, Gtk, Rsvg  # noqa: E402

from pensum.game import content  # noqa: E402

ROLES = ("fg", "accent", "dim", "bg", "tint", "tint-strong")
DIM = 0.3  # share of the text colour in dim
TINT = 0.16  # share of the accent in tint
TINT_STRONG = 0.4  # share of the accent in tint-strong
_TITLE = re.compile(r"<title>(.*?)</title>", re.S)


def _named(widget, name):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        found, color = widget.get_style_context().lookup_color(name)
    return (color.red, color.green, color.blue, color.alpha) if found else None


def _over(top, below):
    """`top` (r, g, b, a) composited over the opaque colour `below`."""
    r, g, b, a = top
    return tuple(c * a + d * (1 - a) for c, d in zip((r, g, b), below[:3]))


def surface(widget, card=False):
    """The opaque colour behind a picture: the window, or a card on it."""
    window = _named(widget, "window_bg_color")
    fg = widget.get_color()
    if window is None:  # no named colours: guess from the text colour
        light = fg.red + fg.green + fg.blue < 1.5
        window = (0.98, 0.98, 0.98, 1) if light else (0.14, 0.14, 0.15, 1)
    base = window[:3]
    card_bg = _named(widget, "card_bg_color") if card else None
    return _over(card_bg, base) if card_bg else base


def _mix(top, below, share):
    return tuple(t * share + b * (1 - share) for t, b in zip(top, below))


def colours(widget, card=False):
    """The roles as opaque (r, g, b) for the widget's style."""
    below = surface(widget, card)
    fg = widget.get_color()
    acc = Gtk.Label(css_classes=["accent"]).get_color()
    text = _over((fg.red, fg.green, fg.blue, fg.alpha), below)
    accent = _over((acc.red, acc.green, acc.blue, acc.alpha), below)
    return {
        "fg": text,
        "accent": accent,
        "dim": _mix(text, below, DIM),
        "bg": tuple(below),
        "tint": _mix(accent, below, TINT),
        "tint-strong": _mix(accent, below, TINT_STRONG),
    }


def stylesheet(roles):
    hexes = {k: "#%02x%02x%02x" % tuple(round(c * 255) for c in v) for k, v in roles.items()}
    return "".join(f".{k}{{fill:{v}}}" for k, v in sorted(hexes.items()))


def far_stylesheet(roles):
    """The far band: every role in tint, one silhouette with the ground."""
    return stylesheet({k: roles["tint"] for k in roles})


@lru_cache(maxsize=128)
def _handle(path, css):
    handle = Rsvg.Handle.new_from_file(str(path))
    handle.set_stylesheet(css.encode())
    return handle


def title(name):
    path = content.art_path(name)
    if path is None:
        return ""
    found = _TITLE.search(path.read_text(encoding="utf-8"))
    return html.unescape(found.group(1).strip()) if found else ""


def draw(cr, name, x, y, width, height, css):
    """One picture into the rectangle; nothing if it is not installed."""
    path = content.art_path(name)
    if path is None:
        return False
    rect = Rsvg.Rectangle()
    rect.x, rect.y, rect.width, rect.height = x, y, width, height
    _handle(path, css).render_document(cr, rect)
    return True


def draw_scene(cr, scene, width, height, roles):
    """A scene scaled to fit, centred and clipped to its own size, in the
    roles' colours; the far band as one silhouette in tint."""
    scale = min(width / scene["width"], height / scene["height"])
    css, far = stylesheet(roles), far_stylesheet(roles)
    cr.save()
    cr.translate((width - scene["width"] * scale) / 2, (height - scene["height"] * scale) / 2)
    cr.scale(scale, scale)
    cr.rectangle(0, 0, scene["width"], scene["height"])
    cr.clip()
    for p in scene["pictures"]:
        draw(cr, p["art"], p["x"], p["y"], p["width"], p["height"],
             far if p.get("band") == "far" else css)
    cr.restore()


def _area(label, draw_func, card):
    area = Gtk.DrawingArea(accessible_role=Gtk.AccessibleRole.IMG)
    area.update_property([Gtk.AccessibleProperty.LABEL], [label])

    def on_draw(area, cr, width, height):
        draw_func(cr, width, height, colours(area, card))

    area.set_draw_func(on_draw)
    return area


def picture_area(name, size, card=False):
    """A picture as a widget of size × size px."""
    area = _area(title(name), lambda cr, w, h, roles: draw(cr, name, 0, 0, w, h, stylesheet(roles)), card)
    area.set_content_width(size)
    area.set_content_height(size)
    return area


def scene_area(scene, card=False):
    """A scene as a widget as wide as its parent, its height following the
    width in the scene's proportions."""
    area = _area(scene["title"], lambda cr, w, h, roles: draw_scene(cr, scene, w, h, roles), card)
    area.set_hexpand(True)
    area.set_content_height(scene["height"])

    def on_resize(area, width, _height):
        wanted = round(width * scene["height"] / scene["width"])
        if wanted != area.get_content_height():
            # Not during the allocation itself: GTK drops a resize queued there.
            GLib.idle_add(area.set_content_height, wanted)

    area.connect("resize", on_resize)
    return area
