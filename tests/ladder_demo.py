"""The ladders' pages of the pictures' demo (QuestArc#42), for the owner to
judge, the same as QuestArc's preview (packages/plugin/preview/ladders.ts):
`sequence-<ladder>` shows one ladder as it grows (each version, then the
scaffold while the next is worked on, the scaffold with the flag when it is
ready, the last version with the lit lantern, the row of versions), `journey-<ladder>` a static mock of the
journey screen with the build on top, `palette` every hue and each ladder
in two hues. Not part of the app; the real journey pages are unchanged."""
import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402

from pensum.game import content  # noqa: E402
from pensum.ui.journey import art  # noqa: E402


def _words(ladder, version, state):
    """The state in words, as under the row of versions."""
    versions = ladder["versions"]
    now = versions[version - 1]["title"]
    following = versions[version]["title"].lower() if version < len(versions) else ""
    stands = "stands" if now.startswith("A ") else "stand"
    if state == "extending":
        return f"{now} {stands} · work on {following} has begun"
    if state == "ready":
        return f"{now} {stands} · {following} is ready"
    return f"{now} {stands}"


def _frame(ladder, hue, version, state, lit, caption, width=310):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["card"],
                   overflow=Gtk.Overflow.HIDDEN, width_request=width, valign=Gtk.Align.START)
    card.append(art.scene_area(art.ladder_scene(ladder, version, state, lit), card=True, hue=hue))
    card.append(Gtk.Label(label=caption, xalign=0, wrap=True, css_classes=["dimmed", "dim-label"],
                          margin_start=12, margin_end=12, margin_bottom=10))
    return card


def _version_row(ladder, hue, standing, card=True):
    row = Gtk.Box(spacing=4, margin_start=8, margin_end=8, margin_top=8, margin_bottom=4)
    for i, version in enumerate(ladder["versions"][:standing]):
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cell.append(art.picture_area(version["art"], 60, card=card, hue=hue, height=40))
        cell.append(Gtk.Label(label=str(i + 1), css_classes=["caption", "dimmed", "dim-label"]))
        row.append(cell)
    if standing < len(ladder["versions"]):
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.END)
        cell.append(Gtk.Frame(width_request=56, height_request=36, margin_start=2, margin_end=2))
        cell.append(Gtk.Label(label=str(standing + 1), css_classes=["caption", "dimmed", "dim-label"]))
        row.append(cell)
    return row


def _flow(children, per_line=4):
    box = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=per_line,
                      homogeneous=True,
                      max_children_per_line=per_line, column_spacing=12, row_spacing=12,
                      valign=Gtk.Align.START)
    for child in children:
        box.append(child)
    return box


def _hue(ladder, name):
    return name if name in content.palette() else ladder["hue"]


def sequence(page, name, hue_name=None):
    ladder = content.ladder(name)
    if ladder is None:
        page.append(Gtk.Label(label=f"No ladder {name}"))
        return
    hue = _hue(ladder, hue_name)
    versions = ladder["versions"]
    frames = []
    for v in range(1, len(versions) + 1):
        frames.append(_frame(ladder, hue, v, "standing", False, f"{v} · {_words(ladder, v, 'standing')}"))
        if v < len(versions):
            for state in ("extending", "ready"):
                frames.append(_frame(ladder, hue, v, state, False, _words(ladder, v, state)))
    frames.append(_frame(ladder, hue, len(versions), "standing", True,
                         f"{len(versions)} · after graduation: the lantern lit"))
    row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["card"], width_request=310,
                  valign=Gtk.Align.START)
    row.append(_version_row(ladder, hue, len(versions)))
    row.append(Gtk.Label(label="The row of versions, 60 × 40 px", xalign=0,
                         css_classes=["dimmed", "dim-label"], margin_start=12, margin_bottom=10))
    frames.append(row)
    page.append(_flow(frames))


class _Day(Gtk.DrawingArea):
    def __init__(self, state):
        super().__init__(content_width=18, content_height=18)
        self.set_draw_func(self._draw, state)

    def _draw(self, area, cr, width, height, state):
        r, g, b = art.colours(area)["accent" if state != "off" else "fg"]
        cr.set_source_rgb(r, g, b)
        cr.arc(width / 2, height / 2, 8, 0, 2 * math.pi)
        if state == "on":
            cr.fill()
        else:
            cr.arc_negative(width / 2, height / 2, 6.5, 2 * math.pi, 0)
            cr.fill()


def journey(page, name, hue_name=None):
    ladder = content.ladder(name)
    if ladder is None:
        page.append(Gtk.Label(label=f"No ladder {name}"))
        return
    hue = _hue(ladder, hue_name)
    standing = 3
    page.set_margin_start(0)
    page.set_margin_end(0)
    page.set_margin_top(0)
    page.set_spacing(8)
    page.append(art.scene_area(art.ladder_scene(ladder, standing, "extending"), hue=hue))
    page.append(_version_row(ladder, hue, standing, card=False))
    page.append(Gtk.Label(
        label=_words(ladder, standing, "extending"),
        xalign=0, wrap=True, css_classes=["dimmed", "dim-label"], margin_start=16, margin_end=16))
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"],
                   margin_start=8, margin_end=8)
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=16, margin_end=16,
                    margin_top=14, margin_bottom=14)
    inner.append(Gtk.Label(label="STATION 3 OF 4", xalign=0, css_classes=["caption-heading", "dimmed",
                                                                           "dim-label"]))
    inner.append(Gtk.Label(label="After getting up, I will drink a glass of water and stretch for five "
                                 "minutes.", xalign=0, wrap=True, css_classes=["heading"]))
    inner.append(Gtk.ProgressBar(fraction=0.6))
    inner.append(Gtk.Label(label="3 of 5 days in the last 7 due days", xalign=0))
    days = Gtk.Box(homogeneous=True)
    for day, state in (("Fr", "off"), ("Sa", "on"), ("Su", "on"), ("Mo", "off"), ("Tu", "on"),
                       ("We", ""), ("Th", "")):
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        cell.append(_Day(state))
        cell.append(Gtk.Label(label=day, css_classes=["caption", "dimmed", "dim-label"]))
        days.append(cell)
    inner.append(days)
    card.append(inner)
    page.append(card)


def palette(page):
    swatches = []
    for name, entry in content.palette().items():
        cell = Gtk.Box(spacing=8)
        cell.append(art.picture_area("lantern", 28, card=True, hue=name))
        cell.append(Gtk.Label(label=f"{entry['title']} ({name})", xalign=0))
        swatches.append(cell)
    grid = _flow(swatches, per_line=4)
    grid.add_css_class("card")
    page.append(grid)
    frames = []
    for name, hues in (("crossing", ("water", "slate")), ("home", ("meadow", "rust"))):
        ladder = content.ladder(name)
        for hue in hues:
            frames.append(_frame(ladder, hue, 4, "ready", False,
                                 f"{ladder['title']} in {content.palette()[hue]['title'].lower()}"))
    page.append(_flow(frames))
