"""Correct a task's time spent: one field per day it was worked on, plus
today and any other day chosen in the calendar."""
from datetime import datetime

from gi.repository import Adw, Gtk

from pensum import duration
from pensum.store import dates, tracking


class TimeDialog(Adw.Dialog):
    def __init__(self, window, task_id):
        super().__init__(title="Time Spent", content_width=360, content_height=520)
        self.window = window
        self.task_id = task_id
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.calendar = Gtk.Calendar()
        self.calendar.connect("day-selected", self._on_day)
        add = Gtk.MenuButton(icon_name="list-add-symbolic", tooltip_text="Add Day",
                             popover=Gtk.Popover(child=self.calendar))
        add.update_property([Gtk.AccessibleProperty.LABEL], ["Add Day"])
        header.pack_start(add)
        toolbar.add_top_bar(header)
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.set_child(toolbar)
        self.group = None
        self.extra_days = set()
        self._fill()

    def _fill(self):
        if self.group is not None:
            self.page.remove(self.group)
        ds = self.window.ds
        task = ds.task(self.task_id)
        per_day = task.get("timeSpentOnDay") or {}
        days = sorted(set(per_day) | {ds.today()} | self.extra_days, reverse=True)
        self.group = Adw.PreferencesGroup(
            description="Write the time like 1h 30m; empty or 0 removes the day.")
        for day in days:
            label = dates.parse_day(day).strftime("%a, %-d %b %Y")
            if day == ds.today():
                label = "Today"
            row = Adw.EntryRow(title=label, show_apply_button=True)
            ms = per_day.get(day, 0)
            row.set_text(duration.format_short(ms) if ms else "")
            row.connect("apply", self._on_apply, day)
            self.group.add(row)
        self.page.add(self.group)

    def _on_apply(self, row, day):
        ms = duration.parse(row.get_text())
        if ms is None:
            self.window.toast("Write the time like 1h 30m or 45m")
            return
        tracking.set_time_on_day(self.window.ds, self.task_id, day, ms)
        self.window.changed()

    def _on_day(self, calendar):
        value = calendar.get_date()
        day = datetime(value.get_year(), value.get_month(),
                       value.get_day_of_month()).strftime("%Y-%m-%d")
        self.extra_days.add(day)
        self._fill()
