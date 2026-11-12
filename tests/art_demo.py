"""The pictures' demo (QuestArc#86, #97, #42): a region at three moments,
a second region kind, every single picture at 48, 32 and 24 px and the
ladders (tests/ladder_demo.py), drawn by pensum/ui/journey/art.py in
libadwaita's colours. For screenshots; not part of the app. Needs
PENSUM_QUESTARC_DIR with content/art/ (docs/journeys.md); the argument
picks the part, `growth` (default), `shore`, `sizes`, `sequence-<ladder>`,
`journey-<ladder>` or `palette`; a second argument a palette hue:

    PENSUM_QUESTARC_DIR=../QuestArc /usr/bin/python3.12 tests/art_demo.py sequence-crossing slate
"""
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pensum.game import content  # noqa: E402
from pensum.ui.journey import art  # noqa: E402

import ladder_demo  # noqa: E402

GROWTH = [("meadow-started", "Just started"), ("meadow-half", "Half built"),
          ("meadow-finished", "Finished and graduated")]
SHORE = ("shore-finished", "Finished and graduated")
TITLES = {"growth": "A Meadow as It Grows", "shore": "Another Kind: a Shore",
          "sizes": "Pictures at 48, 32 and 24 px", "sequence": "One Thing, Whole at Every Step",
          "journey": "A Gentle Morning", "palette": "A Hue per Region"}


def scene_card(name, caption):
    scene = content.scene(name)
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["card"],
                   overflow=Gtk.Overflow.HIDDEN)
    if scene is None:
        card.append(Gtk.Label(label=f"No scene {name}"))
        return card
    card.append(art.scene_area(scene, card=True))
    card.append(Gtk.Label(label=caption, xalign=0, css_classes=["dimmed", "dim-label"],
                          margin_start=12, margin_end=12, margin_bottom=10))
    return card


def sizes_card():
    folder = content.directory() / "content" / "art"
    names = sorted(p.stem for p in folder.glob("*.svg") if not p.stem.startswith("ground-"))
    grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=2,
                       max_children_per_line=4, homogeneous=True, css_classes=["card"])
    for name in names:
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_start=6)
        row = Gtk.Box(spacing=8, valign=Gtk.Align.END)
        for size in (48, 32, 24):
            area = art.picture_area(name, size, card=True)
            area.set_valign(Gtk.Align.END)
            row.append(area)
        cell.append(row)
        cell.append(Gtk.Label(label=name, xalign=0, css_classes=["caption", "dimmed", "dim-label"]))
        grid.append(cell)
    return grid


def build(window, part, hue=None):
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                   margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
    clamp_size = 720
    if content.scene(GROWTH[0][0]) is None:
        page.append(Adw.StatusPage(title="No Pictures Installed",
                                   description="Set PENSUM_QUESTARC_DIR to a QuestArc with content/art."))
    elif part.startswith("sequence-"):
        clamp_size = 1400
        ladder_demo.sequence(page, part.removeprefix("sequence-"), hue)
    elif part.startswith("journey-"):
        ladder_demo.journey(page, part.removeprefix("journey-"), hue)
    elif part == "palette":
        clamp_size = 1400
        ladder_demo.palette(page)
    elif part == "shore":
        page.append(scene_card(*SHORE))
    elif part == "sizes":
        page.append(sizes_card())
    else:
        for name, caption in GROWTH:
            page.append(scene_card(name, caption))
    title = TITLES.get(part.split("-")[0], TITLES["growth"])
    clamp = Adw.Clamp(maximum_size=clamp_size, child=page)
    view = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=clamp, vexpand=True))
    view.add_top_bar(Adw.HeaderBar(title_widget=Adw.WindowTitle(title=title)))
    window.set_content(view)


def activate(app, part, hue):
    css = Gtk.CssProvider()
    css.load_from_path(str(Path(__file__).resolve().parents[1] / "pensum" / "style.css"))
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window = Adw.ApplicationWindow(application=app, default_width=360, default_height=720)
    window.set_size_request(360, 294)
    build(window, part, hue)
    window.present()


if __name__ == "__main__":
    app = Adw.Application(application_id="de.nexumia.Pensum.ArtDemo")
    app.connect("activate", activate, sys.argv[1] if len(sys.argv) > 1 else "growth",
                sys.argv[2] if len(sys.argv) > 2 else None)
    app.run([])
