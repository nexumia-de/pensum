"""A task's attachments on its page (#25): each one with its title or
path; links, pictures and files open through the portal, a note is shown
as text, a command is listed but never run. **Add Link** appends one,
the remove button takes one away with Undo (pensum/store/attachments.py)."""
from gi.repository import Adw, Gio, GLib, Gtk

from pensum.i18n import _
from pensum.store import attachments

ICONS = {"LINK": "web-browser-symbolic", "IMG": "image-x-generic-symbolic",
         "FILE": "text-x-generic-symbolic", "NOTE": "accessories-text-editor-symbolic",
         "COMMAND": "utilities-terminal-symbolic"}


class AttachmentsGroup(Adw.PreferencesGroup):
    def __init__(self, window, task_id):
        super().__init__(title=_("Attachments"))
        self.window = window
        self.task_id = task_id
        self.entry = Adw.EntryRow(title=_("Add Link"), show_apply_button=True)
        self.entry.connect("apply", self._on_add)
        self._rows = []
        self.add(self.entry)
        self.refresh()

    def refresh(self):
        for row in self._rows:
            self.remove(row)
        self._rows = []
        task = self.window.ds.task(self.task_id) or {}
        for item in attachments.of_task(task):
            row = Adw.ActionRow(title=GLib.markup_escape_text(attachments.label(item)),
                                subtitle=GLib.markup_escape_text(
                                    item.get("path", "") if item.get("title") else ""),
                                activatable=attachments.can_open(item))
            row.add_prefix(Gtk.Image(icon_name=ICONS.get(item.get("type"), "mail-attachment-symbolic")))
            if item.get("type") == "COMMAND":
                row.set_subtitle(_("A command; Day Planner does not run commands."))
            if attachments.can_open(item):
                row.connect("activated", lambda _r, i=item: self._open(i))
            remove = Gtk.Button(icon_name="list-remove-symbolic", valign=Gtk.Align.CENTER,
                                css_classes=["flat"], tooltip_text=_("Remove Attachment"))
            remove.update_property([Gtk.AccessibleProperty.LABEL], [_("Remove Attachment")])
            remove.connect("clicked", lambda _b, i=item["id"]: self._remove(i))
            row.add_suffix(remove)
            self.add(row)
            self._rows.append(row)

    def _on_add(self, entry):
        if attachments.add(self.window.ds, self.task_id, entry.get_text()):
            entry.set_text("")
            self.window.changed()

    def _remove(self, attachment_id):
        self.window.undoable(_("Attachment removed"), lambda: attachments.delete(
            self.window.ds, self.task_id, attachment_id))

    def _open(self, item):
        if item.get("type") == "FILE":
            launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(item["path"]))
        else:
            launcher = Gtk.UriLauncher.new(item["path"])
        launcher.launch(self.window, None, self._launched)

    def _launched(self, launcher, result):
        try:
            launcher.launch_finish(result)
        except GLib.Error:
            self.window.toast(_("Can't open the attachment"))
