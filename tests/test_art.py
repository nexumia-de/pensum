"""QuestArc's pictures (content/art/) drawn with librsvg in the roles'
colours (pensum/ui/journey/art.py). Skipped when the QuestArc content in
PENSUM_QUESTARC_DIR has no pictures yet (they arrive with the QuestArc
release after 3.1.0, QuestArc#86)."""
import cairo
import pytest

from pensum.game import content
from pensum.ui.journey import art

SCENE = "spike-region"
ROLES = {"fg": (1.0, 0.0, 0.0), "accent": (0.0, 1.0, 0.0), "dim": (0.0, 0.0, 1.0)}


@pytest.fixture
def scene():
    found = content.scene(SCENE)
    if found is None:
        pytest.skip("no content/art in PENSUM_QUESTARC_DIR")
    return found


def render(scene, width=640, height=240):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    art.draw_scene(cairo.Context(surface), scene, width, height, art.stylesheet(ROLES))
    surface.flush()
    data = surface.get_data()
    return [tuple(data[i:i + 4]) for i in range(0, len(data), 4)]  # B, G, R, A


def test_scene_is_drawn_only_in_the_roles_colours(scene):
    pixels = [p for p in render(scene) if p[3] == 255]
    pure = {(0, 0, 255, 255): "fg", (0, 255, 0, 255): "accent", (255, 0, 0, 255): "dim"}
    seen = {pure[p] for p in pixels if p in pure}
    assert seen == {"fg", "accent", "dim"}
    # Antialiased edges between two roles mix them; anything else would be
    # a colour of the picture's own (an unfilled shape is black).
    assert (0, 0, 0, 255) not in pixels
    assert sum(p in pure for p in pixels) / len(pixels) > 0.97


def test_every_picture_of_the_scene_exists_and_has_a_title(scene):
    for item in scene["pictures"]:
        assert content.art_path(item["art"]) is not None, item["art"]
        assert art.title(item["art"])


def test_names_cannot_leave_the_folder(scene):
    assert content.art_path("../journeys/gentle-morning") is None
    assert content.art_path("Tree") is None
    assert content.scene("../x") is None


def test_stylesheet_has_the_three_roles():
    css = art.stylesheet({"fg": (0, 0, 0), "accent": (1, 0.5, 0), "dim": (0.5, 0.5, 0.5)})
    assert css == ".accent{fill:#ff8000}.dim{fill:#808080}.fg{fill:#000000}"
