"""Work that belongs to the start of a logical day: once at start, after
an import and whenever the day changes (checked every minute), the due
repeat instances are created, as Super Productivity does on day change
(task-due.effects, createRepeatableTasksAndAddDueToday$)."""
import logging

from gi.repository import GLib

from pensum.store.repeat import instances

log = logging.getLogger(__name__)
CHECK_SECONDS = 60


class DayWatch:
    def __init__(self, ds_getter, changed):
        self._ds = ds_getter
        self._changed = changed
        self._day = None
        GLib.timeout_add_seconds(CHECK_SECONDS, self._check)

    def start_day(self):
        """Create today's instances now; True when something changed."""
        ds = self._ds()
        self._day = ds.today()
        created = instances.create_due(ds)
        if created:
            log.info("created %d repeat instances", len(created))
        return bool(created)

    def _check(self):
        if self._ds().today() != self._day:
            self.start_day()
            self._changed()
        return GLib.SOURCE_CONTINUE
