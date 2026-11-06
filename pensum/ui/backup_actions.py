"""Import and export of Super Productivity backups through the file
chooser portal, so the Flatpak needs no file system access."""
from datetime import datetime

from gi.repository import Gio, GLib, Gtk

from pensum.store.backup import BackupError


def _json_filter():
    filters = Gio.ListStore.new(Gtk.FileFilter)
    json_filter = Gtk.FileFilter(name="Super Productivity Backups")
    json_filter.add_pattern("*.json")
    json_filter.add_mime_type("application/json")
    filters.append(json_filter)
    return filters


def import_backup(window):
    dialog = Gtk.FileDialog(title="Import Backup", modal=True, filters=_json_filter())

    def chosen(dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return  # cancelled
        confirm(window, file.get_path())

    dialog.open(window, None, chosen)


def confirm(window, path):
    from pensum.ui.dialogs import confirm_dialog

    def done():
        window.flush()
        try:
            ds = window.files.import_file(path, window.ds)
        except (BackupError, OSError) as error:
            window.toast(str(error))
            return
        window.replace_dataset(ds)
        window.toast("Backup imported")

    confirm_dialog(window, "Replace All Tasks?",
                   "Your tasks, projects and tracked time are replaced by "
                   "the backup's. A copy of the current data is kept in the "
                   "backups folder.", "Replace", done)


def export_backup(window):
    name = f"sp-backup-{datetime.now():%Y-%m-%d_%H%M%S}.json"
    dialog = Gtk.FileDialog(title="Export Backup", modal=True, initial_name=name,
                            filters=_json_filter())

    def chosen(dialog, result):
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        window.timer.book()
        try:
            window.files.export_file(file.get_path(), window.ds)
        except OSError as error:
            window.toast(f"Can't export: {error.strerror}")
            return
        window.toast("Backup exported")

    dialog.save(window, None, chosen)
