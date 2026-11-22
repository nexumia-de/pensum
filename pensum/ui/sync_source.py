"""The sync page's source form (pensum.ui.sync_page): which sync folder to
read, a WebDAV server, a folder on this device or a GitHub repository kept
by Git Sync (pensum.sync.github), and the source object for it. Passwords
and the token live in the keyring only."""
from gi.repository import Adw, GLib, Gtk

from pensum.i18n import _
from pensum.sync import SyncError, keyring
from pensum.sync.github import GitHub, parse_repository
from pensum.sync.local import LocalFolder
from pensum.sync.webdav import WebDav
from pensum.ui import sync_github_setup

KINDS = ("webdav", "local", "github")
GITHUB_HELP = "https://github.com/nexumia-de/tabularium#readme"


def build_group(page):
    """The form; its rows become attributes of the page."""
    group = Adw.PreferencesGroup(
        description=_("Read the tasks Super Productivity keeps in its sync "
                      "folder. Reading never changes the folder; Send Changes "
                      "adds Day Planner's edits."))
    s = page.settings
    page.kind_row = Adw.ComboRow(title=_("Kind"), model=Gtk.StringList.new(
        [_("WebDAV or Nextcloud"), _("Folder on This Device"), _("GitHub Repository")]))
    page.kind_row.set_selected(KINDS.index(s.sync_kind) if s.sync_kind in KINDS else 0)
    page.kind_row.connect("notify::selected", lambda *_: on_kind_changed(page))
    group.add(page.kind_row)

    page.url_row = Adw.EntryRow(title=_("Server Address"), text=s.sync_url,
                                input_purpose=Gtk.InputPurpose.URL)
    page.user_row = Adw.EntryRow(title=_("User Name"), text=s.sync_user)
    page.password_row = Adw.PasswordEntryRow(title=_("Password"))
    page.folder_row = Adw.EntryRow(title=_("Folder on the Server"), text=s.sync_folder)
    page.webdav_rows = (page.url_row, page.user_row, page.password_row, page.folder_row)

    page.local_row = Adw.ActionRow(title=_("Folder"),
                                   subtitle=s.sync_local_path or _("None chosen"))
    choose = Gtk.Button(label=_("Choose…"), valign=Gtk.Align.CENTER)
    choose.connect("clicked", lambda *_: choose_folder(page))
    page.local_row.add_suffix(choose)

    page.repo_row = Adw.EntryRow(title=_("Repository (owner/name)"), text=s.sync_github_repo)
    page.token_row = Adw.PasswordEntryRow(title=_("Access Token"))
    page.repo_folder_row = Adw.EntryRow(title=_("Folder in the Repository"),
                                        text=s.sync_github_folder)
    page.github_help_row = Adw.ActionRow(
        title=_("How to Set Up Git Sync"),
        subtitle=_("On the desktop the Git Sync plugin keeps Super "
                   "Productivity's folder in the repository"), activatable=True)
    page.github_help_row.add_suffix(Gtk.Image(icon_name="adw-external-link-symbolic",
                                              accessible_role=Gtk.AccessibleRole.PRESENTATION))
    page.github_help_row.connect(
        "activated", lambda *_: Gtk.UriLauncher.new(GITHUB_HELP).launch(page.window, None, None))
    create_repo, create_token = sync_github_setup.build_rows(page)
    page.github_rows = (create_repo, create_token, page.token_row, page.repo_row,
                        page.repo_folder_row, page.github_help_row)

    for row in (*page.webdav_rows, page.local_row, *page.github_rows):
        group.add(row)
    if s.sync_url and s.sync_user:
        password = keyring.lookup(s.sync_url, s.sync_user)
        if password:
            page.password_row.set_text(password)
    if s.sync_github_repo:
        token = keyring.lookup(github_key(s.sync_github_repo), "")
        if token:
            page.token_row.set_text(token)
    return group


def github_key(repository):
    return f"github:{repository}"


def kind(page):
    return KINDS[page.kind_row.get_selected()]


def on_kind_changed(page):
    current = kind(page)
    for row in page.webdav_rows:
        row.set_visible(current == "webdav")
    page.local_row.set_visible(current == "local")
    for row in page.github_rows:
        row.set_visible(current == "github")


def choose_folder(page):
    dialog = Gtk.FileDialog(title=_("Choose the Sync Folder"), modal=True)

    def chosen(dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return  # cancelled
        page.settings.sync_local_path = folder.get_path() or ""
        page.local_row.set_subtitle(page.settings.sync_local_path or _("None chosen"))
        page.window.save_settings()

    dialog.select_folder(page.window, None, chosen)


def source(page):
    """The source from the form, and a key that names it; remembers the
    form (passwords and the token only in the keyring)."""
    s = page.settings
    s.sync_kind = kind(page)
    if s.sync_kind == "local":
        if not s.sync_local_path:
            raise SyncError(_("Choose the folder first."))
        page.window.save_settings()
        return LocalFolder(s.sync_local_path), f"local:{s.sync_local_path}"
    if s.sync_kind == "github":
        s.sync_github_repo = parse_repository(page.repo_row.get_text())
        s.sync_github_folder = page.repo_folder_row.get_text().strip().strip("/")
        token = page.token_row.get_text().strip()
        if not token:
            raise SyncError(_("Enter the access token."))
        page.window.save_settings()
        keyring.store(github_key(s.sync_github_repo), "", token)
        return (GitHub(s.sync_github_repo, token, s.sync_github_folder),
                f"github:{s.sync_github_repo}|{s.sync_github_folder}")
    s.sync_url = page.url_row.get_text().strip()
    s.sync_user = page.user_row.get_text().strip()
    s.sync_folder = page.folder_row.get_text().strip()
    password = page.password_row.get_text()
    if not s.sync_url:
        raise SyncError(_("Enter the server address."))
    page.window.save_settings()
    if s.sync_user and password:
        keyring.store(s.sync_url, s.sync_user, password)
    return (WebDav(s.sync_url, s.sync_user, password, s.sync_folder),
            f"webdav:{s.sync_url}|{s.sync_user}|{s.sync_folder}")


def encryption_password(page, key):
    """The password typed, remembered in the keyring for this source, or
    the one remembered before."""
    typed = page.encryption_row.get_text()
    if typed:
        keyring.store(f"encryption:{key}", "", typed)
        return typed
    return keyring.lookup(f"encryption:{key}", "")
