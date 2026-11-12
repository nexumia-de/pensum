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
A scene of a region may take its hue from QuestArc's palette
(content/art/palette.json): then accent, tint and tint-strong come from
the hue's light or dark value, fg, bg and dim stay libadwaita's. A
ladder's scene (a build; in front of it, while a stage runs, a festive
marker that grows one element at a time and is "on" while the stage is
met; the lantern after graduation) is composed by ladder_scene from the
ladder file's places.
Every picture and scene has its title as the accessible label."""
import html
import math
import re
import warnings
from functools import lru_cache

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Rsvg", "2.0")
from gi.repository import Adw, GLib, Gtk, Rsvg  # noqa: E402

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


def hex_rgb(value):
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def with_hue(roles, colour):
    """The roles with accent, tint and tint-strong from a palette colour."""
    below = roles["bg"]
    return dict(roles, accent=tuple(colour), tint=_mix(colour, below, TINT),
                **{"tint-strong": _mix(colour, below, TINT_STRONG)})


def hue_colour(hue, dark):
    """A palette hue's value for the style as (r, g, b), or None."""
    entry = content.palette().get(hue or "")
    return hex_rgb(entry["dark" if dark else "light"]) if entry else None


def colours(widget, card=False, hue=None):
    """The roles as opaque (r, g, b) for the widget's style; with a hue
    from the palette for accent, tint and tint-strong."""
    roles = _host_colours(widget, card)
    colour = hue_colour(hue, Adw.StyleManager.get_default().get_dark())
    return with_hue(roles, colour) if colour else roles


def _host_colours(widget, card):
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


def build_words(ladder, version, progress=0, ready=False):
    """The state in words, as under the row of versions: "A plank bridge
    stands · a stone bridge is on its way" while the stage runs, "… is
    ready" while it is met; never a count, never a building site."""
    versions = ladder["versions"]
    now = versions[min(max(version, 1), len(versions)) - 1]["title"]
    stands = "stands" if now.startswith("A ") else "stand"
    if version >= len(versions) or (not ready and progress <= 0):
        return f"{now} {stands}"
    following = versions[version]["title"].lower()
    return f"{now} {stands} · {following} {'is ready' if ready else 'is on its way'}"


def marker_elements(ladder):
    """E: how many elements the ladder's marker has (posts, then hanging ones)."""
    return max((p["order"] for p in ladder["pictures"] if p.get("slot") == "marker"), default=0)


def elements_shown(ladder, progress):
    """How many elements stand at `progress` (0…1): the first ceil(p × E)."""
    return max(0, math.ceil(min(max(progress, 0.0), 1.0) * marker_elements(ladder) - 1e-9))


def ladder_scene(ladder, version, progress=0, ready=False, marker=None, graduated=False):
    """The scene of a ladder (`<name>.ladder.json`) with `version` (from 1)
    standing. While a stage runs its marker grows in the foreground one
    element at a time, plain posts first, then the hanging elements: the first
    ceil(p × E) of them, `progress` p the best progress reached in the stage,
    so it never loses one; a line shows once both its posts stand. `ready`
    while the stage's condition is met now: every element stands in its
    "on" form (the posts stay plain). `marker` is a kind of markers.json, the ladder's default if
    None. After the last version there is no marker; `graduated` adds the
    lantern (QuestArc's journey design, "Builds and ladders")."""
    versions = ladder["versions"]
    standing = versions[min(max(version, 1), len(versions)) - 1]
    last = version >= len(versions)
    ready = ready and not last
    shown = 0 if last else marker_elements(ladder) if ready else elements_shown(ladder, progress)
    kind = marker or ladder["marker"]
    title = build_words(ladder, version, 0 if last else progress, ready).replace(" · ", ", ")
    if graduated:
        title += ", the lantern lit"
    pictures = []
    for place in ladder["pictures"]:
        slot = place.get("slot")
        if slot is None:
            pictures.append(place)
        elif slot == "build":
            pictures.append(dict(place, art=standing["art"]))
        elif slot == "lantern" and graduated:
            pictures.append(dict(place, art="lantern"))
        elif slot == "marker" and place["order"] <= shown:
            lit = "-lit" if ready and place["part"] == "bead" else ""
            name = place["art"] if place["part"] == "cord" else \
                f"marker-{kind}-{place['part']}{lit}"
            pictures.append(dict(place, art=name))
    return {"title": title, "width": ladder["width"], "height": ladder["height"],
            "pictures": pictures}


def _area(label, draw_func, card, hue=None):
    area = Gtk.DrawingArea(accessible_role=Gtk.AccessibleRole.IMG)
    area.update_property([Gtk.AccessibleProperty.LABEL], [label])

    def on_draw(area, cr, width, height):
        draw_func(cr, width, height, colours(area, card, hue))

    area.set_draw_func(on_draw)
    return area


def draw_part(cr, name, width, height, part, css, box=(120, 80)):
    """The part [x, y, w, h] of a picture whose view box is `box`, zoomed to
    fill width × height (the row of versions of a ladder with `row`)."""
    x, y, w, h = part
    scale = min(width / w, height / h)
    cr.save()
    cr.rectangle(0, 0, width, height)
    cr.clip()
    found = draw(cr, name, -x * scale, -y * scale, box[0] * scale, box[1] * scale, css)
    cr.restore()
    return found


def picture_area(name, size, card=False, hue=None, height=None, part=None):
    """A picture as a widget of size × size px (or size × height); with
    `part`, only that part of a build ([x, y, w, h], view box 120 × 80)."""
    def paint(cr, w, h, roles):
        if part:
            draw_part(cr, name, w, h, part, stylesheet(roles))
        else:
            draw(cr, name, 0, 0, w, h, stylesheet(roles))
    area = _area(title(name), paint, card, hue)
    area.set_content_width(size)
    area.set_content_height(height or size)
    return area


def scene_area(scene, card=False, hue=None):
    """A scene as a widget as wide as its parent, its height following the
    width in the scene's proportions."""
    area = _area(scene["title"], lambda cr, w, h, roles: draw_scene(cr, scene, w, h, roles), card,
                 hue)
    area.set_hexpand(True)
    area.set_content_height(scene["height"])

    def on_resize(area, width, _height):
        wanted = round(width * scene["height"] / scene["width"])
        if wanted != area.get_content_height():
            # Not during the allocation itself: GTK drops a resize queued there.
            GLib.idle_add(area.set_content_height, wanted)

    area.connect("resize", on_resize)
    return area
