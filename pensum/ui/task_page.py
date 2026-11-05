"""One task: title, done, timer and estimate, the day it is planned for,
project and tags, notes, subtasks, and deleting it."""
from datetime import datetime

from gi.repository import Adw, GLib, Gtk

from pensum import duration
from pensum.store import dates, tasks
from pensum.ui.task_row import TaskRow


class TaskPage(Adw.NavigationPage):
    def __init__(self, window, task_id):
        super().__init__(title="Task", tag=f"task-{task_id}")
        self.window = window
        self.task_id = task_id
        self.sub_rows = []
        self._notes_source = None
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        page = Adw.PreferencesPage()
        toolbar.set_content(page)
        self.set_child(toolbar)

        main = Adw.PreferencesGroup()
        self.title_row = Adw.EntryRow(title="Title", show_apply_button=True)
        self.title_row.connect("apply", self._on_title)
        main.add(self.title_row)
        self.done_row = Adw.SwitchRow(title="Done")
        self._done_handler = self.done_row.connect("notify::active", self._on_done)
        main.add(self.done_row)
        page.add(main)

        time = Adw.PreferencesGroup(title="Time")
        self.timer_row = Adw.ActionRow(title="Time Spent")
        self.play = Gtk.Button(valign=Gtk.Align.CENTER)
        self.play.add_css_class("circular")
        self.play.connect("clicked", lambda *_: window.timer.toggle(self.task_id))
        self.timer_row.add_suffix(self.play)
        time.add(self.timer_row)
        self.estimate_row = Adw.EntryRow(title="Estimate, e.g. 1h 30m",
                                         show_apply_button=True)
        self.estimate_row.connect("apply", self._on_estimate)
        time.add(self.estimate_row)
        page.add(time)

        plan = Adw.PreferencesGroup(title="Planning")
        self.today_row = Adw.SwitchRow(title="Today")
        self._today_handler = self.today_row.connect("notify::active", self._on_today)
        plan.add(self.today_row)
        self.day_row = Adw.ActionRow(title="Planned For")
        self.calendar = Gtk.Calendar()
        self._calendar_handler = self.calendar.connect("day-selected", self._on_day)
        popover = Gtk.Popover(child=self.calendar)
        day_button = Gtk.MenuButton(icon_name="x-office-calendar-symbolic",
                                    popover=popover, valign=Gtk.Align.CENTER,
                                    tooltip_text="Choose Day")
        day_button.add_css_class("flat")
        day_button.update_property([Gtk.AccessibleProperty.LABEL], ["Choose Day"])
        self.clear_day = Gtk.Button(icon_name="edit-clear-symbolic",
                                    valign=Gtk.Align.CENTER, tooltip_text="Unplan")
        self.clear_day.add_css_class("flat")
        self.clear_day.update_property([Gtk.AccessibleProperty.LABEL], ["Unplan"])
        self.clear_day.connect("clicked", self._on_clear_day)
        self.day_row.add_suffix(self.clear_day)
        self.day_row.add_suffix(day_button)
        plan.add(self.day_row)
        self.priority_row = Adw.ComboRow(title="Priority", model=Gtk.StringList.new(
            ["None", "Low", "Medium", "High"]))
        self._priority_handler = self.priority_row.connect("notify::selected",
                                                           self._on_priority)
        plan.add(self.priority_row)
        self.project_row = Adw.ComboRow(title="Project")
        self._project_ids = []
        self._project_handler = self.project_row.connect("notify::selected",
                                                         self._on_project)
        plan.add(self.project_row)
        self.tags_row = Adw.ActionRow(title="Tags", activatable=True)
        self.tags_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        self.tags_row.connect("activated", self._on_tags)
        plan.add(self.tags_row)
        page.add(plan)

        notes = Adw.PreferencesGroup(title="Notes")
        self.notes = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=12,
                                  bottom_margin=12, left_margin=12, right_margin=12)
        self.notes.update_property([Gtk.AccessibleProperty.LABEL], ["Notes"])
        self.notes.set_size_request(-1, 120)
        self.notes.add_css_class("pensum-notes")
        frame = Gtk.Frame(child=self.notes)
        frame.add_css_class("view")
        notes.add(frame)
        self._notes_handler = self.notes.get_buffer().connect("changed", self._on_notes)
        page.add(notes)

        self.subs = Adw.PreferencesGroup(title="Subtasks")
        self.sub_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.sub_list.add_css_class("boxed-list")
        self.subs.add(self.sub_list)
        self.sub_entry = Adw.EntryRow(title="Add Subtask", show_apply_button=True)
        self.sub_entry.connect("entry-activated", self._on_add_sub)
        self.sub_entry.connect("apply", self._on_add_sub)
        page.add(self.subs)

        danger = Adw.PreferencesGroup()
        delete = Gtk.Button(label="Delete Task", halign=Gtk.Align.CENTER)
        delete.add_css_class("pill")
        delete.add_css_class("destructive-action")
        delete.connect("clicked", self._on_delete)
        danger.add(delete)
        page.add(danger)
        self.connect("hidden", lambda *_: self._save_notes())
        self.refresh(initial=True)

    @property
    def task(self):
        return self.window.ds.task(self.task_id)

    # --- showing -----------------------------------------------------------

    def refresh(self, initial=False):
        task = self.task
        if task is None:
            return
        ds = self.window.ds
        if initial or not self.title_row.has_focus():
            self.title_row.set_text(task.get("title") or "")
        self.set_title(task.get("title") or "Task")
        with self._blocked(self.done_row, self._done_handler):
            self.done_row.set_active(bool(task.get("isDone")))
        if initial:
            estimate = task.get("timeEstimate", 0)
            self.estimate_row.set_text(duration.format_short(estimate) if estimate else "")
            with self._blocked(self.notes.get_buffer(), self._notes_handler):
                self.notes.get_buffer().set_text(task.get("notes") or "")
        is_parent = bool(task.get("subTaskIds"))
        self.estimate_row.set_sensitive(not is_parent)
        self.tick()

        today = ds.today()
        with self._blocked(self.today_row, self._today_handler):
            self.today_row.set_active(ds.is_due_today(task, today))
        day = task.get("dueDay")
        if task.get("dueWithTime"):
            day = dates.day_str(task["dueWithTime"])
        self.day_row.set_subtitle(self._day_label(day, today) if day else "Not planned")
        self.clear_day.set_visible(bool(day))

        with self._blocked(self.priority_row, self._priority_handler):
            self.priority_row.set_selected(tasks.priority_level(task))
        top_level = not task.get("parentId")
        self.project_row.set_visible(top_level)
        projects = ds.projects()
        self._project_ids = [p["id"] for p in projects]
        with self._blocked(self.project_row, self._project_handler):
            self.project_row.set_model(Gtk.StringList.new(
                [p.get("title") or "Untitled" for p in projects]))
            if task.get("projectId") in self._project_ids:
                self.project_row.set_selected(self._project_ids.index(task["projectId"]))
        names = [ds.tag_entities[t].get("title") or "Untitled"
                 for t in task.get("tagIds", ()) if t in ds.tag_entities]
        self.tags_row.set_subtitle(GLib.markup_escape_text(", ".join(names) or "None"))

        self.subs.set_visible(top_level)
        self.sub_list.remove_all()
        self.sub_rows = []
        for sub in ds.subtasks(task):
            row = TaskRow(self.window, sub["id"])
            self.sub_rows.append(row)
            self.sub_list.append(row)
        self.sub_list.append(self.sub_entry)

    def focus_row(self, task_id):
        for row in self.sub_rows:
            if row.task_id == task_id:
                row.grab_focus()
                return True
        return False

    def tick(self):
        task = self.task
        if task is None:
            return
        timer = self.window.timer
        running = timer.task_id == self.task_id
        sub_running = timer.task_id in task.get("subTaskIds", ())
        extra = timer.unbooked_ms() if running or sub_running else 0
        spent = task.get("timeSpent", 0) + extra
        today = (task.get("timeSpentOnDay") or {}).get(self.window.ds.today(), 0) + extra
        self.timer_row.set_subtitle(f"{duration.format_short(spent)} in total, "
                                    f"{duration.format_short(today)} today")
        trackable = not task.get("subTaskIds") and not task.get("isDone")
        self.play.set_visible(trackable or running)
        tip = "Stop Timer" if running else "Start Timer"
        self.play.set_icon_name("media-playback-pause-symbolic" if running
                                else "media-playback-start-symbolic")
        self.play.set_tooltip_text(tip)
        self.play.update_property([Gtk.AccessibleProperty.LABEL], [tip])
        if running:
            self.play.add_css_class("suggested-action")
        else:
            self.play.remove_css_class("suggested-action")
        for row in self.sub_rows:
            if row.task_id == timer.task_id:
                row.refresh()

    @staticmethod
    def _day_label(day, today):
        if day == today:
            return "Today"
        if day == dates.shift_day(today, 1):
            return "Tomorrow"
        value = dates.parse_day(day)
        label = value.strftime("%a, %-d %b")
        if value.year != dates.parse_day(today).year:
            label += value.strftime(" %Y")
        return label + (" (overdue)" if day < today else "")

    class _blocked:
        def __init__(self, obj, handler):
            self.obj, self.handler = obj, handler

        def __enter__(self):
            self.obj.handler_block(self.handler)

        def __exit__(self, *_):
            self.obj.handler_unblock(self.handler)

    # --- changes -----------------------------------------------------------

    def _change(self):
        self.window.changed()

    def _on_title(self, row):
        title = row.get_text().strip()
        if title:
            tasks.update(self.window.ds, self.task_id, title=title)
            self._change()

    def _on_done(self, row, *_):
        tasks.set_done(self.window.ds, self.task_id, row.get_active())
        self._change()

    def _on_estimate(self, row):
        ms = duration.parse(row.get_text())
        if ms is None:
            self.window.toast("Write the estimate like 1h 30m or 45m")
            return
        tasks.set_estimate(self.window.ds, self.task_id, ms)
        row.set_text(duration.format_short(ms) if ms else "")
        self._change()

    def _on_today(self, row, *_):
        ds = self.window.ds
        tasks.schedule_day(ds, self.task_id, ds.today() if row.get_active() else None)
        self._change()

    def _on_day(self, calendar):
        value = calendar.get_date()
        day = datetime(value.get_year(), value.get_month(),
                       value.get_day_of_month()).strftime("%Y-%m-%d")
        tasks.schedule_day(self.window.ds, self.task_id, day)
        self._change()

    def _on_clear_day(self, *_):
        tasks.schedule_day(self.window.ds, self.task_id, None)
        self._change()

    def _on_priority(self, row, *_):
        tasks.set_priority(self.window.ds, self.task_id, row.get_selected())
        self._change()

    def _on_project(self, row, *_):
        index = row.get_selected()
        if 0 <= index < len(self._project_ids):
            tasks.move_to_project(self.window.ds, self.task_id, self._project_ids[index])
            self._change()

    def _on_tags(self, *_):
        from pensum.ui.tags_dialog import TagsDialog
        TagsDialog(self.window, self.task_id).present(self.window)

    def _on_notes(self, *_):
        if self._notes_source is None:
            self._notes_source = GLib.timeout_add(600, self._save_notes)

    def _save_notes(self):
        if self._notes_source is not None:
            GLib.source_remove(self._notes_source)
            self._notes_source = None
        task = self.task
        if task is None:
            return GLib.SOURCE_REMOVE
        buffer = self.notes.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if text != (task.get("notes") or ""):
            tasks.update(self.window.ds, self.task_id, notes=text)
            self._change()
        return GLib.SOURCE_REMOVE

    def _on_add_sub(self, entry):
        title = entry.get_text().strip()
        if not title:
            return
        tasks.add_subtask(self.window.ds, self.task_id, title)
        entry.set_text("")
        self._change()
        entry.grab_focus()

    def _on_delete(self, *_):
        from pensum.ui.dialogs import confirm_dialog
        task = self.task
        count = len(task.get("subTaskIds", ()))
        body = (f"Its {count} subtasks and the time tracked on them are deleted too."
                if count else "The time tracked on it is deleted too.")

        def done():
            if self.window.timer.task_id in [self.task_id] + task.get("subTaskIds", []):
                self.window.timer.stop()
            self.window.nav.pop()
            tasks.delete(self.window.ds, self.task_id)
            self.window.changed()

        confirm_dialog(self.window, f"Delete “{task.get('title') or 'Untitled'}”?",
                       body, "Delete", done)
