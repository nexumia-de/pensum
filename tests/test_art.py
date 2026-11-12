"""QuestArc's pictures (content/art/) drawn with librsvg in the roles'
colours (pensum/ui/journey/art.py). Skipped when the QuestArc content in
PENSUM_QUESTARC_DIR has no pictures yet (they arrive with the QuestArc
release after 3.1.0, QuestArc#86)."""
import re

import cairo
import pytest

from pensum.game import content
from pensum.ui.journey import art

SCENE = "meadow-finished"
# One pure colour per role, so every pixel tells which role drew it.
ROLES = {"fg": (1.0, 0.0, 0.0), "accent": (0.0, 1.0, 0.0), "dim": (0.0, 0.0, 1.0),
         "bg": (1.0, 1.0, 0.0), "tint": (0.0, 1.0, 1.0), "tint-strong": (1.0, 0.0, 1.0)}
PURE = {(round(b * 255), round(g * 255), round(r * 255), 255): role
        for role, (r, g, b) in ROLES.items()}  # B, G, R, A


@pytest.fixture
def scene():
    found = content.scene(SCENE)
    if found is None:
        pytest.skip("no content/art in PENSUM_QUESTARC_DIR")
    return found


def render(scene, width=1280, height=480):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    art.draw_scene(cairo.Context(surface), scene, width, height, ROLES)
    surface.flush()
    data = surface.get_data()
    return [tuple(data[i:i + 4]) for i in range(0, len(data), 4)]


def test_scene_is_drawn_only_in_the_roles_colours(scene):
    pixels = [p for p in render(scene) if p[3] == 255]
    seen = {PURE[p] for p in pixels if p in PURE}
    # dim is kept for keepsakes; the scene uses the other five roles.
    assert seen == set(ROLES) - {"dim"}
    # Antialiased edges between two roles mix them; anything else would be
    # a colour of the picture's own (an unfilled shape is black).
    assert (0, 0, 0, 255) not in pixels
    assert sum(p in PURE for p in pixels) / len(pixels) > 0.97


def test_far_band_is_one_silhouette_in_tint(scene):
    far = [p for p in scene["pictures"] if p.get("band") == "far"]
    assert far
    ground = scene["pictures"][0]
    only_far = dict(scene, pictures=[dict(ground, art="stone", x=-400)] + far)  # off-scene filler
    pixels = {p for p in render(only_far) if p[3] == 255}
    assert {PURE[p] for p in pixels if p in PURE} == {"tint"}


def test_every_picture_of_the_scene_exists_and_has_a_title(scene):
    for item in scene["pictures"]:
        assert content.art_path(item["art"]) is not None, item["art"]
        assert art.title(item["art"])


def test_every_class_in_content_art_is_a_role_pensum_fills(scene):
    folder = content.directory() / "content" / "art"
    used = {c for path in folder.glob("*.svg")
            for c in re.findall(r'class="([^"]*)"', path.read_text(encoding="utf-8"))}
    assert used <= set(art.ROLES)
    assert set(art.ROLES) == set(ROLES)


def test_names_cannot_leave_the_folder(scene):
    assert content.art_path("../journeys/gentle-morning") is None
    assert content.art_path("Tree") is None
    assert content.scene("../x") is None


def test_stylesheet_has_the_roles():
    css = art.stylesheet({"fg": (0, 0, 0), "accent": (1, 0.5, 0), "dim": (0.5, 0.5, 0.5),
                          "bg": (1, 1, 1), "tint": (1, 0.92, 0.84), "tint-strong": (1, 0.8, 0.6)})
    assert css == (".accent{fill:#ff8000}.bg{fill:#ffffff}.dim{fill:#808080}"
                   ".fg{fill:#000000}.tint{fill:#ffebd6}.tint-strong{fill:#ffcc99}")


def test_far_stylesheet_fills_every_role_with_tint():
    css = art.far_stylesheet(ROLES)
    assert css.count("fill:#00ffff") == len(ROLES)
