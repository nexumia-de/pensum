"""One task: title, done, timer and estimate, the day it is planned for,
project and tags, notes, subtasks, and deleting it."""
from datetime import datetime

from gi.repository import Adw, GLib, Gtk, Pango

from pensum import duration
from pensum.i18n import _
from pensum.store import dates, planning, reminders, tasks
from pensum.ui import scroll
from pensum.ui.notes_box import NotesBox
from pensum.ui.task_row import TaskRow


class TaskPage(Adw.NavigationPage):
    def __init__(self, window, task_id):
        super().__init__(title=_("Task"), tag=f"task-{task_id}")
        self.window = window
        self.task_id = task_id
        self.sub_rows = []
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        # Focus mode for this task (#19).
        focus = Gtk.Button(icon_name="alarm-symbolic", tooltip_text=_("Focus"))
        focus.update_property([Gtk.AccessibleProperty.LABEL], [_("Focus")])
        focus.connect("clicked", lambda *_: window.show_focus(self.task_id))
        header.pack_end(focus)
        toolbar.add_top_bar(header)
        # The two things done most with a task, within thumb reach
        # (phosh-toolkit adaptive rule 10).
        actions = Gtk.Box(spacing=12, homogeneous=True, margin_top=6, margin_bottom=6,
                          margin_start=12, margin_end=12)
        # Labels may shorten: two pill buttons must fit 360 px with any font.
        self.done_label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END)
        self.done_button = Gtk.ToggleButton(child=self.done_label)
        self.done_button.add_css_class("pensum-bar-button")
        self._done_handler = self.done_button.connect("toggled", self._on_done)
        actions.append(self.done_button)
        self.play_label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END)
        self.play = Gtk.Button(child=self.play_label)
        self.play.add_css_class("pensum-bar-button")
        self.play.connect("clicked", lambda *_: window.timer.toggle(self.task_id))
        actions.append(self.play)
        toolbar.add_bottom_bar(Adw.Clamp(child=actions, maximum_size=480))
        page = Adw.PreferencesPage()
        toolbar.set_content(page)
        self.set_child(toolbar)

        main = Adw.PreferencesGroup()
        self.title_row = Adw.EntryRow(title=_("Title"), show_apply_button=True)
        self.title_row.connect("apply", self._on_title)
        main.add(self.title_row)
        page.add(main)

        time = Adw.PreferencesGroup(title=_("Time"))
        self.timer_row = Adw.ActionRow(title=_("Time Spent"), activatable=True)
        self.timer_row.connect("activated", self._on_edit_time)
        self.timer_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        time.add(self.timer_row)
        self.estimate_row = Adw.EntryRow(title=_("Estimate (like 1h 30m)"),
                                         show_apply_button=True)
        self.estimate_row.connect("apply", self._on_estimate)
        time.add(self.estimate_row)
        page.add(time)

        plan = Adw.PreferencesGroup(title=_("Planning"))
        self.today_row = Adw.SwitchRow(title=_("Today"))
        self._today_handler = self.today_row.connect("notify::active", self._on_today)
        plan.add(self.today_row)
        self.day_row = Adw.ActionRow(title=_("Planned For"))
        self.calendar = Gtk.Calendar()
        self._calendar_handler = self.calendar.connect("day-selected", self._on_day)
        popover = Gtk.Popover(child=self.calendar)
        day_button = Gtk.MenuButton(icon_name="x-office-calendar-symbolic",
                                    popover=popover, valign=Gtk.Align.CENTER,
                                    tooltip_text=_("Choose Day"))
        day_button.add_css_class("flat")
        day_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Choose Day")])
        self.clear_day = Gtk.Button(icon_name="edit-clear-symbolic",
                                    valign=Gtk.Align.CENTER, tooltip_text=_("Unplan"))
        self.clear_day.add_css_class("flat")
        self.clear_day.update_property([Gtk.AccessibleProperty.LABEL], [_("Unplan")])
        self.clear_day.connect("clicked", self._on_clear_day)
        self.day_row.add_suffix(self.clear_day)
        self.day_row.add_suffix(day_button)
        plan.add(self.day_row)
        self.time_row = Adw.ActionRow(title=_("Time"), activatable=True)
        self.time_row.connect("activated", self._on_time)
        self.clear_time = Gtk.Button(icon_name="edit-clear-symbolic",
                                     valign=Gtk.Align.CENTER, tooltip_text=_("Remove Time"))
        self.clear_time.add_css_class("flat")
        self.clear_time.update_property([Gtk.AccessibleProperty.LABEL], [_("Remove Time")])
        self.clear_time.connect("clicked", self._on_clear_time)
        self.time_row.add_suffix(self.clear_time)
        self.time_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        plan.add(self.time_row)
        # A reminder is a lead before the time (pensum.store.reminders).
        self.remind_row = Adw.ComboRow(title=_("Reminder"), model=Gtk.StringList.new(
            reminders.option_labels()))
        self._remind_handler = self.remind_row.connect("notify::selected", self._on_remind)
        plan.add(self.remind_row)
        self.deadline_row = Adw.ActionRow(title=_("Deadline"))
        self.deadline_calendar = Gtk.Calendar()
        self.deadline_calendar.connect("day-selected", self._on_deadline)
        deadline_button = Gtk.MenuButton(icon_name="x-office-calendar-symbolic",
                                         popover=Gtk.Popover(child=self.deadline_calendar),
                                         valign=Gtk.Align.CENTER,
                                         tooltip_text=_("Choose Deadline"))
        deadline_button.add_css_class("flat")
        deadline_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Choose Deadline")])
        self.clear_deadline = Gtk.Button(icon_name="edit-clear-symbolic",
                                         valign=Gtk.Align.CENTER,
                                         tooltip_text=_("Remove Deadline"))
        self.clear_deadline.add_css_class("flat")
        self.clear_deadline.update_property([Gtk.AccessibleProperty.LABEL],
                                            [_("Remove Deadline")])
        self.clear_deadline.connect("clicked", self._on_clear_deadline)
        self.deadline_row.add_suffix(self.clear_deadline)
        self.deadline_row.add_suffix(deadline_button)
        plan.add(self.deadline_row)
        self.priority_row = Adw.ComboRow(title=_("Priority"), model=Gtk.StringList.new(
            [_("None"), _("Low"), _("Medium"), _("High")]))
        self._priority_handler = self.priority_row.connect("notify::selected",
                                                           self._on_priority)
        plan.add(self.priority_row)
        self.project_row = Adw.ComboRow(title=_("Project"))
        self._project_ids = []
        self._project_titles = None
        self._project_handler = self.project_row.connect("notify::selected",
                                                         self._on_project)
        plan.add(self.project_row)
        self.tags_row = Adw.ActionRow(title=_("Tags"), activatable=True)
        self.tags_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        self.tags_row.connect("activated", self._on_tags)
        plan.add(self.tags_row)
        self.repeat_row = Adw.ActionRow(title=_("Repeat"), activatable=True)
        self.repeat_row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        self.repeat_row.connect("activated", self._on_repeat)
        plan.add(self.repeat_row)
        page.add(plan)

        self.notes = NotesBox(window, task_id)
        page.add(self.notes)

        self.subs = Adw.PreferencesGroup(title=_("Subtasks"))
        self.sub_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.sub_list.add_css_class("boxed-list")
        self.subs.add(self.sub_list)
        self.sub_entry = Adw.EntryRow(title=_("Add Subtask"), show_apply_button=True)
        self.sub_entry.connect("entry-activated", self._on_add_sub)
        self.sub_entry.connect("apply", self._on_add_sub)
        page.add(self.subs)

        danger = Adw.PreferencesGroup()
        delete = Gtk.Button(label=_("Delete Task"), halign=Gtk.Align.CENTER)
        delete.add_css_class("pill")
        delete.add_css_class("destructive-action")
        delete.connect("clicked", self._on_delete)
        danger.add(delete)
        page.add(danger)
        self.connect("hidden", lambda *_: self.notes.save())
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
        self.set_title(task.get("title") or _("Task"))
        done = bool(task.get("isDone"))
        with self._blocked(self.done_button, self._done_handler):
            self.done_button.set_active(done)
        self.done_label.set_label(_("Done") if done else _("Mark as Done"))

        if initial:
            estimate = task.get("timeEstimate", 0)
            self.estimate_row.set_text(duration.format_short(estimate) if estimate else "")
            self.notes.load()
        else:
            self.notes.sync()
        is_parent = bool(task.get("subTaskIds"))
        self.estimate_row.set_sensitive(not is_parent)
        self.tick()
        self.repeat_row.set_visible(not task.get("parentId"))
        self.repeat_row.set_subtitle(self._repeat_label(ds, task))

        today = ds.today()
        with self._blocked(self.today_row, self._today_handler):
            self.today_row.set_active(ds.is_due_today(task, today))
        day = task.get("dueDay")
        if task.get("dueWithTime"):
            day = dates.day_str(task["dueWithTime"])
        self.day_row.set_subtitle(self._day_label(day, today) if day else _("Not planned"))
        self.clear_day.set_visible(bool(day))
        due = task.get("dueWithTime")
        self.time_row.set_subtitle(datetime.fromtimestamp(due / 1000).strftime("%H:%M")
                                   if due else _("No time"))
        self.clear_time.set_visible(bool(due))
        option = reminders.option_of(task)
        keys = [key for key, _ in reminders.OPTIONS]
        with self._blocked(self.remind_row, self._remind_handler):
            self.remind_row.set_selected(keys.index(option) if option in keys else 0)
        self.remind_row.set_sensitive(bool(task.get("dueWithTime")))
        remind = task.get("remindAt")
        self.remind_row.set_subtitle(
            _("Set a time first") if not task.get("dueWithTime") else
            _("At {time}").format(
                time=datetime.fromtimestamp(remind / 1000).strftime("%H:%M"))
            if option == "custom" else "")

        deadline = tasks.deadline_day(ds, task)
        self.deadline_row.set_subtitle(self._day_label(deadline, today) if deadline
                                       else _("None"))
        self.clear_deadline.set_visible(bool(deadline))
        with self._blocked(self.priority_row, self._priority_handler):
            self.priority_row.set_selected(tasks.priority_level(task))
        top_level = not task.get("parentId")
        self.project_row.set_visible(top_level)
        projects = ds.projects()
        titles = [p.get("title") or _("Untitled") for p in projects]
        with self._blocked(self.project_row, self._project_handler):
            # Replacing the model while the row is still handling a
            # selection crashes GTK, so only replace it when it changed.
            if titles != self._project_titles:
                self.project_row.set_model(Gtk.StringList.new(titles))
                self._project_titles = titles
            self._project_ids = [p["id"] for p in projects]
            if task.get("projectId") in self._project_ids:
                self.project_row.set_selected(self._project_ids.index(task["projectId"]))
        names = [ds.tag_entities[t].get("title") or _("Untitled")
                 for t in task.get("tagIds", ()) if t in ds.tag_entities]
        self.tags_row.set_subtitle(GLib.markup_escape_text(", ".join(names) or _("None")))

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
                scroll.focus_in_place(row)
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
        self.timer_row.set_subtitle(_("{total} in total, {today} today").format(
            total=duration.format_short(spent), today=duration.format_short(today)))
        trackable = not task.get("subTaskIds") and not task.get("isDone")
        self.play.set_visible(trackable or running)
        self.play_label.set_label(_("Stop Timer") if running else _("Start Timer"))
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
            return _("Today")
        if day == dates.shift_day(today, 1):
            return _("Tomorrow")
        value = dates.parse_day(day)
        label = value.strftime("%a, %-d %b")
        if value.year != dates.parse_day(today).year:
            label += value.strftime(" %Y")
        return _("{day} (overdue)").format(day=label) if day < today else label

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

    def _on_edit_time(self, *args):
        task = self.task
        if task is None or task.get("subTaskIds"):
            self.window.toast(_("A parent's time is the sum of its subtasks'"))
            return
        from pensum.ui.time_dialog import TimeDialog
        TimeDialog(self.window, self.task_id).present(self.window)

    def _on_estimate(self, row):
        ms = duration.parse(row.get_text())
        if ms is None:
            self.window.toast(_("Write the estimate like 1h 30m or 45m"))
            return
        tasks.set_estimate(self.window.ds, self.task_id, ms)
        row.set_text(duration.format_short(ms) if ms else "")
        self._change()

    def _on_today(self, row, *_):
        ds = self.window.ds
        planning.schedule_day(ds, self.task_id, ds.today() if row.get_active() else None)
        self._change()

    def _on_day(self, calendar):
        value = calendar.get_date()
        day = datetime(value.get_year(), value.get_month(),
                       value.get_day_of_month()).strftime("%Y-%m-%d")
        planning.schedule_day(self.window.ds, self.task_id, day)
        self._change()

    def _on_time(self, *_):
        """The picker starts at the task's time, else at the next full hour."""
        from pensum.ui.time_picker import TimePicker
        due = (self.task or {}).get("dueWithTime")
        start = datetime.fromtimestamp(due / 1000) if due else datetime.now()
        hours, minutes = ((start.hour, start.minute) if due
                          else ((start.hour + 1) % 24, 0))
        TimePicker(hours, minutes, self.set_time).present(self.window)

    def set_time(self, hours, minutes):
        """Plan the task at a time on its planned day, else today."""
        ds = self.window.ds
        day = ds.planned_day(self.task) or ds.today()
        planning.schedule_time(ds, self.task_id, day, hours, minutes)
        self._change()

    def _on_clear_time(self, *_):
        planning.clear_time(self.window.ds, self.task_id)
        self._change()

    def _on_remind(self, row, *_):
        option = reminders.OPTIONS[row.get_selected()][0]
        if option != reminders.option_of(self.task):
            reminders.set_option(self.window.ds, self.task_id, option)
            self._change()

    @staticmethod
    def _repeat_label(ds, task):
        from pensum.store.repeat import rules
        from pensum.ui.repeat_page import describe
        cfg = rules.rule_of(ds, task)
        return describe(cfg) if cfg else _("Never")

    def _on_repeat(self, *_):
        from pensum.ui.repeat_page import RepeatPage
        self.window.nav.push(RepeatPage(self.window, self.task_id))

    def _on_clear_day(self, *_):
        planning.schedule_day(self.window.ds, self.task_id, None)
        self._change()

    def _on_deadline(self, calendar):
        value = calendar.get_date()
        day = datetime(value.get_year(), value.get_month(),
                       value.get_day_of_month()).strftime("%Y-%m-%d")
        tasks.set_deadline(self.window.ds, self.task_id, day)
        self._change()

    def _on_clear_deadline(self, *_):
        tasks.set_deadline(self.window.ds, self.task_id, None)
        self._change()

    def _on_priority(self, row, *_):
        tasks.set_priority(self.window.ds, self.task_id, row.get_selected())
        self._change()

    def _on_project(self, row, *_):
        index = row.get_selected()
        if 0 <= index < len(self._project_ids):
            project_id = self._project_ids[index]
            # Redraw after the row has finished its own signal handling.
            GLib.idle_add(self._move_to_project, project_id)

    def _move_to_project(self, project_id):
        if self.task is not None:
            tasks.move_to_project(self.window.ds, self.task_id, project_id)
            self._change()
        return GLib.SOURCE_REMOVE

    def _on_tags(self, *_):
        from pensum.ui.tags_dialog import TagsDialog
        TagsDialog(self.window, self.task_id).present(self.window)

    def _on_add_sub(self, entry):
        title = entry.get_text().strip()
        if not title:
            return
        tasks.add_subtask(self.window.ds, self.task_id, title)
        entry.set_text("")
        self._change()
        entry.grab_focus()

    def _on_delete(self, *args):
        """Delete at once and offer Undo, instead of asking first (GNOME
        HIG: undo is better than a confirmation dialog)."""
        task = self.task
        if task is None:
            return
        if self.window.timer.task_id in [self.task_id] + task.get("subTaskIds", []):
            self.window.timer.stop()
        title = task.get("title") or _("Untitled")
        self.window.nav.pop()
        self.window.undoable(_("“{title}” deleted").format(title=title),
                             lambda: tasks.delete(self.window.ds, self.task_id))
