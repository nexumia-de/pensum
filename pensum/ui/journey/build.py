"""The build of a journey in the game (QuestArc docs/behaviour.md,
screen 4): the ladder's standing version in its setting with the flowers
of the stage under way, the row of the versions that stand (nothing of
what comes next) and one line of state in words. Everything comes from
the engine's `build` view; nothing is counted here."""
from gi.repository import Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.ui.journey import art

DIM = ["caption", "dimmed", "dim-label"]


def version_row(ladder, hue, standing, card=False, skipped=()):
    """The versions that stand as small pictures with their number; a
    version that stands for a skipped stage says "already yours" under
    its number (QuestArc behaviour, screen 4)."""
    row = Gtk.Box(spacing=4)
    for number, version in enumerate(ladder["versions"][:standing], start=1):
        cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        cell.append(art.picture_area(version["art"], 60, card=card, hue=hue, height=40,
                                     part=ladder.get("row")))
        cell.append(Gtk.Label(label=str(number), css_classes=DIM))
        if number in skipped:
            cell.append(Gtk.Label(label=t("ui.build.given"), css_classes=DIM, wrap=True,
                                  max_width_chars=8, justify=Gtk.Justification.CENTER))
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
    total = build.get("versions")
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    scene = art.ladder_scene(ladder, version, progress, ready, total)
    frame = Gtk.Box(css_classes=["card"], overflow=Gtk.Overflow.HIDDEN)
    frame.append(art.scene_area(scene, card=True, hue=hue))
    box.append(frame)
    row = version_row(ladder, hue, version, card=False, skipped=build.get("skipped") or ())
    row.set_margin_start(4)
    box.append(row)
    words = Gtk.Label(label=art.build_words(ladder, version), xalign=0,
                      wrap=True, css_classes=["dimmed", "dim-label"], margin_start=4)
    box.append(words)
    return box
