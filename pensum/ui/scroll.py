"""Keep a scrolled list where it is when its rows are rebuilt."""
from gi.repository import Gtk


def focus_in_place(row):
    """Give a freshly built row the keyboard focus without the jump to the
    top that focusing a row without a place causes; once it has a place,
    scroll just far enough to show it."""
    scroller = row.get_ancestor(Gtk.ScrolledWindow)
    if scroller is None:
        row.grab_focus()
        return
    adjustment = scroller.get_vadjustment()
    value = adjustment.get_value()
    row.grab_focus()
    adjustment.set_value(value)
    frames = [0]

    def reveal(*_):
        frames[0] += 1
        if frames[0] < 2:  # the first frame lays the rows out
            return True
        viewport = scroller.get_child()
        if row.get_parent() is not None and isinstance(viewport, Gtk.Viewport):
            viewport.scroll_to(row, None)
        return False

    scroller.add_tick_callback(reveal)
