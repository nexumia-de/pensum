"""One place, large (QuestArc docs/behaviour.md, screen 0b and 4): the
Valley's layout for a single place, 230 units high, with the flowers of
the growing thing and a pencil on the free side of the path that opens
"Change this moment"; under it the versions that stand and their words,
once for each thing. Used by the place's page and by the journey's page,
which is set in the same piece."""
from gi.repository import Adw, Gtk

from pensum.game import content, engine, moments
from pensum.game.content import t
from pensum.ui.journey.build import version_row
from pensum.ui.journey import art
from pensum.ui.journey.valley import MAX_WIDTH, ValleyScene

HEIGHT = 230
_layouts = {}


def place_of_run(view, run_id):
    """The place that holds a run's thing, or None (a run without a moment)."""
    return next((p for p in view.get("valley", [])
                 if any(th["runId"] == run_id for th in p["things"])), None)


def layout_for(place):
    key = (place["side"], len(place["things"]) or 1)
    if key not in _layouts:
        _layouts[key] = engine.valley_layout([key[0]], [key[1]], 360, HEIGHT)
    return _layouts[key]


def piece(window, view, place):
    """The piece as a picture with its pencil; it is not a button (the
    page around it is the place), but it is named in words."""
    title = moments.place_title(view, place)
    scene = ValleyScene([place], [title], layout_for(place), growing_flowers=True)
    overlay = Gtk.Overlay(child=scene)
    if place.get("anchorId"):
        free = Gtk.Align.START if place["side"] == "right" else Gtk.Align.END
        pencil = Gtk.Button(icon_name="document-edit-symbolic", halign=free, valign=Gtk.Align.START,
                            margin_top=4, margin_start=4, margin_end=4, width_request=44,
                            height_request=44, css_classes=["circular", "pensum-place-edit"],
                            tooltip_text=t("ui.moment.change"))
        pencil.update_property([Gtk.AccessibleProperty.LABEL], [t("ui.moment.change")])
        pencil.connect("clicked", lambda *_: _change(window, place["anchorId"]))
        overlay.add_overlay(pencil)
    return overlay


def _change(window, anchor_id):
    from pensum.ui.journey.change_moment_page import ChangeMomentPage
    window.nav.push(ChangeMomentPage(window, anchor_id))


def things(place, run_id=None):
    """Per thing: its journey's title where the place holds more than one,
    the versions that stand as small pictures and the words, e.g. "A well
    sweep stands". With `run_id` only that journey's thing (its own page)."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_start=4)
    shown = [th for th in place["things"] if run_id is None or th["runId"] == run_id]
    for thing in shown:
        ladder = content.ladder(thing["ladder"])
        if not ladder:
            continue
        journey = content.journey(thing["journeyId"])
        if run_id is None and len(place["things"]) > 1 and journey:
            box.append(Gtk.Label(label=t(journey["title"]), xalign=0, wrap=True,
                                 css_classes=["caption", "dimmed"]))
        standing = max(1, min(thing["version"], len(ladder["versions"])))
        box.append(version_row(ladder, place["hue"], standing, card=False,
                               skipped=thing.get("skipped") or ()))
        words = art.build_words(ladder, standing)
        box.append(Gtk.Label(label=words, xalign=0, wrap=True,
                             css_classes=["dimmed", "dim-label"]))
    return box


def section(window, view, place, run_id=None):
    """The piece, then the versions that stand."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    box.append(Adw.Clamp(child=piece(window, view, place), maximum_size=MAX_WIDTH))
    box.append(things(place, run_id))
    return box
