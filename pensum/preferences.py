"""Preferences: style, the day boundary Super Productivity uses, and where
the data and its backups are."""
from gi.repository import Adw, GLib, Gtk
from phosh_toolkit.style import style_row


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, window):
        super().__init__(title="Preferences")
        self.window = window
        page = Adw.PreferencesPage(title="General",
                                   icon_name="preferences-system-symbolic")
        appearance = Adw.PreferencesGroup(title="Appearance")
        appearance.add(style_row(window.settings.style, self._on_style))
        page.add(appearance)

        day = Adw.PreferencesGroup(
            title="Day",
            description="Work after midnight still counts for the previous day "
                        "until this hour. Shared with Super Productivity.")
        self.hour_row = Adw.SpinRow.new_with_range(0, 23, 1)
        self.hour_row.set_title("Next Day Starts At")
        from pensum.store.dates import day_offset_ms
        self.hour_row.set_value(day_offset_ms(window.ds.config) // 3_600_000)
        self.hour_row.connect("notify::value", self._on_hour)
        day.add(self.hour_row)
        page.add(day)

        data = Adw.PreferencesGroup(
            title="Data",
            description="Day Planner keeps everything in a Super Productivity backup "
                        "file and makes an automatic backup at most every 15 "
                        "minutes. Use Export Backup to move the data to Super "
                        "Productivity, and Import Backup for the other way.")
        for title, path in (("Data File", window.files.path),
                            ("Automatic Backups", window.files.backups)):
            data.add(Adw.ActionRow(title=title, subtitle_selectable=True,
                                   subtitle=GLib.markup_escape_text(str(path))))
        page.add(data)
        self.add(page)

    def _on_style(self, style):
        self.window.settings.style = style
        self.window.save_settings()

    def _on_hour(self, row, *_):
        hours = int(row.get_value())
        misc = self.window.ds.config.setdefault("misc", {})
        misc["startOfNextDay"] = hours
        misc["startOfNextDayTime"] = f"{hours:02d}:00"
        self.window.changed()
