"""One task in a list: a check button to mark it done, the title with its
time and subtask summary, and a button to start or stop its timer."""
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from pensum import duration
from pensum.store import dates


PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High"}


def summary(ds, task, today, running_ms=0):
    """"25m / 1h · 2 of 3 subtasks · Garden": what the row's subtitle says."""
    from pensum.store.tasks import priority_level
    parts = []
    level = priority_level(task)
    if level:
        parts.append(PRIORITY_NAMES[level] + " priority")
    from pensum.store.tasks import deadline_day
    deadline = deadline_day(ds, task) if not task.get("isDone") else None
    if deadline:
        if deadline < today:
            parts.append("Deadline passed")
        elif deadline == today:
            parts.append("Deadline today")
        else:
            parts.append("Deadline " + dates.parse_day(deadline).strftime("%a, %-d %b"))
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


MOVES = (("Move to Top", "top", -10_000), ("Move Up", "up", -1),
         ("Move Down", "down", 1), ("Move to Bottom", "bottom", 10_000))


class TaskRow(Adw.ActionRow):
    def __init__(self, window, task_id, context_label=None, context=None):
        """`context` is the list the row is in; None for a subtask row."""
        super().__init__(activatable=True, title_lines=2, subtitle_lines=1)
        self.window = window
        self.task_id = task_id
        self.context_label = context_label
        self.context = context
        self._add_move_menu()
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

    def _add_move_menu(self):
        """Long press, right click or Alt+Up/Down reorder the task."""
        group = Gio.SimpleActionGroup()
        menu = Gio.Menu()
        for label, name, offset in MOVES:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_, o=offset: self.move(o))
            group.add_action(action)
            menu.append(label, f"row.{name}")
        self.backlog_action = Gio.SimpleAction.new("backlog", None)
        self.backlog_action.connect("activate", self._on_backlog)
        group.add_action(self.backlog_action)
        if self.context is not None and self.context.kind == "project":
            section = Gio.Menu()
            section.append("Move to Backlog / List", "row.backlog")
            menu.append_section(None, section)
        self.insert_action_group("row", group)
        self.popover = Gtk.PopoverMenu(menu_model=menu, has_arrow=True)
        self.popover.set_parent(self)
        self.connect("destroy", lambda *_: self.popover.unparent())
        press = Gtk.GestureLongPress(touch_only=False)
        press.connect("pressed", self._on_menu)
        self.add_controller(press)
        click = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        click.connect("pressed", self._on_menu)
        self.add_controller(click)
        keys = Gtk.ShortcutController()
        for key, offset in (("<Alt>Up", -1), ("<Alt>Down", 1)):
            keys.add_shortcut(Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(key),
                Gtk.CallbackAction.new(lambda *_, o=offset: self.move(o) or True)))
        self.add_controller(keys)

    def _on_menu(self, gesture, x, y):
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.popover.set_pointing_to(rect)
        self.popover.popup()

    def _on_backlog(self, *_):
        from pensum.store import tasks
        ds = self.window.ds
        project = ds.project_entities.get((self.task or {}).get("projectId")) or {}
        in_backlog = self.task_id in project.get("backlogTaskIds", [])
        if tasks.set_backlog(ds, self.task_id, not in_backlog):
            self.window.changed()

    def move(self, offset):
        from pensum.store import tasks
        if tasks.move(self.window.ds, self.task_id, self.context, offset):
            self.window.changed()
            self.window.focus_task_row(self.task_id)

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
