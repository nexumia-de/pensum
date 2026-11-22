"""A project's notes (#24): the list of its notes and one note's page,
where the text is edited and the note pinned to Today or removed with
Undo. The notes are Super Productivity's (pensum/store/notes.py)."""
from gi.repository import Adw, GLib, Gtk, Pango

from pensum.i18n import _
from pensum.store import notes


def _preview(note):
    lines = [line.strip() for line in (note.get("content") or "").splitlines() if line.strip()]
    return " ".join(lines[1:])[:120]


class NotesPage(Adw.NavigationPage):
    def __init__(self, window, project_id):
        super().__init__(title=_("Notes"))
        self.window = window
        self.project_id = project_id
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.group = Adw.PreferencesGroup()
        page = Adw.PreferencesPage()
        page.add(self.group)
        self.status = Adw.StatusPage(icon_name="accessories-text-editor-symbolic",
                                     title=_("No Notes"),
                                     description=_("Notes keep what belongs to the project but is no task."))
        self.stack = Gtk.Stack()
        self.stack.add_named(page, "list")
        self.stack.add_named(self.status, "empty")
        toolbar.set_content(self.stack)
        bar = Gtk.ActionBar()
        add = Gtk.Button(label=_("New Note"), css_classes=["suggested-action", "pensum-bar-button"])
        add.connect("clicked", self._on_add)
        bar.set_center_widget(add)
        toolbar.add_bottom_bar(bar)
        self.set_child(toolbar)
        self._rows = []
        self.refresh()

    def refresh(self):
        for row in self._rows:
            self.group.remove(row)
        self._rows = []
        found = notes.of_project(self.window.ds, self.project_id)
        for note in found:
            row = Adw.ActionRow(title=GLib.markup_escape_text(notes.title(note) or _("Empty Note")),
                                subtitle=GLib.markup_escape_text(_preview(note)),
                                activatable=True)
            if note.get("isPinnedToToday"):
                pin = Gtk.Image(icon_name="view-pin-symbolic", tooltip_text=_("Pinned to Today"))
                pin.update_property([Gtk.AccessibleProperty.LABEL], [_("Pinned to Today")])
                row.add_suffix(pin)
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, i=note["id"]: self.window.nav.push(
                NotePage(self.window, i)))
            self.group.add(row)
            self._rows.append(row)
        self.stack.set_visible_child_name("list" if found else "empty")

    def _on_add(self, _button):
        note = notes.add(self.window.ds, self.project_id)
        self.window.changed()
        self.window.nav.push(NotePage(self.window, note["id"]))


class NotePage(Adw.NavigationPage):
    """One note: its text, Pin to Today and Remove."""

    def __init__(self, window, note_id):
        super().__init__(title=_("Note"))
        self.window = window
        self.note_id = note_id
        note = self._note()
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text=_("Remove Note"))
        remove.update_property([Gtk.AccessibleProperty.LABEL], [_("Remove Note")])
        remove.connect("clicked", self._on_remove)
        header.pack_end(remove)
        toolbar.add_top_bar(header)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        pin = Adw.SwitchRow(title=_("Pin to Today"), active=bool(note.get("isPinnedToToday")))
        pin.connect("notify::active", self._on_pin)
        pins = Gtk.ListBox(css_classes=["boxed-list"], selection_mode=Gtk.SelectionMode.NONE)
        pins.append(pin)
        box.append(pins)
        self.text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, vexpand=True,
                                 top_margin=8, bottom_margin=8, left_margin=8, right_margin=8)
        self.text.add_css_class("card")
        self.text.get_buffer().set_text(note.get("content") or "")
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [_("Note")])
        box.append(self.text)
        hint = Gtk.Label(label=_("Markdown, as in Super Productivity."), xalign=0,
                         ellipsize=Pango.EllipsizeMode.END, css_classes=["dimmed", "caption"])
        box.append(hint)
        toolbar.set_content(Gtk.ScrolledWindow(child=box, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.set_child(toolbar)
        self.text.get_buffer().connect("changed", self._on_changed)

    def _note(self):
        return self.window.ds.data["note"]["entities"].get(self.note_id) or {}

    def _on_changed(self, buffer):
        """Every change is kept at once (saved soon after, as all changes)."""
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if self._note() and notes.set_content(self.window.ds, self.note_id, text):
            self.window.changed()

    def _on_pin(self, row, _param):
        if notes.set_pinned(self.window.ds, self.note_id, row.get_active()):
            self.window.changed()

    def _on_remove(self, _button):
        self.window.undoable(_("Note removed"), lambda: notes.delete(self.window.ds, self.note_id))
        self.window.nav.pop()

    def refresh(self):
        if not self._note():
            self.window.nav.pop()
