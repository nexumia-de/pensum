"""Folders in the sidebar (#27): a folder row that opens and closes on a
tap, with a menu to rename or delete it, and the dialog for a new
folder (pensum/store/menu_tree.py)."""
from gi.repository import Gio, GLib, Gtk, Pango

from pensum.i18n import _
from pensum.store import menu_tree
from pensum.store.dataset import Context

INDENT = 18


def folder_row(window, kind, node, depth):
    expanded = node.get("isExpanded", True) is not False
    box = Gtk.Box(spacing=12, margin_start=depth * INDENT)
    box.append(Gtk.Image(icon_name="pan-down-symbolic" if expanded else "pan-end-symbolic",
                         accessible_role=Gtk.AccessibleRole.PRESENTATION))
    box.append(Gtk.Label(label=node.get("name") or "", xalign=0, hexpand=True,
                         ellipsize=Pango.EllipsizeMode.END))
    menu = Gio.Menu()
    menu.append(_("Rename Folder…"), f"folder.rename::{node['id']}")
    menu.append(_("Delete Folder"), f"folder.delete::{node['id']}")
    button = Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=menu,
                            css_classes=["flat"], tooltip_text=_("Folder Menu"))
    button.update_property([Gtk.AccessibleProperty.LABEL], [_("Folder Menu")])
    box.append(button)
    row = Gtk.ListBoxRow(child=box)
    # Keeps the sidebar's headers ("Projects", "Tags") working.
    row.context = Context(kind, "folder:" + node["id"])
    row.folder = (kind, node["id"], expanded)
    row.update_property([Gtk.AccessibleProperty.LABEL],
                        [_("Folder {name}, open").format(name=node.get("name", "")) if expanded
                         else _("Folder {name}, closed").format(name=node.get("name", ""))])
    return row


def toggle(window, row):
    kind, folder_id, expanded = row.folder
    menu_tree.set_expanded(window.ds, kind, folder_id, not expanded)
    window.changed()


def install(window):
    """The `folder.*` actions on the window and `win.new-*-folder`."""
    group = Gio.SimpleActionGroup()
    for name, callback in (("rename", _rename), ("delete", _delete)):
        action = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
        action.connect("activate", lambda _a, v, run=callback: run(window, v.get_string()))
        group.add_action(action)
    window.insert_action_group("folder", group)
    for name, kind in (("new-project-folder", "project"), ("new-tag-folder", "tag")):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda *_a, k=kind: _new(window, k))
        window.add_action(action)


def _kind_of(window, folder_id):
    for kind in ("project", "tag"):
        if any(f[0] == folder_id for f in menu_tree.folders(window.ds, kind)):
            return kind
    return None


def _new(window, kind):
    from pensum.ui.dialogs import name_dialog

    def create(name):
        if menu_tree.add_folder(window.ds, kind, name):
            window.changed()

    name_dialog(window, _("New Folder"), "", _("Create"), create)


def _rename(window, folder_id):
    from pensum.ui.dialogs import name_dialog
    kind = _kind_of(window, folder_id)
    if kind is None:
        return
    current = next(f[1] for f in menu_tree.folders(window.ds, kind) if f[0] == folder_id)

    def done(name):
        if menu_tree.rename_folder(window.ds, kind, folder_id, name):
            window.changed()

    name_dialog(window, _("Rename Folder"), current, _("Rename"), done)


def _delete(window, folder_id):
    kind = _kind_of(window, folder_id)
    if kind is not None:
        window.undoable(_("Folder deleted; its lists stay"),
                        lambda: menu_tree.delete_folder(window.ds, kind, folder_id))
