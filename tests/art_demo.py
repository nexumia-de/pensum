"""The picture spike's demo (QuestArc#86): QuestArc's test scene and every
single picture from content/art/, drawn by pensum/ui/journey/art.py in
libadwaita's colours. For screenshots; not part of the app. Needs
PENSUM_QUESTARC_DIR with content/art/ (docs/journeys.md):

    PENSUM_QUESTARC_DIR=../QuestArc /usr/bin/python3.12 tests/art_demo.py
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

SCENE = "spike-region"


def build(window):
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                   margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
    scene = content.scene(SCENE)
    if scene is None:
        page.append(Adw.StatusPage(title="No Pictures Installed",
                                   description="Set PENSUM_QUESTARC_DIR to a QuestArc with content/art."))
    else:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"])
        card.append(art.scene_area(scene, card=True))
        text = Gtk.Label(label=scene["title"], wrap=True, xalign=0,
                         css_classes=["dimmed", "dim-label"], margin_start=12,
                         margin_end=12, margin_bottom=12)
        card.append(text)
        page.append(card)
        folder = content.directory() / "content" / "art"
        names = sorted(p.stem for p in folder.glob("*.svg") if not p.stem.startswith("ground-"))
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, min_children_per_line=3,
                           max_children_per_line=8, homogeneous=True, css_classes=["card"])
        for name in names:
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                           margin_top=8, margin_bottom=8)
            cell.append(art.picture_area(name, 48, card=True))
            cell.append(Gtk.Label(label=name, css_classes=["caption"], wrap=True))
            grid.append(cell)
        page.append(grid)
        small = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=12,
                            css_classes=["card"])
        for name in names:
            small.append(art.picture_area(name, 24, card=True))
        page.append(small)
    clamp = Adw.Clamp(maximum_size=720, child=page)
    view = Adw.ToolbarView(content=Gtk.ScrolledWindow(child=clamp, vexpand=True))
    view.add_top_bar(Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Pictures")))
    window.set_content(view)


def activate(app):
    css = Gtk.CssProvider()
    css.load_from_path(str(Path(__file__).resolve().parents[1] / "pensum" / "style.css"))
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window = Adw.ApplicationWindow(application=app, default_width=360, default_height=720)
    window.set_size_request(360, 294)
    build(window)
    window.present()


if __name__ == "__main__":
    app = Adw.Application(application_id="de.nexumia.Pensum.ArtDemo")
    app.connect("activate", activate)
    app.run([])
