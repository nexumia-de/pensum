"""A journey of the user's own as a file (#80, QuestArc #40): importing
a journey file, checked by the engine's journey checker before it is
kept, and exporting one, which gives the file QuestArc reads."""
from gi.repository import Gio, GLib, Gtk

from pensum.game import own
from pensum.i18n import _


def _filter():
    filters = Gio.ListStore.new(Gtk.FileFilter)
    found = Gtk.FileFilter(name=_("Journey Files"))
    found.add_pattern("*.json")
    found.add_mime_type("application/json")
    filters.append(found)
    return filters


def read(window, path, done=None):
    """Keep the journey of the file at `path`; `done(journey)` after it
    was written."""
    from pensum.ui.journey.quick_preview import keep
    try:
        with open(path, encoding="utf-8") as file:
            journey = own.read_file(file.read(2 * 1024 * 1024))
    except (OSError, UnicodeDecodeError):
        journey = None
    if journey is None:
        window.toast(_("This file is not a journey."))
        return False
    if not keep(window, journey):
        return False
    window.toast(_("Journey imported"))
    if done:
        done(journey)
    return True


def import_journey(window, done=None):
    dialog = Gtk.FileDialog(title=_("Import a Journey File"), modal=True, filters=_filter())

    def chosen(dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return  # cancelled
        read(window, file.get_path(), done)

    dialog.open(window, None, chosen)


def write(window, path, journey):
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(own.file_text(journey))
    except OSError as error:
        window.toast(_("Can't export: {reason}").format(reason=error.strerror))
        return False
    window.toast(_("Journey exported"))
    return True


def export_journey(window, journey):
    dialog = Gtk.FileDialog(title=_("Export Journey"), modal=True,
                            initial_name=f"{journey['id']}.json", filters=_filter())

    def chosen(dialog, result):
        try:
            file = dialog.save_finish(result)
        except GLib.Error:
            return
        write(window, file.get_path(), journey)

    dialog.save(window, None, chosen)
