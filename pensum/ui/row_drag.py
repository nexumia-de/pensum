"""Reorder task rows by dragging: a row dropped on another row of the same
list takes its place. A pointer drags at once; a finger drags after a long
press, because until then a drag scrolls the list. While a drag is near
the upper or lower edge of the list, the list scrolls."""
from gi.repository import Gdk, GLib, GObject, Graphene, Gtk

from pensum.store import order

EDGE = 56  # px from the edge of the scrolled area where a drag scrolls it
STEP = 10  # px per frame

# The row being dragged: drags stay inside the window, so the drop asks
# the row itself instead of the dragged value.
_dragged = None
_scroll = {"speed": 0, "scroller": None, "tick": 0}


def attach(row):
    """Make a task row a drag source and a place to drop another one."""
    source = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
    source.connect("prepare", _on_prepare, row)
    source.connect("drag-begin", _on_begin, row)
    source.connect("drag-end", _on_end, row)
    row.add_controller(source)
    target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
    target.connect("enter", _on_motion, row)
    target.connect("motion", _on_motion, row)
    target.connect("leave", _on_leave, row)
    target.connect("drop", _on_drop, row)
    row.add_controller(target)


def can_drop(dragged, row):
    """Rows of one list box share one stored order (open, done, backlog,
    subtasks); the overdue tasks have none."""
    return (dragged is not None and dragged is not row
            and dragged.get_parent() is row.get_parent()
            and row.task_id in order.siblings(row.window.ds, dragged.task_id,
                                              dragged.context))


def drop(dragged, row):
    """Write the new order and show it. Returns True when the task moved."""
    window = row.window
    if not can_drop(dragged, row) or not order.move_to(
            window.ds, dragged.task_id, dragged.context, row.task_id):
        return False
    window.changed()
    window.focus_task_row(dragged.task_id)
    return True


def _on_prepare(source, x, y, row):
    if len(order.siblings(row.window.ds, row.task_id, row.context)) < 2:
        return None
    source.set_icon(Gtk.WidgetPaintable.new(row), int(x), int(y))
    return Gdk.ContentProvider.new_for_value(row.task_id)


def _on_begin(_source, _drag, row):
    global _dragged
    _dragged = row
    row.held = False
    row.remove_css_class("pensum-held")
    row.add_css_class("pensum-dragged")


def _on_end(_source, _drag, _delete, row):
    global _dragged
    _dragged = None
    row.remove_css_class("pensum-dragged")
    _set_scroll(None, 0)


def _mark(row, name=None):
    for css in ("pensum-drop-before", "pensum-drop-after"):
        if css == name:
            row.add_css_class(css)
        else:
            row.remove_css_class(css)


def _on_motion(_target, x, y, row):
    if not can_drop(_dragged, row):
        _mark(row)
        return 0
    # A line where the task will land: moving down it goes after the row.
    _mark(row, "pensum-drop-after" if _dragged.get_index() < row.get_index()
          else "pensum-drop-before")
    scroller = row.get_ancestor(Gtk.ScrolledWindow)
    if scroller is not None:
        found, point = row.compute_point(scroller, Graphene.Point().init(x, y))
        speed = 0
        if found and point.y < EDGE:
            speed = -STEP
        elif found and point.y > scroller.get_height() - EDGE:
            speed = STEP
        _set_scroll(scroller, speed)
    return Gdk.DragAction.MOVE


def _on_leave(_target, row):
    _mark(row)
    _set_scroll(None, 0)


def _on_drop(_target, _value, _x, _y, row):
    _mark(row)
    _set_scroll(None, 0)
    dragged = _dragged
    if not can_drop(dragged, row):
        return False
    # The list is rebuilt once the drag has ended, not inside its signal.
    GLib.idle_add(lambda: drop(dragged, row) and False)
    return True


def _set_scroll(scroller, speed):
    """Scroll `scroller` by `speed` px each frame until the speed is 0."""
    old = _scroll["scroller"]
    if old is not None and (speed == 0 or old is not scroller):
        old.remove_tick_callback(_scroll["tick"])
        _scroll.update(scroller=None, tick=0)
    _scroll["speed"] = speed
    if speed and _scroll["scroller"] is None:
        _scroll.update(scroller=scroller,
                       tick=scroller.add_tick_callback(_on_tick))


def _on_tick(scroller, _clock):
    adjustment = scroller.get_vadjustment()
    adjustment.set_value(adjustment.get_value() + _scroll["speed"])
    return True
