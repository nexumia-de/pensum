"""The planner (#26): today and the six days after it with their open
tasks and the estimate left per day; a task moves to another day from
its menu (pensum/store/planner.py). Tapping a task opens it."""
from datetime import date

from gi.repository import Adw, Gio, GLib, Gtk

from pensum.duration import format_short
from pensum.i18n import _
from pensum.store import planner


def day_title(day, today):
    if day == today:
        return _("Today")
    weekdays = [_("Monday"), _("Tuesday"), _("Wednesday"), _("Thursday"), _("Friday"),
                _("Saturday"), _("Sunday")]
    found = date.fromisoformat(day)
    return f"{weekdays[found.weekday()]}, {found.day}.{found.month}."


class PlannerPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title=_("Planner"), tag="planner")
        self.window = window
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.set_child(toolbar)
        self.groups = []
        action = Gio.SimpleAction.new("move-to-day", GLib.VariantType.new("(ss)"))
        action.connect("activate", self._on_move)
        group = Gio.SimpleActionGroup()
        group.add_action(action)
        self.insert_action_group("planner", group)
        self.refresh()

    def refresh(self):
        for group in self.groups:
            self.page.remove(group)
        self.groups = []
        ds = self.window.ds
        today = ds.today()
        found = planner.days(ds, today)
        for day, tasks, estimate in found:
            group = Adw.PreferencesGroup(
                title=GLib.markup_escape_text(day_title(day, today)),
                description=(_("{time} estimated").format(time=format_short(estimate))
                             if estimate else None))
            for task in tasks:
                group.add(self._row(task, day, found))
            if not tasks:
                group.add(Adw.ActionRow(title=_("Nothing planned"), sensitive=False))
            self.page.add(group)
            self.groups.append(group)

    def _row(self, task, day, found):
        row = Adw.ActionRow(title=GLib.markup_escape_text(task.get("title") or ""),
                            activatable=True)
        left = planner.left_estimate(task)
        if left:
            row.set_subtitle(format_short(left))
        menu = Gio.Menu()
        today = found[0][0]
        for other, _tasks, _estimate in found:
            if other != day:
                menu.append(day_title(other, today),
                            f"planner.move-to-day(('{task['id']}', '{other}'))")
        button = Gtk.MenuButton(icon_name="x-office-calendar-symbolic", menu_model=menu,
                                valign=Gtk.Align.CENTER, css_classes=["flat"],
                                tooltip_text=_("Move to Another Day"))
        button.update_property([Gtk.AccessibleProperty.LABEL], [_("Move to Another Day")])
        row.add_suffix(button)
        row.connect("activated", lambda _r: self.window.show_task(task["id"]))
        return row

    def _on_move(self, _action, param):
        task_id, day = param.unpack()
        if planner.move(self.window.ds, task_id, day):
            self.window.changed()
