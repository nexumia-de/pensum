"""The moment of the tick (QuestArc docs/journey-design.md): a drawing
remembers which run, version and number of flowers it showed last. When
a redraw shows more flowers, the new ones grow in from their foot (scale
from 0.6 and fade, 600 ms, ease-out). The first draw animates nothing,
and nothing moves when animations are off in the system."""
from gi.repository import GLib, Gtk

DURATION_US = 600_000


def animations_on():
    settings = Gtk.Settings.get_default()
    return bool(settings and settings.get_property("gtk-enable-animations"))


class Growth:
    def __init__(self):
        self.key = None
        self.count = None
        self.new = range(0)
        self.start = None

    def show(self, key, count):
        """What is drawn now: `key` names the run and its version, `count`
        the flowers. True when new flowers grow in."""
        grows = (key == self.key and self.count is not None and count > self.count
                 and animations_on())
        self.new = range(self.count, count) if grows else range(0)
        self.start = None
        self.key, self.count = key, count
        return grows

    def running(self):
        return len(self.new) > 0

    def factor(self, index):
        """0…1 for flower `index` (0-based): 1 once it has grown."""
        if index not in self.new or self.start is None:
            return 1.0 if index not in self.new else 0.0
        passed = (GLib.get_monotonic_time() - self.start) / DURATION_US
        return min(1.0, max(0.0, passed))

    def attach(self, widget):
        """Redraw `widget` every frame until the new flowers have grown."""
        if not self.running():
            return

        def frame(area, clock):
            if self.start is None:
                self.start = GLib.get_monotonic_time()
            area.queue_draw()
            if not self.running() or self.factor(self.new[0]) >= 1.0:
                self.new = range(0)
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        widget.add_tick_callback(frame)
