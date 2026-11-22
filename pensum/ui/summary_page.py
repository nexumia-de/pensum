"""The daily summary (#23): what was done today and how long, breaks and
focus sessions, and Super Productivity's evaluation of the day (impact
1-4, energy 1-3, a reflection) in the slice `metric`
(pensum/store/metric.py). Opened from the main menu and after Finish
Day."""
from gi.repository import Adw, GLib, Gtk

from pensum.duration import format_short
from pensum.i18n import _
from pensum.store import breaks, metric, tracking


def impact_names():
    return [_("No progress"), _("Some progress"), _("Good progress"), _("Big impact")]


def energy_names():
    return [_("Exhausted"), _("OK"), _("Good")]


class SummaryPage(Adw.NavigationPage):
    def __init__(self, window, day=None):
        super().__init__(title=_("Daily Summary"), tag="summary")
        self.window = window
        self.day = day or window.ds.today()
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.set_child(toolbar)
        self.done = Adw.PreferencesGroup(title=_("Done Today"))
        self.page.add(self.done)
        self._done_rows = []
        evaluation = Adw.PreferencesGroup(title=_("How Was Your Day?"))
        self.impact = self._choice(evaluation, _("Impact of your work"), impact_names(),
                                   metric.set_impact)
        self.energy = self._choice(evaluation, _("Your energy"), energy_names(), metric.set_energy)
        self.reflection = Adw.EntryRow(title=_("A thought about today"))
        self.reflection.set_text(metric.reflection(window.ds, self.day))
        self.reflection.connect("apply", self._on_reflection)
        self.reflection.set_show_apply_button(True)
        evaluation.add(self.reflection)
        self.page.add(evaluation)
        self.refresh()

    def _choice(self, group, title, names, setter):
        row = Adw.ComboRow(title=title, model=Gtk.StringList.new(["–"] + names))
        row.connect("notify::selected", self._on_choice, setter)
        group.add(row)
        return row

    def refresh(self):
        ds = self.window.ds
        for row in self._done_rows:
            self.done.remove(row)
        self._done_rows = []
        worked = [t for t in ds.tasks.values() if not t.get("parentId")
                  and (tracking.time_on_day(ds, t, self.day) or (
                      t.get("isDone") and ds.today(t.get("doneOn") or 0) == self.day))]
        total = tracking.day_total(ds, self.day)
        count, pause = breaks.breaks_on(ds, self.day)
        sessions = metric.for_day(ds, self.day)["focusSessions"]
        self.done.set_description(GLib.markup_escape_text(
            _("{time} worked, {done} tasks done, {breaks} breaks ({pause}), "
              "{sessions} focus sessions").format(
                time=format_short(total), done=sum(1 for t in worked if t.get("isDone")),
                breaks=count, pause=format_short(pause), sessions=len(sessions))))
        for task in sorted(worked, key=lambda t: -tracking.time_on_day(ds, t, self.day)):
            row = Adw.ActionRow(title=GLib.markup_escape_text(task.get("title") or ""))
            if task.get("isDone"):
                row.add_prefix(Gtk.Image(icon_name="object-select-symbolic",
                                         tooltip_text=_("Done")))
            row.add_suffix(Gtk.Label(label=format_short(tracking.time_on_day(ds, task, self.day)),
                                     css_classes=["numeric"]))
            self.done.add(row)
            self._done_rows.append(row)
        found = metric.for_day(ds, self.day)
        self._set_quietly(self.impact, found.get("impactOfWork") or 0)
        self._set_quietly(self.energy, found.get("energyCheckin") or 0)

    def _set_quietly(self, row, value):
        if row.get_selected() != value:
            row.set_selected(value)

    def _on_choice(self, row, _param, setter):
        value = row.get_selected()
        found = metric.for_day(self.window.ds, self.day)
        current = found.get("impactOfWork" if row is self.impact else "energyCheckin") or 0
        if value and value != current:
            setter(self.window.ds, self.day, value)
            self.window.changed()

    def _on_reflection(self, row):
        if metric.set_reflection(self.window.ds, self.day, row.get_text()):
            self.window.changed()
