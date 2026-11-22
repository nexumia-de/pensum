"""Focus mode (#19): a page for the running task with Pomodoro, Flowtime
or a countdown (pensum/store/focus.py). Work starts tracking the task;
breaks stop tracking when `focusMode.isPauseTrackingDuringBreak` says so
and start it again afterwards. A finished session is logged in
`metric.focusSessions`, and the end of a session or a break is told by a
notification, so it also reaches a phone whose screen is off."""
from gi.repository import Adw, Gio, GLib, Gtk

from pensum.duration import format_clock
from pensum.i18n import _
from pensum.store import dates, focus, metric

COUNTDOWNS = (10, 15, 25, 45, 60)


def mode_names():
    return {"Pomodoro": _("Pomodoro"), "Flowtime": _("Flowtime"), "Countdown": _("Countdown")}


class FocusPage(Adw.NavigationPage):
    def __init__(self, window, task_id):
        super().__init__(title=_("Focus"), tag="focus")
        self.window = window
        self.task_id = task_id
        self.session = None
        self._source = None
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, valign=Gtk.Align.CENTER,
                      margin_top=24, margin_bottom=24, margin_start=16, margin_end=16)
        self.task_label = Gtk.Label(wrap=True, justify=Gtk.Justification.CENTER,
                                    css_classes=["title-3"])
        box.append(self.task_label)
        self.modes = Gtk.Box(css_classes=["linked"], halign=Gtk.Align.CENTER)
        self._mode_buttons = {}
        first = None
        for mode, name in mode_names().items():
            button = Gtk.ToggleButton(label=name, group=first)
            first = first or button
            button.connect("toggled", self._on_mode, mode)
            self.modes.append(button)
            self._mode_buttons[mode] = button
        box.append(self.modes)
        self.minutes = Adw.SpinRow.new_with_range(1, 180, 5)
        self.minutes.set_title(_("Minutes"))
        rows = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        rows.append(self.minutes)
        self.minutes_box = rows
        box.append(rows)
        self.phase = Gtk.Label(css_classes=["dimmed"])
        box.append(self.phase)
        self.clock = Gtk.Label(css_classes=["title-1", "numeric"])
        self.clock.update_property([Gtk.AccessibleProperty.LABEL], [_("Time")])
        box.append(self.clock)
        self.button = Gtk.Button(halign=Gtk.Align.CENTER,
                                 css_classes=["pill", "suggested-action"])
        self.button.connect("clicked", self._on_button)
        box.append(self.button)
        toolbar.set_content(Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.set_child(toolbar)
        self.connect("hidden", lambda *_: self._stop_clock())
        self.connect("shown", lambda *_: self._resume())
        task = window.ds.task(task_id) or {}
        default = focus.countdown_for_task(focus.DEFAULTS["duration"], task)
        self.minutes.set_value(default // focus.MINUTE)
        self._mode_buttons["Pomodoro"].set_active(True)
        self.refresh()

    # --- state -----------------------------------------------------------

    def _mode(self):
        return next(m for m, b in self._mode_buttons.items() if b.get_active())

    def _on_mode(self, button, mode):
        if button.get_active():
            self.refresh()

    def refresh(self):
        task = self.window.ds.task(self.task_id)
        if task is None:
            self.window.nav.pop()
            return
        self.task_label.set_label(task.get("title") or "")
        running = self.session is not None
        self.modes.set_sensitive(not running)
        self.minutes_box.set_visible(not running and self._mode() == "Countdown")
        self.tick()

    def tick(self):
        now = dates.now_ms()
        if self.session is None:
            self.phase.set_label(_("Ready"))
            mode = self._mode()
            length = (focus.pomodoro_config(self.window.ds.config)["duration"] if mode == "Pomodoro"
                      else int(self.minutes.get_value()) * focus.MINUTE if mode == "Countdown" else 0)
            self.clock.set_label(format_clock(length))
            self.button.set_label(_("Start Focus"))
            return
        if self.session.is_due(now):
            self._finish_phase(now)
            return
        remaining = self.session.remaining(now)
        shown = self.session.elapsed(now) if remaining is None else remaining
        self.clock.set_label(format_clock(shown))
        if self.session.phase == "work":
            self.phase.set_label(_("Session {number}").format(number=self.session.cycle)
                                 if self.session.mode == "Pomodoro" else _("Focus"))
            self.button.set_label(_("End Session"))
        else:
            self.phase.set_label(_("Long Break") if self.session.long_break else _("Break"))
            self.button.set_label(_("Skip Break"))

    # --- actions ---------------------------------------------------------

    def _on_button(self, _button):
        now = dates.now_ms()
        if self.session is None:
            self.start(now)
        elif self.session.phase == "work":
            self._end_work(now, notify=False)
        else:
            self._end_break(now, notify=False)
        self.refresh()

    def start(self, now):
        countdown = int(self.minutes.get_value()) * focus.MINUTE
        self.session = focus.Session(self._mode(), self.window.ds.config, now, countdown)
        self._track(True)
        if self._source is None:
            self._source = GLib.timeout_add_seconds(1, self._on_second)

    def _finish_phase(self, now):
        if self.session.phase == "work":
            self._end_work(now, notify=True)
        else:
            self._end_break(now, notify=True)
        self.refresh()

    def _end_work(self, now, notify):
        worked, has_break = self.session.end_work(now)
        if metric.log_focus_session(self.window.ds, self.window.ds.today(now), worked):
            self.window.changed()
        if has_break:
            if focus.pause_tracking_in_breaks(self.window.ds.config):
                self._track(False)
            if notify:
                self._notify(_("Time for a break"), _("The focus session is over."))
        else:
            self._track(False)
            self._done()
            if notify:
                self._notify(_("Focus session done"), _("Well done."))

    def _end_break(self, now, notify):
        self.session.end_break(now)
        if self.session.phase == "work":
            self._track(True)
            if notify:
                self._notify(_("Break is over"), _("The next focus session starts."))
        else:
            self._done()
            if notify:
                self._notify(_("Break is over"), _("Back to work when you are ready."))

    def _done(self):
        self.session = None
        self._stop_clock()

    def _track(self, on):
        timer = self.window.timer
        running = timer.task_id == self.task_id
        if on != running:
            timer.toggle(self.task_id)

    def _notify(self, title, body):
        note = Gio.Notification.new(title)
        note.set_body(body)
        app = self.window.get_application()
        if app is not None:
            app.send_notification("focus", note)

    def _on_second(self):
        if self.session is None:
            self._source = None
            return GLib.SOURCE_REMOVE
        self.tick()
        return GLib.SOURCE_CONTINUE

    def _resume(self):
        """Back on the page: the session went on, the clock shows it again."""
        if self.session is not None and self._source is None:
            self._source = GLib.timeout_add_seconds(1, self._on_second)
        self.tick()

    def _stop_clock(self):
        if self._source is not None:
            GLib.source_remove(self._source)
            self._source = None
