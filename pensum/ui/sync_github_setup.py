"""The guided setup of a GitHub sync folder on the sync page (like Git
Sync's page on the desktop, docs/git-sync.md#guided-setup): links that
open GitHub's new-repository and new-token forms filled in, and a button
that lists the repositories the token reaches so the person picks one
instead of typing it. The token is only sent to the API; it is kept in the
keyring by pensum.ui.sync_source."""
import threading

from gi.repository import Adw, GLib, Gtk

from pensum.i18n import _
from pensum.sync import SyncError, github

from pensum.sync.github import REPOSITORY_NAME, REPOSITORY_URL, TOKEN_URL


def _link_row(page, title, subtitle, url):
    row = Adw.ActionRow(title=title, subtitle=subtitle, activatable=True)
    row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic",
                             accessible_role=Gtk.AccessibleRole.PRESENTATION))
    row.connect("activated", lambda *_: Gtk.UriLauncher.new(url).launch(page.window, None, None))
    return row


def build_rows(page):
    """The two link rows, and a Find button on the repository row."""
    page.create_repo_row = _link_row(
        page, _("Create Repository"),
        _("Opens GitHub's form filled in: a private repository named sp-sync"),
        REPOSITORY_URL)
    page.create_token_row = _link_row(
        page, _("Create Token"),
        _("Opens GitHub's form filled in; under Repository access choose "
          "Only select repositories and the sync repository"),
        TOKEN_URL)
    find = Gtk.Button(icon_name="system-search-symbolic", valign=Gtk.Align.CENTER,
                      tooltip_text=_("Find Repositories"), css_classes=["flat"])
    find.update_property([Gtk.AccessibleProperty.LABEL], [_("Find Repositories")])
    find.connect("clicked", lambda *_: find_repositories(page))
    page.repo_row.add_suffix(find)
    page.find_button = find
    return page.create_repo_row, page.create_token_row


def find_repositories(page, wait=False):
    """Asks GitHub with the token typed; `wait` asks at once (tests)."""
    token = page.token_row.get_text().strip()
    if not token:
        page._show_error(_("Enter the access token."))
        return
    page.banner.set_revealed(False)
    page.find_button.set_sensitive(False)

    def work():
        try:
            result = github.list_repositories(token)
        except SyncError as error:
            result = error
        if wait:
            _found(page, result)
        else:
            GLib.idle_add(_found, page, result)

    if wait:
        work()
    else:
        threading.Thread(target=work, daemon=True).start()


def _found(page, result):
    page.find_button.set_sensitive(True)
    if isinstance(result, SyncError):
        page._show_error(str(result))
        return GLib.SOURCE_REMOVE
    usable = [r for r in result if r[2]]
    if not usable:
        page._show_error(_("The token reaches no repository it may write to."))
        return GLib.SOURCE_REMOVE
    if len(usable) == 1:
        choose(page, usable[0])
        return GLib.SOURCE_REMOVE
    usable.sort(key=lambda r: (not r[0].endswith("/" + REPOSITORY_NAME), r[0].lower()))
    dialog = Adw.Dialog(title=_("Choose the Repository"), content_width=360)
    view = Adw.ToolbarView()
    view.add_top_bar(Adw.HeaderBar())
    group = Adw.PreferencesGroup()
    for repository in usable:
        name, private, _write = repository
        row = Adw.ActionRow(title=name, activatable=True,
                            subtitle="" if private else _("Public: everyone can read it"))
        row.connect("activated", lambda _row, r=repository: (choose(page, r), dialog.close()))
        group.add(row)
    content = Adw.PreferencesPage()
    content.add(group)
    view.set_content(content)
    dialog.set_child(view)
    page.repo_dialog = dialog
    dialog.present(page.window)
    return GLib.SOURCE_REMOVE


def choose(page, repository):
    name, private, _write = repository
    page.repo_row.set_text(name)
    if not private:
        page._show_error(_("This repository is public: everyone can read your "
                           "tasks. Use a private one."))
