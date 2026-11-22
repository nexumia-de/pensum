"""The worklog (#22): time per day of a list for a week or a month, with
the week's or month's total, and the time sheet exported as CSV with the
list's export settings (pensum/store/worklog.py)."""
from datetime import date, timedelta

from gi.repository import Adw, GLib, Gtk

from pensum.duration import format_short
from pensum.i18n import _
from pensum.store import worklog


def week_range(day):
    """Monday to Sunday around a day string."""
    start = date.fromisoformat(day) - timedelta(days=date.fromisoformat(day).weekday())
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


def month_range(day):
    first = date.fromisoformat(day).replace(day=1)
    following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first.isoformat(), (following - timedelta(days=1)).isoformat()


def shift(first, span, step):
    start = date.fromisoformat(first)
    if span == "week":
        return week_range((start + timedelta(days=7 * step)).isoformat())
    month = start.month - 1 + step
    return month_range(date(start.year + month // 12, month % 12 + 1, 1).isoformat())


class WorklogPage(Adw.NavigationPage):
    def __init__(self, window, context):
        super().__init__(title=_("Worklog"), tag="worklog")
        self.window = window
        self.context = context
        self.span = "week"
        self.first, self.last = week_range(window.ds.today())
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        export = Gtk.Button(icon_name="document-save-symbolic", tooltip_text=_("Export Time Sheet"))
        export.update_property([Gtk.AccessibleProperty.LABEL], [_("Export Time Sheet")])
        export.connect("clicked", self._on_export)
        header.pack_end(export)
        toolbar.add_top_bar(header)
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        bar = Gtk.ActionBar()
        spans = Gtk.Box(css_classes=["linked"])
        week = Gtk.ToggleButton(label=_("Week"), active=True, css_classes=["pensum-bar-button"])
        month = Gtk.ToggleButton(label=_("Month"), group=week, css_classes=["pensum-bar-button"])
        week.connect("toggled", self._on_span, "week")
        month.connect("toggled", self._on_span, "month")
        spans.append(week)
        spans.append(month)
        bar.set_center_widget(spans)
        for icon, label, step, pack in (("go-previous-symbolic", _("Earlier"), -1, bar.pack_start),
                                        ("go-next-symbolic", _("Later"), 1, bar.pack_end)):
            button = Gtk.Button(icon_name=icon, tooltip_text=label,
                                css_classes=["pensum-bar-button"])
            button.update_property([Gtk.AccessibleProperty.LABEL], [label])
            button.connect("clicked", self._on_step, step)
            pack(button)
        toolbar.add_bottom_bar(bar)
        self.set_child(toolbar)
        self.group = None
        self.refresh()

    def _on_span(self, button, span):
        if button.get_active():
            self.span = span
            ranger = week_range if span == "week" else month_range
            self.first, self.last = ranger(self.first)
            self.refresh()

    def _on_step(self, _button, step):
        self.first, self.last = shift(self.first, self.span, step)
        self.refresh()

    def refresh(self):
        if self.group is not None:
            self.page.remove(self.group)
        ds = self.window.ds
        tasks = worklog.tasks_in_range(ds, self.context, self.first, self.last)
        days = worklog.per_day(tasks)
        total = sum(days.values())
        self.group = Adw.PreferencesGroup(
            title=GLib.markup_escape_text(f"{self.first} – {self.last}"),
            description=GLib.markup_escape_text(
                _("{list}: {time} on {days} days").format(
                    list=ds.context_title(self.context), time=format_short(total),
                    days=len(days))))
        for day in sorted(days, reverse=True):
            names = sorted({t.get("title") or "" for t in tasks
                            if day in t["timeSpentOnDay"] and not t.get("subTaskIds")})
            row = Adw.ActionRow(title=day, subtitle=GLib.markup_escape_text(", ".join(names)),
                                subtitle_lines=2)
            row.add_suffix(Gtk.Label(label=format_short(days[day]), css_classes=["numeric"]))
            self.group.add(row)
        if not days:
            self.group.add(Adw.ActionRow(title=_("No time tracked"), sensitive=False))
        self.page.add(self.group)

    def _on_export(self, _button):
        text = worklog.csv_text(self.window.ds, self.context, self.first, self.last)
        dialog = Gtk.FileDialog(title=_("Export Time Sheet"), modal=True,
                                initial_name=worklog.file_name(self.first, self.last))

        def chosen(dialog, result):
            try:
                file = dialog.save_finish(result)
            except GLib.Error:
                return
            try:
                with open(file.get_path(), "w", encoding="utf-8") as out:
                    out.write(text)
            except OSError as error:
                self.window.toast(_("Can't export: {reason}").format(reason=error.strerror))
                return
            self.window.toast(_("Time sheet exported"))

        dialog.save(self.window, None, chosen)
