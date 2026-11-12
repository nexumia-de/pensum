"""Read a Super Productivity sync folder (WebDAV, Nextcloud or a folder on
this device), show what it holds and offer it as an import. Pensum only
reads the folder (pensum.sync); the import replaces Pensum's data like a
backup import."""
import logging
import threading

from gi.repository import Adw, GLib, Gtk

from pensum.sync import SyncError, changes, keyring, reader, summary
from pensum.sync.local import LocalFolder
from pensum.sync.webdav import WebDav

log = logging.getLogger("pensum.sync")

KINDS = ("webdav", "local")


class SyncPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="Sync Folder", tag="sync")
        self.window = window
        self.settings = window.settings
        self.snapshot = None
        self.source_key = ""
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.banner = Adw.Banner()
        toolbar.add_top_bar(self.banner)
        page = Adw.PreferencesPage()
        page.add(self._folder_group())
        self.result = Adw.PreferencesGroup(title="In the Sync Folder", visible=False)
        self.rows = {}
        for key, title in (("open", "Open Tasks"), ("done", "Done Tasks"),
                           ("archived", "Archived Tasks"), ("projects", "Projects"),
                           ("tags", "Tags"), ("changes", "Changes Since Last Read")):
            row = Adw.ActionRow(title=title)
            label = Gtk.Label(css_classes=["dim-label", "numeric"])
            row.add_suffix(label)
            self.rows[key] = label
            self.result.add(row)
        page.add(self.result)
        toolbar.set_content(page)
        toolbar.add_bottom_bar(self._bottom_bar())
        self.set_child(toolbar)
        self._on_kind_changed()
        self.connect("shown", lambda *_: GLib.idle_add(window._unfocus))

    # --- layout ---------------------------------------------------------

    def _folder_group(self):
        group = Adw.PreferencesGroup(
            description="Read the tasks Super Productivity keeps in its sync "
                        "folder. Day Planner only reads the folder and never "
                        "changes it.")
        s = self.settings
        self.kind_row = Adw.ComboRow(title="Kind", model=Gtk.StringList.new(
            ["WebDAV or Nextcloud", "Folder on This Device"]))
        self.kind_row.set_selected(KINDS.index(s.sync_kind) if s.sync_kind in KINDS else 0)
        self.kind_row.connect("notify::selected", self._on_kind_changed)
        group.add(self.kind_row)
        self.url_row = Adw.EntryRow(title="Server Address", text=s.sync_url,
                                    input_purpose=Gtk.InputPurpose.URL)
        self.user_row = Adw.EntryRow(title="User Name", text=s.sync_user)
        self.password_row = Adw.PasswordEntryRow(title="Password")
        self.folder_row = Adw.EntryRow(title="Folder on the Server", text=s.sync_folder)
        self.webdav_rows = (self.url_row, self.user_row, self.password_row, self.folder_row)
        for row in self.webdav_rows:
            group.add(row)
        self.local_row = Adw.ActionRow(title="Folder",
                                       subtitle=s.sync_local_path or "None chosen")
        choose = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose.connect("clicked", self._on_choose)
        self.local_row.add_suffix(choose)
        group.add(self.local_row)
        if s.sync_url and s.sync_user:
            password = keyring.lookup(s.sync_url, s.sync_user)
            if password:
                self.password_row.set_text(password)
        return group

    def _bottom_bar(self):
        bar = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER,
                      margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        self.read_button = Gtk.Button(label="Read Folder", css_classes=["pill"])
        self.read_button.connect("clicked", lambda *_: self.read())
        # Adw.Spinner needs libadwaita 1.6; Ubuntu 24.04 (CI) has 1.5.
        self.spinner = (Adw.Spinner(visible=False) if hasattr(Adw, "Spinner")
                        else Gtk.Spinner(spinning=True, visible=False))
        self.import_button = Gtk.Button(label="Import…", sensitive=False,
                                        css_classes=["pill", "suggested-action"])
        self.import_button.connect("clicked", self._on_import)
        bar.append(self.read_button)
        bar.append(self.spinner)
        bar.append(self.import_button)
        return bar

    def _kind(self):
        return KINDS[self.kind_row.get_selected()]

    def _on_kind_changed(self, *_):
        webdav = self._kind() == "webdav"
        for row in self.webdav_rows:
            row.set_visible(webdav)
        self.local_row.set_visible(not webdav)

    def _on_choose(self, *_):
        dialog = Gtk.FileDialog(title="Choose the Sync Folder", modal=True)

        def chosen(dialog, result):
            try:
                folder = dialog.select_folder_finish(result)
            except GLib.Error:
                return  # cancelled
            self.settings.sync_local_path = folder.get_path() or ""
            self.local_row.set_subtitle(self.settings.sync_local_path or "None chosen")
            self.window.save_settings()

        dialog.select_folder(self.window, None, chosen)

    # --- reading --------------------------------------------------------

    def _source(self):
        """The source from the form, and a key that names it; remembers
        the form (the password only in the keyring)."""
        s = self.settings
        s.sync_kind = self._kind()
        if s.sync_kind == "local":
            if not s.sync_local_path:
                raise SyncError("Choose the folder first.")
            self.window.save_settings()
            return LocalFolder(s.sync_local_path), f"local:{s.sync_local_path}"
        s.sync_url = self.url_row.get_text().strip()
        s.sync_user = self.user_row.get_text().strip()
        s.sync_folder = self.folder_row.get_text().strip()
        password = self.password_row.get_text()
        if not s.sync_url:
            raise SyncError("Enter the server address.")
        self.window.save_settings()
        if s.sync_user and password:
            keyring.store(s.sync_url, s.sync_user, password)
        source = WebDav(s.sync_url, s.sync_user, password, s.sync_folder)
        return source, f"webdav:{s.sync_url}|{s.sync_user}|{s.sync_folder}"

    def read(self, wait=False):
        """Read the folder in a thread; `wait` reads at once (tests)."""
        self.banner.set_revealed(False)
        try:
            source, key = self._source()
        except SyncError as error:
            self._show_error(str(error))
            return
        self.read_button.set_sensitive(False)
        self.import_button.set_sensitive(False)
        self.spinner.set_visible(True)

        def work():
            try:
                result = reader.read(source)
            except SyncError as error:
                result = error
            if wait:
                self._done(key, result)
            else:
                GLib.idle_add(self._done, key, result)

        if wait:
            work()
        else:
            threading.Thread(target=work, daemon=True).start()

    def _done(self, key, result):
        self.read_button.set_sensitive(True)
        self.spinner.set_visible(False)
        if isinstance(result, SyncError):
            self.snapshot = None
            self.result.set_visible(False)
            self._show_error(str(result))
            return GLib.SOURCE_REMOVE
        s = self.settings
        seen = s.sync_seen_version if s.sync_seen_source == key else None
        self.changes = changes.since(result, seen)
        s.sync_seen_source, s.sync_seen_version = key, result.sync_version
        self.window.save_settings()
        self.snapshot, self.source_key = result, key
        self._show(result)
        return GLib.SOURCE_REMOVE

    def _show_error(self, message):
        self.banner.set_title(GLib.markup_escape_text(message))
        self.banner.set_revealed(True)

    def _show(self, snapshot):
        counts = summary.summarize(snapshot.data)
        for key, value in (("open", counts.open_tasks), ("done", counts.done_tasks),
                           ("archived", counts.archived_tasks),
                           ("projects", counts.projects), ("tags", counts.tags)):
            self.rows[key].set_label(str(value))
        found = self.changes
        if not found.complete:
            text = "More than the folder keeps"
        else:
            text = str(found.count)
        self.rows["changes"].set_label(text)
        when = snapshot.last_modified // 1000
        stamp = GLib.DateTime.new_from_unix_local(when).format("%x %H:%M") if when else ""
        self.result.set_description(
            (f"Last synced {stamp}. " if stamp else "") +
            "Read only: the folder is not changed.")
        self.result.set_visible(True)
        self.import_button.set_sensitive(True)
        log.info("sync page: %d tasks shown, %d changes since last read",
                 counts.open_tasks + counts.done_tasks, found.count)

    # --- import ---------------------------------------------------------

    def _on_import(self, *_):
        from pensum.ui.dialogs import confirm_dialog
        confirm_dialog(self.window, "Replace All Tasks?",
                       "Your tasks, projects and tracked time are replaced by "
                       "the ones in the sync folder. A copy of the current data "
                       "is kept in the backups folder. The sync folder is not "
                       "changed.", "Replace", self.import_now)

    def import_now(self):
        if self.snapshot is None:
            return
        window = self.window
        window.flush()
        ds = window.files.import_data(self.snapshot.data, window.ds)
        self.snapshot = None
        window.replace_dataset(ds)
        window.toast("Sync folder imported")
        log.info("imported sync folder: %d tasks", len(ds.data["task"]["ids"]))
