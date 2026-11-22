"""A task's notes: shown formatted (Markdown), with one tap to the text
field that edits the source and one tap back. The stored note is what was
typed: showing a note writes nothing, a ticked checkbox changes its one
character, and the editor saves only what the user changed."""
from gi.repository import Adw, GLib, Gtk

from pensum import markdown
from pensum.i18n import _
from pensum.store import tasks
from pensum.ui.notes_view import NotesView


class NotesBox(Adw.PreferencesGroup):
    def __init__(self, window, task_id):
        super().__init__(title=_("Notes"))
        self.window = window
        self.task_id = task_id
        self.editing = False
        self._dirty = False
        self._save_source = None
        self._shown = None

        self.switch = Gtk.Button(valign=Gtk.Align.CENTER)
        self.switch.add_css_class("flat")
        self.switch.add_css_class("pensum-touch")
        self.switch.connect("clicked", lambda *_: self.set_editing(not self.editing))
        self.set_header_suffix(self.switch)

        self.view = NotesView(self._on_toggle)
        view_frame = Gtk.Frame(child=self.view)
        view_frame.add_css_class("view")
        self.text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, top_margin=12,
                                 bottom_margin=12, left_margin=12, right_margin=12)
        self.text.update_property([Gtk.AccessibleProperty.LABEL], [_("Notes")])
        self.text.set_size_request(-1, 120)
        self.text.add_css_class("pensum-notes")
        text_frame = Gtk.Frame(child=self.text)
        text_frame.add_css_class("view")
        self.stack = Gtk.Stack(vhomogeneous=False, hhomogeneous=False)
        self.stack.add_named(view_frame, "view")
        self.stack.add_named(text_frame, "edit")
        self.add(self.stack)
        self._changed = self.text.get_buffer().connect("changed", self._on_changed)

    @property
    def formatted(self):
        """Super Productivity's switch for Markdown in notes; on if missing."""
        config = self.window.ds.config.get("tasks") or {}
        return config.get("isMarkdownFormattingInNotesEnabled", True) is not False

    def _source(self):
        task = self.window.ds.task(self.task_id)
        return (task.get("notes") or "") if task else ""

    def _set_buffer(self, source):
        buffer = self.text.get_buffer()
        buffer.handler_block(self._changed)
        buffer.set_text(source)
        buffer.handler_unblock(self._changed)
        self._dirty = False

    def load(self):
        """Show the task's note when the page opens: formatted when there
        is one, else the empty text field (which does not take the focus)."""
        source = self._source()
        self._set_buffer(source)
        self.switch.set_visible(self.formatted)
        self.set_editing(not self.formatted or not source, focus=False)

    def sync(self):
        """The note changed elsewhere (an import, Undo): show it again."""
        source = self._source()
        if self._dirty or source == self._shown:
            return
        self._set_buffer(source)
        self._render(source)

    def _render(self, source):
        self._shown = source
        if not self.editing:
            self.view.show(source)

    def set_editing(self, editing, focus=True):
        if self.editing and not editing:
            self.save()
        self.editing = editing
        self._render(self._source())
        self.stack.set_visible_child_name("edit" if editing else "view")
        label = _("Done") if editing else _("Edit")
        tip = _("Show the Notes Formatted") if editing else _("Edit the Notes")
        self.switch.set_label(label)
        self.switch.set_tooltip_text(tip)
        self.switch.update_property([Gtk.AccessibleProperty.LABEL], [tip])
        if editing and focus:
            self.text.grab_focus()

    def _on_toggle(self, line):
        source = self._source()
        changed = markdown.toggle_task(source, line)
        if changed == source:
            return
        tasks.update(self.window.ds, self.task_id, notes=changed)
        self._set_buffer(changed)
        self._shown = changed
        # The view is rebuilt after the click has been handled.
        GLib.idle_add(lambda: self.view.show(changed) or False)
        self.window.changed()

    def _on_changed(self, *_):
        self._dirty = True
        if self._save_source is None:
            self._save_source = GLib.timeout_add(600, self.save)

    def save(self):
        """Write the text field's content, only if the user changed it."""
        if self._save_source is not None:
            GLib.source_remove(self._save_source)
            self._save_source = None
        if not self._dirty or self.window.ds.task(self.task_id) is None:
            return GLib.SOURCE_REMOVE
        self._dirty = False
        buffer = self.text.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
        if text != self._source():
            tasks.update(self.window.ds, self.task_id, notes=text)
            self._shown = text
            self.window.changed()
        return GLib.SOURCE_REMOVE
