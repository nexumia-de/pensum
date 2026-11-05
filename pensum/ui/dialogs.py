"""Small dialogs: ask for a name, confirm a deletion."""
from gi.repository import Adw, Gtk


def name_dialog(window, heading, current, confirm, done):
    """Ask for a name; done(name) gets the non-empty, stripped text."""
    dialog = Adw.AlertDialog(heading=heading)
    entry = Gtk.Entry(text=current, activates_default=True)
    entry.update_property([Gtk.AccessibleProperty.LABEL], ["Name"])
    dialog.set_extra_child(entry)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("ok", confirm)
    dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
    dialog.set_default_response("ok")
    dialog.set_close_response("cancel")
    dialog.set_response_enabled("ok", bool(current.strip()))
    entry.connect("changed", lambda e: dialog.set_response_enabled(
        "ok", bool(e.get_text().strip())))

    def on_response(dialog, response):
        name = entry.get_text().strip()
        if response == "ok" and name:
            done(name)

    dialog.connect("response", on_response)
    dialog.present(window)
    entry.grab_focus()
    return dialog


def confirm_dialog(window, heading, body, confirm, done):
    """A destructive confirmation; done() runs when confirmed."""
    dialog = Adw.AlertDialog(heading=heading, body=body)
    dialog.add_response("cancel", "Cancel")
    dialog.add_response("delete", confirm)
    dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_close_response("cancel")
    dialog.connect("response", lambda d, r: done() if r == "delete" else None)
    dialog.present(window)
    return dialog
