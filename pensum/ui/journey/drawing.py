"""Small drawn shapes for the journey: a day's mark in the last due
days. Colours come from the theme: the accent
for what is done, the text colour (dimmed) for what is ahead. Every
shape also has words next to it or as its accessible label."""
import math
import warnings

from gi.repository import Adw, Gtk


def accent(widget):
    manager = Adw.StyleManager.get_default()
    if hasattr(manager, "get_accent_color_rgba"):
        return manager.get_accent_color_rgba()
    # libadwaita before 1.6 (host previews): the named colour from style.css.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        found, color = widget.get_style_context().lookup_color("accent_bg_color")
    return color if found else widget.get_color()


def _rgba(cr, color, alpha=1.0):
    cr.set_source_rgba(color.red, color.green, color.blue, color.alpha * alpha)


def day_mark(mark):
    """One of the last due days: done (filled), gap (open ring), still
    open (dashed ring) or paused (dimmed ring with a bar)."""
    area = Gtk.DrawingArea(content_width=24, content_height=24,
                           accessible_role=Gtk.AccessibleRole.PRESENTATION)

    def draw(area, cr, width, height):
        fg, acc = area.get_color(), accent(area)
        x, y, r = width / 2, height / 2, 8
        cr.set_line_width(2)
        cr.arc(x, y, r, 0, 2 * math.pi)
        if mark == "done":
            _rgba(cr, acc)
            cr.fill()
            return
        _rgba(cr, fg, 0.5 if mark == "gap" else 0.35)
        if mark == "open":
            cr.set_dash([2.5, 2.5])
        cr.stroke()
        if mark == "paused":
            cr.set_dash([])
            cr.move_to(x - 4, y)
            cr.line_to(x + 4, y)
            cr.stroke()

    area.set_draw_func(draw)
    return area
