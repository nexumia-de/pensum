"""Preferences: style, the day boundary Super Productivity uses, how the
journeys look and their data, and where the data and its backups are."""
from gi.repository import Adw, GLib
from pensum.i18n import _
from phosh_toolkit.style import style_row


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, window):
        super().__init__(title=_("Preferences"))
        self.window = window
        page = Adw.PreferencesPage(title=_("General"),
                                   icon_name="preferences-system-symbolic")
        appearance = Adw.PreferencesGroup(title=_("Appearance"))
        appearance.add(style_row(window.settings.style, self._on_style))
        page.add(appearance)

        day = Adw.PreferencesGroup(
            title=_("Day"),
            description=_("Work after midnight still counts for the previous day "
                          "until this hour. Shared with Super Productivity."))
        self.hour_row = Adw.SpinRow.new_with_range(0, 23, 1)
        self.hour_row.set_title(_("Next Day Starts At"))
        from pensum.store.dates import day_offset_ms
        self.hour_row.set_value(day_offset_ms(window.ds.config) // 3_600_000)
        self.hour_row.connect("notify::value", self._on_hour)
        day.add(self.hour_row)
        page.add(day)
        remind = Adw.PreferencesGroup(title=_("Reminders"))
        closed = Adw.SwitchRow(
            title=_("Remind When Closed"),
            subtitle=_("Day Planner stays in the background while a reminder is waiting"),
            active=window.settings.remind_when_closed)
        closed.connect("notify::active", self._on_remind_closed)
        remind.add(closed)
        page.add(remind)
        if window.journeys.available:
            page.add(self._journeys_group())

        data = Adw.PreferencesGroup(
            title=_("Data"),
            description=_("Day Planner keeps everything in a Super Productivity backup "
                          "file and makes an automatic backup at most every 15 "
                          "minutes. Use Export Backup to move the data to Super "
                          "Productivity, and Import Backup for the other way."))
        for title, path in ((_("Data File"), window.files.path),
                            (_("Automatic Backups"), window.files.backups)):
            data.add(Adw.ActionRow(title=title, subtitle_selectable=True,
                                   subtitle=GLib.markup_escape_text(str(path))))
        page.add(data)
        self.add(page)

    def _journeys_group(self):
        from pensum.game.content import t
        group = Adw.PreferencesGroup(title=_("Journeys"), description=t("ui.settings.data.text"))
        strip = Adw.SwitchRow(title=_("Show on Today"),
                              subtitle=_("The step that is growing, on top of Today's tasks"),
                              active=self.window.settings.journey_strip)
        strip.connect("notify::active", self._on_strip)
        group.add(strip)
        remove = Adw.ButtonRow(title=t("ui.settings.data.remove")) if hasattr(
            Adw, "ButtonRow") else Adw.ActionRow(title=t("ui.settings.data.remove"),
                                                  activatable=True)
        remove.add_css_class("destructive-action")
        remove.connect("activated", self._on_remove)
        group.add(remove)
        return group

    def _on_remove(self, *_):
        from pensum.game.content import t
        from pensum.ui.dialogs import confirm_dialog

        def remove():
            model = self.window.journeys
            model.write({key: "" for key in model.records()}, guard=False)

        confirm_dialog(self, t("ui.settings.data.remove"), t("ui.settings.data.confirm"),
                       t("ui.settings.data.remove-now"), remove)

    def _on_remind_closed(self, row, *_):
        from pensum import background
        self.window.settings.remind_when_closed = row.get_active()
        self.window.save_settings()
        background.request(autostart=row.get_active())
        self.window.get_application().reminders.check()

    def _on_strip(self, row, *_):
        self.window.settings.journey_strip = row.get_active()
        self.window.save_settings()
        self.window.list_page.refresh()

    def _on_style(self, style):
        self.window.settings.style = style
        self.window.save_settings()

    def _on_hour(self, row, *_):
        hours = int(row.get_value())
        misc = self.window.ds.config.setdefault("misc", {})
        misc["startOfNextDay"] = hours
        misc["startOfNextDayTime"] = f"{hours:02d}:00"
        self.window.changed()
