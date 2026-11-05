"""The sidebar: Today, the projects and the tags with their open task
counts, the main menu and the buttons that add a project or a tag."""
from gi.repository import Adw, Gio, Gtk, Pango

from pensum import NAME
from pensum.store.dataset import Context


def main_menu():
    menu = Gio.Menu()
    backup = Gio.Menu()
    backup.append("Import Backup…", "app.import-backup")
    backup.append("Export Backup…", "app.export-backup")
    menu.append_section(None, backup)
    rest = Gio.Menu()
    rest.append("Preferences", "app.preferences")
    rest.append("About Pensum", "app.about")
    menu.append_section(None, rest)
    return menu


def add_menu():
    menu = Gio.Menu()
    menu.append("New Project…", "win.new-project")
    menu.append("New Tag…", "win.new-tag")
    return menu


class Sidebar(Adw.Bin):
    def __init__(self, window):
        super().__init__()
        self.window = window
        toolbar = Adw.ToolbarView()
        self.set_child(toolbar)
        header = Adw.HeaderBar(title_widget=Adw.WindowTitle(title=NAME))
        add = Gtk.MenuButton(icon_name="list-add-symbolic", menu_model=add_menu(),
                             tooltip_text="Add List")
        add.update_property([Gtk.AccessibleProperty.LABEL], ["Add List"])
        header.pack_start(add)
        menu = Gtk.MenuButton(icon_name="open-menu-symbolic", primary=True,
                              menu_model=main_menu(), tooltip_text="Main Menu")
        menu.update_property([Gtk.AccessibleProperty.LABEL], ["Main Menu"])
        header.pack_end(menu)
        toolbar.add_top_bar(header)
        for name, kind in (("new-project", "project"), ("new-tag", "tag")):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", self._on_new, kind)
            window.add_action(action)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("navigation-sidebar")
        self.listbox.set_header_func(self._header)
        self.listbox.connect("row-activated", self._on_activated)
        toolbar.set_content(Gtk.ScrolledWindow(
            child=self.listbox, hscrollbar_policy=Gtk.PolicyType.NEVER))
        self._contexts = []

    def _on_new(self, action, param, kind):
        from pensum.ui.dialogs import name_dialog
        from pensum.store import contexts
        title = "New Project" if kind == "project" else "New Tag"

        def create(name):
            add = contexts.add_project if kind == "project" else contexts.add_tag
            entity = add(self.window.ds, name)
            self.window.changed()
            self.window.show_list(Context(kind, entity["id"]))

        name_dialog(self.window, title, "", "Create", create)

    def _row(self, context, title, icon, count):
        box = Gtk.Box(spacing=12)
        box.append(Gtk.Image(icon_name=icon, accessible_role=Gtk.AccessibleRole.PRESENTATION))
        label = Gtk.Label(label=title, xalign=0, hexpand=True,
                          ellipsize=Pango.EllipsizeMode.END)
        box.append(label)
        if count:
            counter = Gtk.Label(label=str(count))
            counter.add_css_class("dimmed")
            counter.add_css_class("numeric")
            box.append(counter)
        row = Gtk.ListBoxRow(child=box)
        row.context = context
        row.update_property([Gtk.AccessibleProperty.LABEL],
                            [f"{title}, {count} open" if count else title])
        return row

    def _header(self, row, before):
        kind = row.context.kind
        if before is not None and before.context.kind == kind:
            row.set_header(None)
            return
        if kind == "today":
            row.set_header(None)
            return
        label = Gtk.Label(label="Projects" if kind == "project" else "Tags",
                          xalign=0, margin_start=12, margin_top=12, margin_bottom=6)
        label.add_css_class("heading")
        label.add_css_class("dimmed")
        row.set_header(label)

    def refresh(self):
        ds = self.window.ds
        selected = self.window.list_page.context
        self.listbox.remove_all()
        today = ds.today()
        entries = [(Context.today(), "Today", "weather-clear-symbolic")]
        entries += [(Context("project", p["id"]), p.get("title") or "Untitled",
                     "folder-symbolic") for p in ds.projects()]
        entries += [(Context("tag", t["id"]), t.get("title") or "Untitled",
                     "pensum-tag-symbolic") for t in ds.tags()]
        for context, title, icon in entries:
            count = len(ds.list_tasks(context, today)[0])
            row = self._row(context, title, icon, count)
            self.listbox.append(row)
            if context == selected:
                self.listbox.select_row(row)

    def select(self, context):
        row = self.listbox.get_first_child()
        while row is not None:
            if getattr(row, "context", None) == context:
                self.listbox.select_row(row)
                return
            row = row.get_next_sibling()

    def _on_activated(self, listbox, row):
        self.window.show_list(row.context)
