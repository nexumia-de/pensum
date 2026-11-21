"""A list of tasks (Today, a project or a tag): the field that adds a task,
the open tasks with the list's sections, the done ones and the backlog."""
from gi.repository import Adw, Gtk

from pensum import duration
from pensum.store import dates, planning, sections, tasks, tracking
from pensum.ui import list_menu, scroll
from pensum.ui.section_group import SectionGroup
from pensum.ui.task_row import TaskRow


def boxed_list():
    listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
    listbox.add_css_class("boxed-list")
    return listbox


class TaskListPage(Adw.NavigationPage):
    def __init__(self, window, context):
        super().__init__(title="Today", tag="list")
        self.window = window
        self.context = context
        self.rows = []
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title = Adw.WindowTitle()
        header.set_title_widget(self.title)
        self.menu = Gtk.MenuButton(icon_name="view-more-symbolic",
                                   tooltip_text="List Menu")
        self.menu.update_property([Gtk.AccessibleProperty.LABEL], ["List Menu"])
        header.pack_end(self.menu)
        toolbar.add_top_bar(header)
        list_menu.install(self)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                      margin_top=12, margin_bottom=24, margin_start=12, margin_end=12)
        # The add field sits at the bottom, within thumb reach and right
        # above the on-screen keyboard (phosh-toolkit adaptive rule 10).
        add_bar = Gtk.Box(spacing=6, margin_top=6, margin_bottom=6,
                          margin_start=12, margin_end=12)
        self.entry = Gtk.Entry(hexpand=True, placeholder_text="Add Task")
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], ["Add Task"])
        self.entry.connect("activate", self._on_add)
        add_bar.append(self.entry)
        add_button = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Task")
        add_button.add_css_class("suggested-action")
        add_button.update_property([Gtk.AccessibleProperty.LABEL], ["Add Task"])
        add_button.connect("clicked", lambda *_: self._on_add(self.entry))
        add_bar.append(add_button)
        toolbar.add_bottom_bar(Adw.Clamp(child=add_bar, maximum_size=720))
        # The growing step of the journey, on Today only (#57).
        from pensum.ui.journey.today_strip import TodayStrip
        self.strip = TodayStrip(window)
        box.append(self.strip)
        overdue_header = Gtk.Box(spacing=12)
        self.overdue_title = Gtk.Label(xalign=0, hexpand=True)
        self.overdue_title.add_css_class("heading")
        overdue_header.append(self.overdue_title)
        move_all = Gtk.Button(label="Move All to Today")
        move_all.add_css_class("flat")
        move_all.connect("clicked", self._on_move_overdue)
        overdue_header.append(move_all)
        self.overdue_header = overdue_header
        box.append(overdue_header)
        self.overdue_list = boxed_list()
        box.append(self.overdue_list)
        self.empty = Adw.StatusPage(icon_name="checkbox-checked-symbolic",
                                    title="No Open Tasks")
        self.empty.add_css_class("compact")
        box.append(self.empty)
        self.open_list = boxed_list()
        box.append(self.open_list)
        # The list's sections, each with its open tasks (section_group.py).
        self.sections_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.section_groups = []
        box.append(self.sections_box)
        self.done_header = Gtk.Box(spacing=12, margin_top=6)
        self.done_title = Gtk.Label(xalign=0, hexpand=True)
        self.done_title.add_css_class("heading")
        self.done_header.append(self.done_title)
        self.finish = Gtk.Button(label="Finish Day")
        self.finish.add_css_class("flat")
        self.finish.set_tooltip_text("Move the done tasks into the archive")
        self.finish.connect("clicked", self._on_finish)
        self.done_header.append(self.finish)
        box.append(self.done_header)
        self.done_list = boxed_list()
        box.append(self.done_list)
        self.backlog = Gtk.Expander(margin_top=6)
        self.backlog_title = Gtk.Label(xalign=0)
        self.backlog_title.add_css_class("heading")
        self.backlog.set_label_widget(self.backlog_title)
        self.backlog_list = boxed_list()
        self.backlog_list.set_margin_top(12)
        self.backlog.set_child(self.backlog_list)
        box.append(self.backlog)
        clamp = Adw.Clamp(child=box, maximum_size=720)
        self.scroller = Gtk.ScrolledWindow(child=clamp,
                                           hscrollbar_policy=Gtk.PolicyType.NEVER)
        toolbar.set_content(self.scroller)
        self.set_child(toolbar)
        self.refresh()

    # --- tasks -------------------------------------------------------------

    def focus_entry(self):
        self.entry.grab_focus()

    def set_context(self, context):
        self.context = context
        self.refresh()
        self.scroller.get_vadjustment().set_value(0)

    def _on_add(self, entry):
        title = entry.get_text().strip()
        if not title:
            return
        from pensum.store import short_syntax
        ds = self.window.ds
        parsed = short_syntax.parse(ds, title)
        task = tasks.add_task(ds, parsed.title, self.context)
        short_syntax.apply(ds, task, parsed)
        entry.set_text("")
        self.window.changed()
        entry.grab_focus()

    def _on_finish(self, *_):
        from pensum.store import archive
        ds = self.window.ds
        done = [t["id"] for t in archive.finishable(ds, self.context)]
        count = sum(1 + len(ds.task(i).get("subTaskIds", ())) for i in done)
        self.window.undoable(f"{count} done tasks archived" if count != 1
                             else "1 done task archived",
                             lambda: archive.archive_tasks(ds, done))

    def _on_move_overdue(self, *_):
        ds = self.window.ds
        today = ds.today()
        for task in ds.overdue_tasks(today):
            planning.schedule_day(ds, task["id"], today)
        self.window.changed()

    def _overdue_label(self, task):
        day = self.window.ds.planned_day(task)
        project = self._context_label(task)
        label = dates.parse_day(day).strftime("%a, %-d %b") if day else ""
        return " · ".join(p for p in (label, project) if p)

    def _context_label(self, task):
        """In Today and tag lists the row also names the task's project."""
        if self.context.kind == "project":
            return None
        project = self.window.ds.project_entities.get(task.get("projectId"))
        return project.get("title") if project else None

    def refresh(self):
        ds = self.window.ds
        title = ds.context_title(self.context)
        self.set_title(title)
        today = ds.today()
        self.title.set_title(title)
        if self.context.kind == "today":
            worked = tracking.day_total(ds, today) + self.window.timer.unbooked_ms()
            self.title.set_subtitle(f"{duration.format_short(worked)} worked"
                                    if worked >= 60_000 else "")
        else:
            self.title.set_subtitle("")
        model = list_menu.model(self)
        self.menu.set_menu_model(model)
        self.menu.set_visible(model is not None)
        self.entry.set_placeholder_text("Add Task to Today" if self.context.kind == "today"
                                        else f"Add Task to {title}")
        self.strip.refresh()
        open_tasks, done_tasks = ds.list_tasks(self.context, today)
        # Rebuilding the rows must not move the list under the finger.
        adjustment = self.scroller.get_vadjustment()
        scrolled = adjustment.get_value()
        self.rows = []
        overdue = ds.overdue_tasks(today) if self.context.kind == "today" else []
        self.overdue_list.remove_all()
        for task in overdue:
            row = TaskRow(self.window, task["id"], self._overdue_label, self.context)
            self.rows.append(row)
            self.overdue_list.append(row)
        self.overdue_list.set_visible(bool(overdue))
        self.overdue_header.set_visible(bool(overdue))
        self.overdue_title.set_label(f"Overdue ({len(overdue)})")
        loose, groups = sections.group(ds, self.context, open_tasks)
        self._fill(self.open_list, loose, main=True)
        for group in self.section_groups:
            self.sections_box.remove(group)
        self.section_groups = []
        for section, items in groups:
            rows = [self._row(task, main=True) for task in items]
            group = SectionGroup(self.window, self.context, section, rows)
            self.section_groups.append(group)
            self.sections_box.append(group)
        self.sections_box.set_visible(bool(groups))
        self._fill(self.done_list, done_tasks)
        backlog = (ds.backlog_tasks(self.context.id)
                   if self.context.kind == "project" else [])
        self.backlog_list.remove_all()
        for task in backlog:
            row = TaskRow(self.window, task["id"], None, self.context)
            self.rows.append(row)
            self.backlog_list.append(row)
        self.backlog.set_visible(bool(backlog))
        self.backlog_title.set_label(f"Backlog ({len(backlog)})")
        self.empty.set_visible(not open_tasks)
        self.empty.set_description(
            "Tasks you plan for today show here." if self.context.kind == "today"
            else None)
        self.done_header.set_visible(bool(done_tasks))
        self.finish.set_label("Finish Day" if self.context.kind == "today" else "Archive Done")
        self.done_title.set_label(f"Done ({len(done_tasks)})")
        adjustment.set_value(scrolled)

    def _row(self, task, main=False):
        """`main`: an open task, which can move between the list's sections."""
        row = TaskRow(self.window, task["id"], self._context_label, self.context)
        row.in_main_list = main
        self.rows.append(row)
        return row

    def _fill(self, listbox, items, main=False):
        listbox.remove_all()
        for task in items:
            listbox.append(self._row(task, main))
        listbox.set_visible(bool(items))

    def focus_row(self, task_id):
        for row in self.rows:
            if row.task_id == task_id:
                scroll.focus_in_place(row)
                return True
        return False

    def tick(self):
        running = self.window.timer.task_id
        for row in self.rows:
            task = row.task
            if task and (row.task_id == running or running in task.get("subTaskIds", ())):
                row.refresh()
        if self.context.kind == "today" and running:
            ds = self.window.ds
            worked = tracking.day_total(ds, ds.today()) + self.window.timer.unbooked_ms()
            if worked >= 60_000:
                self.title.set_subtitle(f"{duration.format_short(worked)} worked")
