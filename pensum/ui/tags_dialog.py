"""Choose a task's tags: a switch per tag, and a field that creates one."""
from gi.repository import Adw, GLib

from pensum.store import contexts, tasks


class TagsDialog(Adw.Dialog):
    def __init__(self, window, task_id):
        super().__init__(title="Tags", content_width=360, content_height=480)
        self.window = window
        self.task_id = task_id
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        self.set_child(toolbar)
        self.group = None
        self._fill()

    def _fill(self):
        if self.group is not None:
            self.page.remove(self.group)
        ds = self.window.ds
        task = ds.task(self.task_id)
        self.group = Adw.PreferencesGroup()
        for tag in ds.tags():
            row = Adw.SwitchRow(title=GLib.markup_escape_text(tag.get("title") or "Untitled"),
                                active=tag["id"] in task.get("tagIds", ()))
            row.connect("notify::active", self._on_toggled, tag["id"])
            self.group.add(row)
        entry = Adw.EntryRow(title="New Tag", show_apply_button=True)
        entry.connect("entry-activated", self._on_new)
        entry.connect("apply", self._on_new)
        self.group.add(entry)
        self.page.add(self.group)

    def _on_toggled(self, row, _, tag_id):
        ds = self.window.ds
        current = list(ds.task(self.task_id).get("tagIds", ()))
        if row.get_active() and tag_id not in current:
            current.append(tag_id)
        elif not row.get_active():
            current = [t for t in current if t != tag_id]
        tasks.set_tags(ds, self.task_id, current)
        self.window.changed()

    def _on_new(self, entry):
        name = entry.get_text().strip()
        if not name:
            return
        ds = self.window.ds
        tag = contexts.add_tag(ds, name)
        tasks.set_tags(ds, self.task_id, list(ds.task(self.task_id)["tagIds"]) + [tag["id"]])
        self.window.changed()
        self._fill()
