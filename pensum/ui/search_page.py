"""Search: a field and the tasks whose title or notes contain the words;
open tasks open their page, archived ones show when they were done."""
from gi.repository import Adw, GLib, Gtk

from pensum.store import dates
from pensum.store.search import search


class SearchPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="Search", tag="search")
        self.window = window
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.entry = Gtk.SearchEntry(placeholder_text="Search Tasks", hexpand=True)
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], ["Search Tasks"])
        self.entry.connect("search-changed", lambda *_: self.refresh())
        header.set_title_widget(Adw.Clamp(child=self.entry, maximum_size=480))
        toolbar.add_top_bar(header)
        self.results = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.results.add_css_class("boxed-list")
        self.results.connect("row-activated", self._on_activated)
        self.status = Adw.StatusPage(icon_name="system-search-symbolic",
                                     title="Search Tasks",
                                     description="Titles and notes, archive included.")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_top=12,
                      margin_bottom=24, margin_start=12, margin_end=12)
        box.append(self.status)
        box.append(self.results)
        toolbar.set_content(Gtk.ScrolledWindow(
            child=Adw.Clamp(child=box, maximum_size=720),
            hscrollbar_policy=Gtk.PolicyType.NEVER))
        self.set_child(toolbar)
        self.connect("shown", lambda *_: self.entry.grab_focus())
        self.refresh()

    def refresh(self):
        ds = self.window.ds
        query = self.entry.get_text()
        found = search(ds, query)
        self.results.remove_all()
        for task, archived in found:
            project = ds.project_entities.get(task.get("projectId")) or {}
            parts = [project.get("title") or ""]
            if archived:
                parts.append("Archived, done " + dates.day_str(task["doneOn"])
                             if task.get("doneOn") else "Archived")
            elif task.get("isDone"):
                parts.append("Done")
            row = Adw.ActionRow(title=GLib.markup_escape_text(task.get("title") or "Untitled"),
                                subtitle=GLib.markup_escape_text(" · ".join(p for p in parts if p)),
                                activatable=not archived)
            row.task_id = None if archived else task["id"]
            self.results.append(row)
        self.results.set_visible(bool(found))
        self.status.set_visible(not found)
        if query.strip() and not found:
            self.status.set_title("No Tasks Found")
            self.status.set_description("Try other words.")
        else:
            self.status.set_title("Search Tasks")
            self.status.set_description("Titles and notes, archive included.")

    def _on_activated(self, listbox, row):
        if row.task_id:
            self.window.show_task(row.task_id)
