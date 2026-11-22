"""The break reminder (#20, docs/breaks.md): counts tracked work without a
break once a minute (pensum/store/breaks.py) and, once that is over the
setting, sends a calm notification with **Take a Break** and **Snooze**;
no full-screen blocker. Taking the break stops tracking; when tracking
starts again, the time in between is counted as a break of the list
that is shown (`timeTracking.*.b`, `bt`), as Super Productivity counts
breaks of the active work context. Logs name no titles."""
import logging

from gi.repository import Gio, GLib

from pensum.i18n import _
from pensum.store import breaks, dates

log = logging.getLogger(__name__)
TICK_SECONDS = 60
NOTIFICATION = "take-a-break"


class BreakWatch:
    def __init__(self, window):
        self.window = window
        self.counter = breaks.Counter()
        self.break_since = None
        self._shown = False
        self._last = dates.now_ms()
        self._source = GLib.timeout_add_seconds(TICK_SECONDS, self._on_tick)
        # Notification buttons need application actions; they act on the
        # newest window's watch.
        app = window.get_application()
        if app is not None:
            app.break_watch = self
            for name, method in (("take-a-break", "take_break"), ("snooze-break", "snooze")):
                if app.lookup_action(name) is None:
                    action = Gio.SimpleAction.new(name, None)
                    action.connect("activate", lambda *_a, m=method, a=app:
                                   getattr(a.break_watch, m)())
                    app.add_action(action)

    def stop(self):
        if self._source is not None:
            GLib.source_remove(self._source)
            self._source = None

    def _on_tick(self):
        self.check(dates.now_ms())
        return GLib.SOURCE_CONTINUE

    def check(self, now):
        """Feed the time since the last check and remind when due."""
        ds = self.window.ds
        tracking = bool(ds.current_task_id())
        self.counter.tick(max(0, now - self._last), tracking)
        self._last = now
        if tracking and self.break_since is not None:
            self._count_break(now)
        if self.counter.due(now, ds.config) and not self._shown:
            self._notify()
        elif not self.counter.due(now, ds.config):
            self._shown = False

    def _notify(self):
        self._shown = True
        minutes = self.counter.worked // breaks.MINUTE
        note = Gio.Notification.new(_("Time for a break"))
        note.set_body(_("You have worked for {hours} h {minutes} min without a break.").format(
            hours=minutes // 60, minutes=minutes % 60))
        note.add_button(_("Take a Break"), "app.take-a-break")
        note.add_button(_("Snooze"), "app.snooze-break")
        note.set_priority(Gio.NotificationPriority.NORMAL)
        app = self.window.get_application()
        if app is not None:
            app.send_notification(NOTIFICATION, note)
        log.debug("break reminder after %d min", minutes)

    def _withdraw(self):
        app = self.window.get_application()
        if app is not None:
            app.withdraw_notification(NOTIFICATION)

    def take_break(self, now=None):
        now = now or dates.now_ms()
        if self.window.ds.current_task_id():
            self.window.timer.stop()
        self.counter.reset()
        self.break_since = now
        self._shown = False
        self._withdraw()
        self.window.toast(_("Enjoy your break"))

    def snooze(self, now=None):
        self.counter.snooze(now or dates.now_ms(), self.window.ds.config)
        self._shown = False
        self._withdraw()

    def _count_break(self, now):
        context = self.window.list_page.context
        if breaks.add_break(self.window.ds, context, self.window.ds.today(self.break_since),
                            now - self.break_since):
            self.window.changed()
        self.break_since = None
