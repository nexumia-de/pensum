"""One task in a list: a check button to mark it done, the title with its
time and subtask summary, and a button to start or stop its timer."""
from gi.repository import Adw, GLib, Gtk

from pensum import duration


def summary(ds, task, today, running_ms=0):
    """"25m / 1h · 2 of 3 subtasks · Garden": what the row's subtitle says."""
    parts = []
    spent = task.get("timeSpent", 0) + running_ms
    estimate = task.get("timeEstimate", 0)
    if spent and estimate:
        parts.append(f"{duration.format_short(spent)} / {duration.format_short(estimate)}")
    elif spent:
        parts.append(duration.format_short(spent))
    elif estimate:
        parts.append(f"{duration.format_short(estimate)} estimated")
    subs = ds.subtasks(task)
    if subs:
        done = sum(1 for s in subs if s.get("isDone"))
        parts.append(f"{done} of {len(subs)} subtasks")
    return " · ".join(parts)


class TaskRow(Adw.ActionRow):
    def __init__(self, window, task_id, context_label=None):
        super().__init__(activatable=True, title_lines=2, subtitle_lines=1)
        self.window = window
        self.task_id = task_id
        self.context_label = context_label
        self.check = Gtk.CheckButton(valign=Gtk.Align.CENTER)
        self.check.add_css_class("selection-mode")
        self._check_handler = self.check.connect("toggled", self._on_done)
        self.add_prefix(self.check)
        self.play = Gtk.Button(valign=Gtk.Align.CENTER)
        self.play.add_css_class("flat")
        self.play.add_css_class("circular")
        self.play.connect("clicked", self._on_play)
        self.add_suffix(self.play)
        self.connect("activated", lambda *_: window.show_task(task_id))
        self.refresh()

    @property
    def task(self):
        return self.window.ds.task(self.task_id)

    def refresh(self):
        task = self.task
        if task is None:
            return
        ds = self.window.ds
        self.set_title(GLib.markup_escape_text(task.get("title") or "Untitled"))
        running = self.window.timer.task_id
        running_ms = self.window.timer.unbooked_ms() if running == self.task_id else 0
        if running and running in task.get("subTaskIds", ()):
            running_ms = self.window.timer.unbooked_ms()
        text = summary(ds, task, ds.today(), running_ms)
        if self.context_label:
            label = self.context_label(task)
            if label:
                text = f"{text} · {label}" if text else label
        self.set_subtitle(GLib.markup_escape_text(text))
        self.check.handler_block(self._check_handler)
        self.check.set_active(bool(task.get("isDone")))
        self.check.handler_unblock(self._check_handler)
        title = task.get("title") or "Untitled"
        self.check.update_property([Gtk.AccessibleProperty.LABEL],
                                   [f"Mark “{title}” as done"])
        trackable = not task.get("subTaskIds") and not task.get("isDone")
        self.play.set_visible(trackable or running == self.task_id)
        is_running = running == self.task_id
        self.play.set_icon_name("media-playback-pause-symbolic" if is_running
                                else "media-playback-start-symbolic")
        tip = "Stop Timer" if is_running else "Start Timer"
        self.play.set_tooltip_text(tip)
        self.play.update_property([Gtk.AccessibleProperty.LABEL], [tip])
        if is_running:
            self.add_css_class("pensum-running")
        else:
            self.remove_css_class("pensum-running")

    def _on_done(self, check):
        from pensum.store import tasks
        tasks.set_done(self.window.ds, self.task_id, check.get_active())
        self.window.changed()

    def _on_play(self, *_):
        self.window.timer.toggle(self.task_id)
