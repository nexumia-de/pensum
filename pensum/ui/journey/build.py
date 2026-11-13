"""The build of a journey in the game (QuestArc docs/behaviour.md,
screen 4): the ladder's standing version in its setting with the marker
of the stage under way, the row of versions that stand (the next one a
plain step without a picture, nothing further) and one line of state in
words. Everything comes from the engine's `build` view; nothing is
counted here."""
from gi.repository import Gtk

from pensum.game import content
from pensum.ui.journey import art

DIM = ["caption", "dimmed", "dim-label"]


def version_row(ladder, hue, standing, total=None, card=False):
    """The versions that stand as small pictures with their number, then
    the next one as an empty frame; `total` is how many this journey uses."""
    total = min(total or len(ladder["versions"]), len(ladder["versions"]))
    row = Gtk.Box(spacing=4)
    for number, version in enumerate(ladder["versions"][:standing], start=1):
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cell.append(art.picture_area(version["art"], 60, card=card, hue=hue, height=40,
                                     part=ladder.get("row")))
        cell.append(Gtk.Label(label=str(number), css_classes=DIM))
        row.append(cell)
    if standing < total:
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.END)
        cell.append(Gtk.Frame(width_request=56, height_request=36, margin_start=2, margin_end=2))
        cell.append(Gtk.Label(label=str(standing + 1), css_classes=DIM))
        row.append(cell)
    return row


def build_header(build):
    """The build, its row of versions and its state in words, or None when
    there is no build to draw (an engine without builds, a
    ladder whose pictures are not here)."""
    ladder = content.ladder((build or {}).get("ladder"))
    if ladder is None:
        return None
    hue = build["hue"] if build.get("hue") in content.palette() else ladder["hue"]
    version = max(1, min(build["version"], len(ladder["versions"])))
    progress, ready = build.get("markerProgress", 0), bool(build.get("ready"))
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scene = art.ladder_scene(ladder, version, progress, ready, build.get("marker"))
    frame = Gtk.Box(css_classes=["card"], overflow=Gtk.Overflow.HIDDEN)
    frame.append(art.scene_area(scene, card=True, hue=hue))
    box.append(frame)
    row = version_row(ladder, hue, version, build.get("versions"))
    row.set_margin_start(4)
    box.append(row)
    words = Gtk.Label(label=art.build_words(ladder, version, progress, ready), xalign=0,
                      wrap=True, css_classes=["dimmed", "dim-label"], margin_start=4)
    box.append(words)
    return box
