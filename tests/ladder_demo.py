"""The ladders' pages of the pictures' demo (QuestArc#42), for the owner to
judge, the same as QuestArc's preview (packages/plugin/preview/ladders.ts):
`sequence-<ladder>[-<marker>]` shows one ladder as it grows (each version,
then its marker growing element by element: every element for the first
stage, a few sampled steps for the others; ready; then the next version;
the last version with the lit lantern; the row of versions),
`journey-<ladder>[-ready]` a static mock of the journey screen with the
build on top (posts up and two elements hanging, or ready), `palette` every
hue and each ladder in two hues.
Not part of the app; the journey page draws the build with the same
functions (pensum/ui/journey/build.py)."""
import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk  # noqa: E402

from pensum.game import content  # noqa: E402
from pensum.ui.journey import art  # noqa: E402
from pensum.ui.journey.build import version_row  # noqa: E402


def _steps(ladder, version):
    """Every element for the first stage, a few sampled steps for the others."""
    every = art.marker_elements(ladder)
    posts = len(ladder["posts"])
    if version == 1:
        return list(range(1, every + 1))
    return [1, posts, posts + math.ceil((every - posts) / 2), every]


def _frame(ladder, hue, version, caption, width=300, **state):
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["card"],
                   overflow=Gtk.Overflow.HIDDEN, width_request=width, valign=Gtk.Align.START)
    card.append(art.scene_area(art.ladder_scene(ladder, version, **state), card=True, hue=hue))
    # A short natural width, so four cards fit on a line and wrap when narrower.
    card.append(Gtk.Label(label=caption, xalign=0, wrap=True, max_width_chars=30,
                          css_classes=["dimmed", "dim-label"],
                          margin_start=12, margin_end=12, margin_bottom=10))
    return card


def _flow(children, per_line=4):
    # At least one per line, so a narrow window wraps instead of overflowing.
    box = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=1,
                      homogeneous=True,
                      max_children_per_line=per_line, column_spacing=12, row_spacing=12,
                      valign=Gtk.Align.START)
    for child in children:
        box.append(child)
    return box


def _hue(ladder, name):
    return name if name in content.palette() else ladder["hue"]


def sequence(page, name, hue_name=None):
    ladder_name, _, kind = name.partition("-")
    ladder = content.ladder(ladder_name)
    if ladder is None:
        page.append(Gtk.Label(label=f"No ladder {name}"))
        return
    hue = _hue(ladder, hue_name)
    kind = kind or ladder["marker"]
    last = len(ladder["versions"])
    page.append(Gtk.Label(label=f"{ladder['title']} with {kind}", xalign=0,
                          css_classes=["title-4"]))
    frames = []
    for v in range(1, last + 1):
        frames.append(_frame(ladder, hue, v, f"{v} · {art.build_words(ladder, v)}"))
        if v < last:
            every = art.marker_elements(ladder)
            for shown in _steps(ladder, v):
                words = art.build_words(ladder, v, shown / every)
                frames.append(_frame(ladder, hue, v, f"{shown} of {every} · {words}",
                                     progress=shown / every, marker=kind))
            frames.append(_frame(ladder, hue, v, f"ready · {art.build_words(ladder, v, ready=True)}",
                                 ready=True, marker=kind))
    frames.append(_frame(ladder, hue, last, f"{last} · after graduation: the lantern lit",
                         graduated=True))
    row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, css_classes=["card"], width_request=300,
                  valign=Gtk.Align.START)
    inner = version_row(ladder, hue, last, card=True)
    for side in ("start", "end", "top"):
        getattr(inner, f"set_margin_{side}")(8)
    row.append(inner)
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
    ladder_name, _, flag = name.partition("-")
    ladder = content.ladder(ladder_name)
    if ladder is None:
        page.append(Gtk.Label(label=f"No ladder {name}"))
        return
    hue = _hue(ladder, hue_name)
    standing = 3
    lit = flag == "ready"
    midway = (len(ladder["posts"]) + 2) / art.marker_elements(ladder)
    page.set_margin_start(0)
    page.set_margin_end(0)
    page.set_margin_top(0)
    page.set_spacing(8)
    page.append(art.scene_area(art.ladder_scene(ladder, standing, midway, lit), hue=hue))
    versions = version_row(ladder, hue, standing)
    versions.set_margin_start(8)
    page.append(versions)
    page.append(Gtk.Label(
        label=art.build_words(ladder, standing, midway, lit),
        xalign=0, wrap=True, css_classes=["dimmed", "dim-label"], margin_start=16, margin_end=16))
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"],
                   margin_start=8, margin_end=8)
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=16, margin_end=16,
                    margin_top=14, margin_bottom=14)
    inner.append(Gtk.Label(label="STATION 3 OF 4", xalign=0, css_classes=["caption-heading", "dimmed",
                                                                           "dim-label"]))
    inner.append(Gtk.Label(label="After getting up, I will drink a glass of water and stretch for five "
                                 "minutes.", xalign=0, wrap=True, css_classes=["heading"]))
    inner.append(Gtk.ProgressBar(fraction=1.0 if lit else 0.6))
    inner.append(Gtk.Label(label=f"{5 if lit else 3} of 5 days in the last 7 due days", xalign=0))
    days = Gtk.Box(homogeneous=True)
    for day, state in (("Fr", "on" if lit else "off"), ("Sa", "on"), ("Su", "on"), ("Mo", "off"),
                       ("Tu", "on"), ("We", "on" if lit else ""), ("Th", "")):
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
            frames.append(_frame(ladder, hue, 4,
                                 f"{ladder['title']} in {content.palette()[hue]['title'].lower()}",
                                 ready=True))
    page.append(_flow(frames))
