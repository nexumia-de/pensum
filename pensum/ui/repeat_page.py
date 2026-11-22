"""How a task repeats: choosing a schedule makes it recurring, the rule
can be paused, changed or removed (with Undo). Pushed from the task
page, so a swipe goes back."""
from datetime import datetime

from gi.repository import Adw, GLib, Gtk

from pensum.i18n import N_, _
from pensum.store import dates, reminders
from pensum.store.repeat import instances, rules, schedule

DAY_NAMES = (N_("Monday"), N_("Tuesday"), N_("Wednesday"), N_("Thursday"), N_("Friday"),
             N_("Saturday"), N_("Sunday"))
SHORT_DAY_NAMES = (N_("Mon"), N_("Tue"), N_("Wed"), N_("Thu"), N_("Fri"), N_("Sat"),
                   N_("Sun"))
EVERY_WEEKDAY = (N_("Every Monday"), N_("Every Tuesday"), N_("Every Wednesday"),
                 N_("Every Thursday"), N_("Every Friday"), N_("Every Saturday"),
                 N_("Every Sunday"))
UNITS = (("DAILY", N_("days")), ("WEEKLY", N_("weeks")), ("MONTHLY", N_("months")),
         ("YEARLY", N_("years")))
EVERY_ONE = {"DAILY": N_("Every day"), "WEEKLY": N_("Every week"),
             "MONTHLY": N_("Every month"), "YEARLY": N_("Every year")}
EVERY_MANY = {"DAILY": N_("Every {n} days"), "WEEKLY": N_("Every {n} weeks"),
              "MONTHLY": N_("Every {n} months"), "YEARLY": N_("Every {n} years")}


def _ordinal(n):
    """3 → "3rd" (German "3.")."""
    if 10 <= n % 100 <= 20:
        return _("{n}th").format(n=n)
    return {1: _("{n}st"), 2: _("{n}nd"), 3: _("{n}rd")}.get(n % 10, _("{n}th")).format(n=n)


def preset_labels(start):
    """(preset, label) pairs for a series that starts on `start`."""
    day = dates.parse_day(start)
    return [("DAILY", _("Every day")),
            ("MONDAY_TO_FRIDAY", _("Monday to Friday")),
            ("WEEKLY_CURRENT_WEEKDAY", _(EVERY_WEEKDAY[day.weekday()])),
            ("MONTHLY_CURRENT_DATE",
             _("Every month on the {day}").format(day=_ordinal(day.day))),
            ("YEARLY_CURRENT_DATE",
             _("Every year on {date}").format(date=day.strftime("%-d %B"))),
            ("CUSTOM", _("Custom"))]


def describe(cfg):
    """A short sentence for a rule, for the task page."""
    every = cfg.get("repeatEvery") or 1
    cycle = cfg.get("repeatCycle")
    if cycle == "WEEKLY":
        days = [i for i, key in enumerate(schedule.WEEKDAYS) if cfg.get(key)]
        names = _("Monday to Friday") if days == [0, 1, 2, 3, 4] else ", ".join(
            _(SHORT_DAY_NAMES[i]) for i in days) or _("no day")
        text = names if every == 1 else _("Every {n} weeks: {days}").format(
            n=every, days=names)
    else:
        cycle = cycle if cycle in EVERY_ONE else "DAILY"
        text = _(EVERY_ONE[cycle]) if every == 1 else _(EVERY_MANY[cycle]).format(n=every)
        if cycle == "MONTHLY" and cfg.get("monthlyLastDay"):
            text = _("{rule} on the last day").format(rule=text)
    return _("{rule} (paused)").format(rule=text) if cfg.get("isPaused") else text


class RepeatPage(Adw.NavigationPage):
    def __init__(self, window, task_id):
        super().__init__(title=_("Repeat"), tag=f"repeat-{task_id}")
        self.window = window
        self.task_id = task_id
        self._updating = False
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        page = Adw.PreferencesPage()
        toolbar.set_content(page)
        self.set_child(toolbar)

        group = Adw.PreferencesGroup(
            description=_("A repeating task comes back on its days, the way "
                          "Super Productivity creates it."))
        self.schedule_row = Adw.ComboRow(title=_("Repeat"))
        self.schedule_row.connect("notify::selected", self._on_schedule)
        group.add(self.schedule_row)
        page.add(group)

        self.custom = Adw.PreferencesGroup(title=_("Custom"))
        self.every_row = Adw.SpinRow.new_with_range(1, 99, 1)
        self.every_row.set_title(_("Every"))
        self.every_row.connect("notify::value", self._on_custom)
        self.custom.add(self.every_row)
        self.unit_row = Adw.ComboRow(title=_("Unit"), model=Gtk.StringList.new(
            [_(label) for _key, label in UNITS]))
        self.unit_row.connect("notify::selected", self._on_custom)
        self.custom.add(self.unit_row)
        self.day_buttons = []
        days = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=7,
                           min_children_per_line=4, column_spacing=6, row_spacing=6,
                           margin_top=12, homogeneous=True)
        for name, short in zip(DAY_NAMES, SHORT_DAY_NAMES):
            name, short = _(name), _(short)
            button = Gtk.ToggleButton(label=short[:2], tooltip_text=name)
            button.set_size_request(44, 44)
            button.update_property([Gtk.AccessibleProperty.LABEL], [name])
            button.connect("toggled", self._on_custom)
            self.day_buttons.append(button)
            days.append(button)
        self.days_box = days
        self.custom.add(days)
        page.add(self.custom)

        self.rule_group = Adw.PreferencesGroup()
        self.pause_row = Adw.SwitchRow(title=_("Paused"),
                                       subtitle=_("No new tasks while paused"))
        self.pause_row.connect("notify::active", self._on_pause)
        self.rule_group.add(self.pause_row)
        # The time of day and the reminder every new task of the rule gets.
        self.time_row = Adw.EntryRow(title=_("Time (like 14:30)"), show_apply_button=True)
        self.time_row.connect("apply", self._on_time)
        self.rule_group.add(self.time_row)
        self.remind_row = Adw.ComboRow(title=_("Reminder"), model=Gtk.StringList.new(
            reminders.option_labels()))
        self.remind_row.connect("notify::selected", self._on_remind)
        self.rule_group.add(self.remind_row)
        page.add(self.rule_group)

        stop = Adw.PreferencesGroup()
        self.stop_button = Gtk.Button(label=_("Stop Repeating"), halign=Gtk.Align.CENTER)
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.add_css_class("pill")
        self.stop_button.connect("clicked", self._on_stop)
        stop.add(self.stop_button)
        page.add(stop)
        self.stop_group = stop
        self.refresh()

    # --- state ---------------------------------------------------------

    @property
    def task(self):
        return self.window.ds.task(self.task_id)

    def _rule(self):
        task = self.task
        return rules.rule_of(self.window.ds, task) if task else None

    def _start(self):
        task, ds = self.task, self.window.ds
        cfg = self._rule()
        return (cfg or {}).get("startDate") or ds.planned_day(task) or ds.today()

    def refresh(self):
        if not self.task:
            return
        self._updating = True
        cfg = self._rule()
        self.presets = preset_labels(self._start())
        labels = [_("Never")] + [label for _, label in self.presets]
        if labels != getattr(self, "_labels", None):
            self._labels = labels
            self.schedule_row.set_model(Gtk.StringList.new(labels))
        selected = 0
        if cfg:
            keys = [p for p, _ in self.presets]
            setting = cfg.get("quickSetting")
            selected = keys.index(setting) + 1 if setting in keys else len(labels) - 1
        self.schedule_row.set_selected(selected)
        custom = bool(cfg) and self.schedule_row.get_selected() == len(labels) - 1
        self.custom.set_visible(custom)
        if cfg:
            self.every_row.set_value(cfg.get("repeatEvery") or 1)
            cycles = [c for c, _ in UNITS]
            self.unit_row.set_selected(cycles.index(cfg.get("repeatCycle"))
                                       if cfg.get("repeatCycle") in cycles else 0)
            for button, key in zip(self.day_buttons, schedule.WEEKDAYS):
                button.set_active(bool(cfg.get(key)))
            self.pause_row.set_active(bool(cfg.get("isPaused")))
            start, option = reminders.rule_time(cfg)
            if not self.time_row.has_focus():
                self.time_row.set_text(start or "")
            keys = [key for key, _ in reminders.OPTIONS]
            self.remind_row.set_selected(keys.index(option) if option in keys else 0)
            self.remind_row.set_sensitive(bool(start))
            self.remind_row.set_subtitle("" if start else _("Set a time first"))
        self.days_box.set_visible(self.unit_row.get_selected() == 1)
        self.rule_group.set_visible(bool(cfg))
        self.stop_group.set_visible(bool(cfg))
        self._updating = False

    # --- changes -------------------------------------------------------

    def _changed(self):
        # Redraw after the widget's own signal: changing a combo row's
        # list from inside its notify::selected blocks GTK.
        GLib.idle_add(lambda: self.window.changed() and False)

    def _fields(self, preset):
        weekdays = [k for b, k in zip(self.day_buttons, schedule.WEEKDAYS) if b.get_active()]
        cycle = UNITS[self.unit_row.get_selected()][0]
        if preset == "CUSTOM" and cycle == "WEEKLY" and not weekdays:
            weekdays = [schedule.WEEKDAYS[dates.parse_day(self._start()).weekday()]]
        return rules.schedule_fields(preset, self._start(), every=int(self.every_row.get_value()),
                                     cycle=cycle, weekdays=weekdays)

    def _on_schedule(self, row, _param):
        if self._updating:
            return
        index = row.get_selected()
        cfg = self._rule()
        if index == 0:
            if cfg:
                self._on_stop()
            return
        preset = self.presets[index - 1][0]
        ds = self.window.ds
        if cfg:
            rules.update(ds, cfg["id"], **self._fields(preset))
        else:
            rules.make_recurring(ds, self.task_id, self._fields(preset))
            instances.create_due(ds)
        self._changed()

    def _on_custom(self, *_):
        if self._updating:
            return
        self.days_box.set_visible(self.unit_row.get_selected() == 1)
        cfg = self._rule()
        if cfg:
            rules.update(self.window.ds, cfg["id"], **self._fields("CUSTOM"))
            self._changed()

    def _set_time(self, start, option):
        ds = self.window.ds
        reminders.set_rule_time(ds, self._rule()["id"], start, option, ds.today())
        self._changed()

    def _on_time(self, row):
        cfg = self._rule()
        if not cfg:
            return
        text = row.get_text().strip().replace(".", ":")
        if text:
            try:
                text = datetime.strptime(text, "%H:%M").strftime("%H:%M")
            except ValueError:
                self.window.toast(_("Write the time like 14:30"))
                return
        self._set_time(text, reminders.rule_time(cfg)[1])

    def _on_remind(self, row, _param):
        cfg = self._rule()
        if self._updating or not cfg:
            return
        start, option = reminders.rule_time(cfg)
        chosen = reminders.OPTIONS[row.get_selected()][0]
        if start and chosen != option:
            self._set_time(start, chosen)

    def _on_pause(self, row, _param):
        cfg = self._rule()
        if self._updating or not cfg:
            return
        rules.set_paused(self.window.ds, cfg["id"], row.get_active())
        self._changed()

    def _on_stop(self, *args):
        cfg = self._rule()
        if not cfg:
            return
        ds = self.window.ds
        undo = rules.snapshot(ds, cfg["id"])
        rules.delete(ds, cfg["id"])
        self._changed()

        def restore(*_):
            rules.restore(self.window.ds, undo)
            self.window.changed()

        toast = Adw.Toast(title=_("Stopped repeating"), button_label=_("Undo"))
        toast.connect("button-clicked", restore)
        self.window.toasts.add_toast(toast)
