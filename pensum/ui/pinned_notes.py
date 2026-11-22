"""The notes pinned to Today (#24), above Today's tasks: one row per note
in `note.todayOrder`, a tap opens it (pensum/ui/notes_page.py)."""
from gi.repository import Adw, GLib, Gtk

from pensum.i18n import _
from pensum.store import notes


class PinnedNotes(Gtk.ListBox):
    def __init__(self, window):
        super().__init__(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.window = window
        self.update_property([Gtk.AccessibleProperty.LABEL], [_("Pinned Notes")])

    def refresh(self, shown):
        self.remove_all()
        found = notes.pinned(self.window.ds) if shown else []
        for note in found:
            row = Adw.ActionRow(title=GLib.markup_escape_text(notes.title(note) or _("Empty Note")),
                                activatable=True)
            row.add_prefix(Gtk.Image(icon_name="view-pin-symbolic"))
            row.connect("activated", lambda _r, i=note["id"]: self._open(i))
            self.append(row)
        self.set_visible(bool(found))

    def _open(self, note_id):
        from pensum.ui.notes_page import NotePage
        self.window.nav.push(NotePage(self.window, note_id))
