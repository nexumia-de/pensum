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


# The ladders (QuestArc#42): one build per ladder, whole at every version,
# a scaffold while the next version is worked on, a flag when it is ready.

@pytest.fixture
def crossing():
    found = content.ladder("crossing")
    if found is None:
        pytest.skip("no ladders in PENSUM_QUESTARC_DIR")
    return found


def _arts(ladder, version, state="standing", lit=False):
    return [p["art"] for p in art.ladder_scene(ladder, version, state, lit)["pictures"]]


def test_ladder_scene_fills_the_build_slot(crossing):
    scene = art.ladder_scene(crossing, 3)
    assert scene["pictures"][0]["art"] == "setting-river"
    assert [a for a in _arts(crossing, 3) if a.startswith("build-")] == ["build-crossing-3"]
    assert scene["title"] == "A plank bridge"
    for item in scene["pictures"]:
        assert content.art_path(item["art"]) is not None, item["art"]


def test_work_on_the_next_version_is_the_scaffold_behind_the_build(crossing):
    arts = _arts(crossing, 3, "extending")
    assert arts.index("build-scaffold") == arts.index("build-crossing-3") - 1
    assert "pennant" not in arts
    assert art.ladder_scene(crossing, 3, "extending")["title"] == \
        "A plank bridge, work on a stone bridge has begun"


def test_ready_sets_the_flag_and_nothing_is_counted(crossing):
    arts = _arts(crossing, 3, "ready")
    assert "build-scaffold" in arts and "pennant" in arts
    assert not any(a.startswith("material-") for a in arts)
    assert art.ladder_scene(crossing, 3, "ready")["title"] == "A plank bridge, a stone bridge is ready"


def test_ladder_last_version_is_never_extended_and_takes_the_lantern(crossing):
    arts = _arts(crossing, 5, "ready", lit=True)
    assert "build-scaffold" not in arts and arts.count("lantern") == 1


def test_ladder_scene_is_drawn_only_in_the_roles_colours(crossing):
    for version in range(1, len(crossing["versions"]) + 1):
        scene = art.ladder_scene(crossing, version, "ready", version == 5)
        pixels = [p for p in render(scene) if p[3] == 255]
        assert (0, 0, 0, 255) not in pixels
        assert sum(p in PURE for p in pixels) / len(pixels) > 0.95


def test_a_hue_replaces_accent_and_tints_only():
    roles = dict(ROLES)
    hued = art.with_hue(roles, (0.2, 0.4, 0.6))
    assert hued["accent"] == (0.2, 0.4, 0.6)
    assert hued["fg"] == roles["fg"] and hued["bg"] == roles["bg"] and hued["dim"] == roles["dim"]
    assert hued["tint-strong"] == pytest.approx(tuple(0.4 * c + 0.6 * b for c, b in zip((0.2, 0.4, 0.6), roles["bg"])))


# The palette's contrast in Day Planner's styles, computed (WCAG relative
# luminance). libadwaita's cards: white on #fafafb in light; 8 % white on
# #222226 (#343437) in dark, the window #222226 itself. Text: #333338 and
# #ffffff. Thresholds as QuestArc's palette check: accent 3 : 1 (WCAG 1.4.11,
# non-text), tint-strong 1.5 : 1 (decorative, but water must show), the
# outline on tint-strong 3 : 1. tint (16 %) is decorative and not tested.
CARDS = {"light": ["#ffffff", "#fafafb"], "dark": ["#343437", "#222226"]}
TEXT = {"light": "#333338", "dark": "#ffffff"}


def _luminance(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_palette_hue_keeps_its_contrast_on_day_planners_cards():
    palette = content.palette()
    if not palette:
        pytest.skip("no palette in PENSUM_QUESTARC_DIR")
    assert 6 <= len(palette) <= 10
    for name, entry in palette.items():
        for style in ("light", "dark"):
            hue = art.hex_rgb(entry[style])
            for card in map(art.hex_rgb, CARDS[style]):
                strong = art.with_hue({"bg": card}, hue)["tint-strong"]
                assert _contrast(hue, card) >= 3, (name, style)
                assert _contrast(strong, card) >= 1.5, (name, style)
                assert _contrast(art.hex_rgb(TEXT[style]), strong) >= 3, (name, style)
