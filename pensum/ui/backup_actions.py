"""Import and export of Super Productivity backups through the file
chooser portal, so the Flatpak needs no file system access."""
import logging
from datetime import datetime

from gi.repository import Gio, GLib, Gtk

from pensum.game import records
from pensum.i18n import N_, _
from pensum.store import dates, incoming
from pensum.store.backup import BackupError
from pensum.ui.dialogs import confirm_dialog

log = logging.getLogger("pensum.import")


def _json_filter():
    filters = Gio.ListStore.new(Gtk.FileFilter)
    json_filter = Gtk.FileFilter(name=_("Super Productivity Backups"))
    json_filter.add_pattern("*.json")
    json_filter.add_mime_type("application/json")
    filters.append(json_filter)
    return filters


def import_backup(window):
    dialog = Gtk.FileDialog(title=_("Import Backup"), modal=True, filters=_json_filter())

    def chosen(dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return  # cancelled
        confirm(window, file.get_path())

    dialog.open(window, None, chosen)


def _count(number, one, many):
    """"1 task" or "3 tasks": `one` and `many` are texts for translation."""
    return _(one) if number == 1 else _(many).format(count=number)


def _and(first, second):
    return _("{first} and {second}").format(first=first, second=second)


def _days(ds, completions, shown=3):
    days = [dates.parse_day(ds.today(done_on)).strftime("%a %-d %b")
            for _task_id, done_on in completions]
    if len(days) > shown:
        rest = len(days) - shown
        return _and(", ".join(days[:shown]),
                    _count(rest, N_("1 more day"), N_("{count} more days")))
    return days[0] if len(days) == 1 else _and(", ".join(days[:-1]), days[-1])


def warning(ds, loss):
    """Heading and body of the import dialog for what the import would
    lose (pensum.store.incoming.Loss); no loss, the plain question."""
    keep = _("A copy of the current data is kept in the backups folder.")
    if not loss:
        return (_("Replace All Tasks?"),
                _("Your tasks, projects and tracked time are replaced by the "
                  "backup's.") + f" {keep}")
    parts = ([_count(len(loss.tasks), N_("1 task"), N_("{count} tasks"))]
             if loss.tasks else [])
    if loss.records:
        parts.append(_count(len(loss.records), N_("1 journey entry"),
                            N_("{count} journey entries")))
    lost = _and(*parts) if len(parts) == 2 else parts[0]
    if loss.unrelated:
        heading = _("Replace Other Data?")
        body = _("This file has none of the tasks on this device: {lost} "
                 "would be lost.").format(lost=lost)
    else:
        heading = _("Import Older Data?")
        body = _("This file is older than what is on this device: {lost} "
                 "would be lost.").format(lost=lost)
    if loss.completions:
        body += " " + _("Among them is your journey's task, done on {days}.").format(
            days=_days(ds, loss.completions))
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
        window.toast(_("Backup imported"))

    heading, body = warning(window.ds, loss)
    return confirm_dialog(window, heading, body,
                          _("Import Anyway") if loss else _("Replace"), done)


def export_backup(window):
    name = f"sp-backup-{datetime.now():%Y-%m-%d_%H%M%S}.json"
    dialog = Gtk.FileDialog(title=_("Export Backup"), modal=True, initial_name=name,
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
            window.toast(_("Can't export: {reason}").format(reason=error.strerror))
            return
        window.toast(_("Backup exported"))

    dialog.save(window, None, chosen)
