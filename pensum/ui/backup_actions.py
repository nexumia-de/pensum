"""Import and export of Super Productivity backups through the file
chooser portal, so the Flatpak needs no file system access."""
import logging
from datetime import datetime

from gi.repository import Gio, GLib, Gtk

from pensum.game import records
from pensum.store import dates, incoming
from pensum.store.backup import BackupError
from pensum.ui.dialogs import confirm_dialog

log = logging.getLogger("pensum.import")


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


def _count(number, word, words=None):
    return f"{number} {word}" if number == 1 else f"{number} {words or word + 's'}"


def _days(ds, completions, shown=3):
    days = [dates.parse_day(ds.today(done_on)).strftime("%a %-d %b")
            for _task_id, done_on in completions]
    if len(days) > shown:
        rest = len(days) - shown
        return ", ".join(days[:shown]) + f" and {_count(rest, 'more day')}"
    return days[0] if len(days) == 1 else ", ".join(days[:-1]) + " and " + days[-1]


def warning(ds, loss):
    """Heading and body of the import dialog for what the import would
    lose (pensum.store.incoming.Loss); no loss, the plain question."""
    keep = "A copy of the current data is kept in the backups folder."
    if not loss:
        return ("Replace All Tasks?",
                "Your tasks, projects and tracked time are replaced by the "
                f"backup's. {keep}")
    parts = [_count(len(loss.tasks), "task")] if loss.tasks else []
    if loss.records:
        parts.append(_count(len(loss.records), "journey entry", "journey entries"))
    lost = " and ".join(parts)
    if loss.unrelated:
        heading, body = ("Replace Other Data?",
                         f"This file has none of the tasks on this device: {lost} would be lost.")
    else:
        heading, body = ("Import Older Data?",
                         f"This file is older than what is on this device: {lost} would be lost.")
    if loss.completions:
        body += (" Among them is your journey's task, done on "
                 f"{_days(ds, loss.completions)}.")
    return heading, f"{body} {keep}"


def confirm(window, path):
    window.flush()
    try:
        ds = window.files.read_import(path)
    except (BackupError, OSError) as error:
        window.toast(str(error))
        return
    loss = incoming.compare(window.ds.data, ds.data, records.PREFIX,
                            records.journey_ids(window.ds))
    # Ids and counts only; titles and notes never reach the log.
    log.info("import would lose %d tasks (%d journey completions), %d records; "
             "unrelated: %s", len(loss.tasks), len(loss.completions), len(loss.records),
             loss.unrelated)

    def done():
        window.flush()
        try:
            imported = window.files.import_dataset(ds, window.ds, records.PREFIX)
        except OSError as error:
            window.toast(str(error))
            return
        window.replace_dataset(imported)
        window.toast("Backup imported")

    heading, body = warning(window.ds, loss)
    return confirm_dialog(window, heading, body,
                          "Import Anyway" if loss else "Replace", done)


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
