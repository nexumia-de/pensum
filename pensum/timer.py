"""The running timer of the current task: books the elapsed time into the
dataset each minute and when tracking stops, like Super Productivity's
tick. The UI asks it for the time to show."""
from gi.repository import GLib

from pensum.store import dates, tracking

BOOK_EVERY_S = 60


class Timer:
    def __init__(self, ds_getter, changed, tick):
        """ds_getter() returns the current dataset; changed() is called after
        time was booked; tick() every second while a task runs."""
        self._ds = ds_getter
        self._changed = changed
        self._tick = tick
        self._since = None
        self._source = None
        self._booked_at = 0

    @property
    def task_id(self):
        return self._ds().current_task_id()

    def resume(self):
        """After loading: a task stored as current runs on from now."""
        if self.task_id and self._source is None:
            self._start_clock()

    def toggle(self, task_id):
        """Start the task, or stop it when it runs."""
        if self.task_id == task_id:
            self.stop()
        else:
            self.book()
            if tracking.set_current(self._ds(), task_id):
                self._start_clock()
            self._changed()

    def stop(self):
        self.book()
        tracking.set_current(self._ds(), None)
        if self._source:
            GLib.source_remove(self._source)
            self._source = None
        self._since = None
        self._changed()

    def unbooked_ms(self):
        return dates.now_ms() - self._since if self._since else 0

    def book(self):
        """Add the time since the last booking to the current task."""
        if self.task_id and self._since:
            now = dates.now_ms()
            tracking.add_time(self._ds(), self.task_id, now - self._since, now)
            self._since = now
            return True
        return False

    def _start_clock(self):
        self._since = dates.now_ms()
        self._booked_at = GLib.get_monotonic_time()
        if self._source is None:
            self._source = GLib.timeout_add_seconds(1, self._on_second)

    def _on_second(self):
        if not self.task_id:
            self._source = None
            self._since = None
            self._tick()
            return GLib.SOURCE_REMOVE
        if GLib.get_monotonic_time() - self._booked_at >= BOOK_EVERY_S * 1_000_000:
            self._booked_at = GLib.get_monotonic_time()
            if self.book():
                self._changed()
        self._tick()
        return GLib.SOURCE_CONTINUE
