"""The journey's drawn marks use Day Planner's own accent from style.css,
not the system accent (#52)."""
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

from pensum.ui.journey import drawing  # noqa: E402


def test_accent_is_the_apps_indigo():
    Adw.init()
    manager = Adw.StyleManager.get_default()
    manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    css = Gtk.CssProvider()
    css.load_from_path(str(Path(__file__).resolve().parents[1] / "pensum" / "style.css"))
    Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    try:
        colour = drawing.accent(Gtk.Label())
        got = tuple(round(c * 255) for c in (colour.red, colour.green, colour.blue))
        # libadwaita 1.6+ may darken the text accent slightly for contrast.
        assert all(abs(a - b) <= 8 for a, b in zip(got, (0x5B, 0x4F, 0xC7))), got
    finally:
        Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), css)
        manager.set_color_scheme(Adw.ColorScheme.DEFAULT)
