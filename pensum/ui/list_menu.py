"""A list's menu: add a section, rename, archive, delete the list."""
from gi.repository import Gio

from pensum.store import contexts, sections
from pensum.store.dataset import Context


def install(page):
    """The `list.*` actions on a task list page."""
    group = Gio.SimpleActionGroup()
    for name, callback in (("add-section", _on_add_section), ("rename", _on_rename),
                           ("archive", _on_archive), ("delete", _on_delete)):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", lambda *_, run=callback: run(page))
        group.add_action(action)
    page.insert_action_group("list", group)


def model(page):
    """The menu for the list the page shows; None when it has no entry."""
    context = page.context
    menu = Gio.Menu()
    if sections.can_have(context):
        menu.append("Add Section…", "list.add-section")
    if context.kind == "today":
        return menu
    menu.append("Rename…", "list.rename")
    if context.kind == "project" and context.id != "INBOX_PROJECT":
        archived = page.window.ds.project_entities[context.id].get("isArchived")
        menu.append("Unarchive Project" if archived else "Archive Project",
                    "list.archive")
    if context.id != "INBOX_PROJECT":
        menu.append("Delete", "list.delete")
    return menu


def _on_add_section(page):
    from pensum.ui.dialogs import name_dialog
    window, context = page.window, page.context

    def done(name):
        sections.add(window.ds, context, name)
        window.changed()

    name_dialog(window, "Add Section", "", "Add", done)


def _on_rename(page):
    from pensum.ui.dialogs import name_dialog
    window, context = page.window, page.context

    def done(name):
        contexts.rename(window.ds, context.kind, context.id, name)
        window.changed()

    kind = "Project" if context.kind == "project" else "Tag"
    name_dialog(window, f"Rename {kind}", window.ds.context_title(context),
                "Rename", done)


def _on_archive(page):
    window = page.window
    ds = window.ds
    archived = not ds.project_entities[page.context.id].get("isArchived")
    contexts.set_archived(ds, page.context.id, archived)
    if archived:
        window.toast("Project archived")
        window.show_list(Context.today())
    else:
        window.toast("Project back in the sidebar")
    window.changed()


def _on_delete(page):
    """Delete at once and offer Undo (GNOME HIG)."""
    window, context = page.window, page.context
    ds = window.ds
    name = ds.context_title(context)

    def delete():
        if context.kind == "project":
            contexts.delete_project(ds, context.id)
        else:
            contexts.delete_tag(ds, context.id)

    window.show_list(Context.today())
    window.undoable(f"“{name}” deleted", delete)
