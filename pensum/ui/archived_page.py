"""Archived projects: open one to see its tasks, or bring it back to the
sidebar."""
from gi.repository import Adw, GLib, Gtk

from pensum.i18n import _
from pensum.store import contexts
from pensum.store.dataset import Context


class ArchivedPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title=_("Archived Projects"), tag="archived")
        self.window = window
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.page = Adw.PreferencesPage()
        self.status = Adw.StatusPage(icon_name="folder-symbolic",
                                     title=_("No Archived Projects"),
                                     description=_("Archive a project from its list menu."))
        self.stack = Gtk.Stack()
        self.stack.add_named(self.page, "list")
        self.stack.add_named(self.status, "empty")
        toolbar.set_content(self.stack)
        self.set_child(toolbar)
        self.group = None
        self.refresh()

    def refresh(self):
        if self.group is not None:
            self.page.remove(self.group)
        self.group = Adw.PreferencesGroup()
        projects = self.window.ds.projects(archived=True)
        for project in projects:
            open_count = sum(1 for i in project.get("taskIds", ())
                             if not (self.window.ds.task(i) or {}).get("isDone", True))
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(project.get("title") or _("Untitled")),
                subtitle=(_("{count} open tasks").format(count=open_count)
                      if open_count != 1 else _("1 open task")),
                activatable=True)
            row.connect("activated", self._on_open, project["id"])
            button = Gtk.Button(label=_("Unarchive"), valign=Gtk.Align.CENTER)
            button.connect("clicked", self._on_unarchive, project["id"])
            row.add_suffix(button)
            self.group.add(row)
        self.page.add(self.group)
        self.stack.set_visible_child_name("list" if projects else "empty")

    def _on_open(self, row, project_id):
        self.window.show_list(Context("project", project_id))

    def _on_unarchive(self, button, project_id):
        contexts.set_archived(self.window.ds, project_id, False)
        self.window.toast(_("Project back in the sidebar"))
        self.window.changed()
