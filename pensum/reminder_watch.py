"""Reminders as notifications (#13, docs/reminders.md): when a task's
`remindAt` comes, a notification with Done and Snooze. It works on the
window's dataset while a window is open and on the file while none is,
so reminders also come when Day Planner is closed: the application then
stays in the background as long as a reminder is pending or a repeat
rule will bring one, and creates the repeat instances of a new day there. The clock is checked at least
once a minute, because a timer does not count the time a phone sleeps.
Logs name ids and counts, never titles."""
import logging

from gi.repository import Gio, GLib

from pensum import background
from pensum.store import dates, reminders, tasks
from pensum.store.repeat import instances

log = logging.getLogger(__name__)
CHECK_SECONDS = 60


class ReminderWatch:
    def __init__(self, app):
        self.app = app
        self._source = None
        self._shown = set()     # (task id, remindAt) already notified
        self._held = False
        self._asked = False
        self._day = None

    # --- data ----------------------------------------------------------------

    def _window(self):
        return next((w for w in self.app.get_windows() if hasattr(w, "ds")
                     and not getattr(w, "closed", False)), None)

    def _dataset(self):
        window = self._window()
        return window.ds if window else self.app.files.load()

    def change(self, make):
        """Run `make(ds)` on the window's dataset, or on the file when no
        window is open, and save."""
        window = self._window()
        if window:
            make(window.ds)
            window.changed()
            return
        ds = self.app.files.load()
        make(ds)
        self.app.files.save(ds)
        self.check()

    # --- watching ------------------------------------------------------------

    def check(self):
        """Notify what is due and wait for the next reminder."""
        if self._source is not None:
            GLib.source_remove(self._source)
            self._source = None
        ds = self._dataset()
        if self._window() is None:
            ds = self._start_day(ds)
        now = dates.now_ms()
        for task_id in reminders.due(ds, now):
            key = (task_id, ds.tasks[task_id]["remindAt"])
            if key not in self._shown:
                self._shown.add(key)
                self._notify(ds.tasks[task_id])
        self._shown &= {(task_id, at) for at, task_id in reminders.pending(ds)}
        self._hold(reminders.expected(ds)
                   and self.app.settings_store.load().remind_when_closed)
        upcoming = reminders.next_at(ds, now)
        if upcoming is not None or self._held:
            wait = CHECK_SECONDS if upcoming is None else \
                min(CHECK_SECONDS, max(1, (upcoming - now) // 1000 + 1))
            self._source = GLib.timeout_add_seconds(wait, self._on_time)

    def _on_time(self):
        self._source = None
        self.check()
        return GLib.SOURCE_REMOVE

    def _start_day(self, ds):
        """Without a window: the repeat instances of a new day, so that a
        habit's reminder comes on a day Day Planner was not opened."""
        today = ds.today()
        if today == self._day:
            return ds
        self._day = today
        created = instances.create_due(ds)
        if created:
            log.info("created %d repeat instances in the background", len(created))
            self.app.files.save(ds)
        return ds

    def _hold(self, wanted):
        """Stay alive without a window while a reminder is pending."""
        if wanted and not self._held:
            self.app.hold()
            if not self._asked:
                self._asked = True
                background.request(autostart=True)
        elif self._held and not wanted:
            self.app.release()
        self._held = wanted

    # --- notifications -------------------------------------------------------

    def _notify(self, task):
        note = Gio.Notification.new(task.get("title") or "Reminder")
        due = task.get("dueWithTime")
        if due:
            note.set_body("Planned at " + GLib.DateTime.new_from_unix_local(
                due // 1000).format("%H:%M"))
        note.set_priority(Gio.NotificationPriority.HIGH)
        target = GLib.Variant("s", task["id"])
        note.set_default_action_and_target("app.reminder-open", target)
        note.add_button_with_target("Done", "app.reminder-done", target)
        note.add_button_with_target(f"Snooze {reminders.SNOOZE_MINUTES} min",
                                    "app.reminder-snooze", target)
        self.app.send_notification(f"reminder-{task['id']}", note)
        log.info("reminder shown for task %s", task["id"])

    def _withdraw(self, task_id):
        self.app.withdraw_notification(f"reminder-{task_id}")

    def done(self, task_id):
        self._withdraw(task_id)
        self.change(lambda ds: task_id in ds.tasks and tasks.set_done(ds, task_id, True))

    def snooze(self, task_id):
        self._withdraw(task_id)
        self.change(lambda ds: task_id in ds.tasks and reminders.snooze(ds, task_id))

    def open(self, task_id):
        """The notification itself: the reminder is put away and the task shown."""
        self._withdraw(task_id)
        self.app.activate()
        window = self._window()
        if window and task_id in window.ds.tasks:
            reminders.dismiss(window.ds, task_id)
            window.changed()
            window.show_task(task_id)
