"""One section of a list: a header that collapses and expands it, with its
menu (rename, delete), and the section's tasks below."""
from gi.repository import Gio, Gtk, Pango

from pensum.store import sections
from pensum.ui import row_drag


class SectionGroup(Gtk.Box):
    def __init__(self, window, context, section, rows):
        """`rows` are the task rows of the section's open tasks."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.window = window
        self.context = context
        self.section_id = section["id"]
        title = section.get("title") or "Untitled"
        expanded = sections.is_expanded(section)

        header = Gtk.Box(spacing=6)
        arrow = Gtk.Image(icon_name="pan-down-symbolic" if expanded
                          else "pan-end-symbolic")
        label = Gtk.Label(label=title, xalign=0, hexpand=True,
                          ellipsize=Pango.EllipsizeMode.END)
        label.add_css_class("heading")
        count = Gtk.Label(label=str(len(rows)))
        count.add_css_class("dim-label")
        inner = Gtk.Box(spacing=6)
        for widget in (arrow, label, count):
            inner.append(widget)
        self.toggle = Gtk.Button(child=inner, hexpand=True)
        self.toggle.add_css_class("flat")
        self.toggle.add_css_class("pensum-touch")
        tip = f"Collapse Section “{title}”" if expanded else f"Expand Section “{title}”"
        self.toggle.set_tooltip_text(tip)
        self.toggle.update_property([Gtk.AccessibleProperty.LABEL], [tip])
        self.toggle.update_state([Gtk.AccessibleState.EXPANDED], [int(expanded)])
        self.toggle.connect("clicked", self._on_toggle, not expanded)
        header.append(self.toggle)

        menu = Gio.Menu()
        menu.append("Rename…", "section.rename")
        menu.append("Delete", "section.delete")
        group = Gio.SimpleActionGroup()
        for name, callback in (("rename", self._on_rename), ("delete", self._on_delete)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            group.add_action(action)
        self.insert_action_group("section", group)
        button = Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=menu,
                                tooltip_text="Section Menu", valign=Gtk.Align.CENTER)
        button.add_css_class("flat")
        button.add_css_class("pensum-touch")
        button.update_property([Gtk.AccessibleProperty.LABEL],
                               [f"Menu of Section “{title}”"])
        header.append(button)
        self.append(header)
        # A task dropped on the header becomes the section's first.
        row_drag.attach_section(header, self)

        self.list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        for row in rows:
            self.list.append(row)
        self.list.set_visible(expanded and bool(rows))
        self.append(self.list)

    def _on_toggle(self, _button, expanded):
        sections.set_expanded(self.window.ds, self.section_id, expanded)
        self.window.changed()

    def _on_rename(self, *_):
        from pensum.ui.dialogs import name_dialog
        ds = self.window.ds
        section = ds.data["section"]["entities"].get(self.section_id)
        if section is None:
            return

        def done(name):
            sections.rename(ds, self.section_id, name)
            self.window.changed()

        name_dialog(self.window, "Rename Section", section.get("title") or "",
                    "Rename", done)

    def _on_delete(self, *_):
        """Delete at once and offer Undo; the tasks stay in the list."""
        ds = self.window.ds
        section = ds.data["section"]["entities"].get(self.section_id)
        if section is None:
            return
        title = section.get("title") or "Untitled"
        self.window.undoable(f"Section “{title}” deleted",
                             lambda: sections.delete(ds, self.section_id))
