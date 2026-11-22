"""Read a Super Productivity sync folder (WebDAV, Nextcloud, a folder on
this device or a GitHub repository kept by Git Sync; the form is
pensum.ui.sync_source), show what it holds and offer it as an import.
Reading never changes the folder (pensum.sync); the import replaces
Pensum's data like a backup import; Send Changes is pensum.ui.sync_send."""
import logging
import threading

from gi.repository import Adw, GLib, Gtk

from pensum.i18n import _
from pensum.sync import SyncError, changes, reader, summary
from pensum.ui import sync_source

log = logging.getLogger("pensum.sync")

class SyncPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title=_("Sync Folder"), tag="sync")
        self.window = window
        self.settings = window.settings
        self.snapshot = None
        self.source_key = ""
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        # Day Planner's task edits to the folder (#30, sync_send.py).
        self.send_button = Gtk.Button(icon_name="mail-send-symbolic",
                                      tooltip_text=_("Send Changes"))
        self.send_button.update_property([Gtk.AccessibleProperty.LABEL], [_("Send Changes")])
        self.send_button.connect("clicked", lambda *_: self.send())
        header.pack_end(self.send_button)
        toolbar.add_top_bar(header)
        self.banner = Adw.Banner()
        toolbar.add_top_bar(self.banner)
        page = Adw.PreferencesPage()
        page.add(sync_source.build_group(self))
        encryption = Adw.PreferencesGroup(
            description=_("Only when encryption is switched on in Super "
                          "Productivity's sync settings."))
        self.encryption_row = Adw.PasswordEntryRow(title=_("Encryption Password"))
        encryption.add(self.encryption_row)
        page.add(encryption)
        self.result = Adw.PreferencesGroup(title=_("In the Sync Folder"), visible=False)
        self.rows = {}
        for key, title in (("open", _("Open Tasks")), ("done", _("Done Tasks")),
                           ("archived", _("Archived Tasks")), ("projects", _("Projects")),
                           ("tags", _("Tags")),
                           ("changes", _("Changes Since Last Read"))):
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

    def _bottom_bar(self):
        bar = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER,
                      margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        self.read_button = Gtk.Button(label=_("Read Folder"), css_classes=["pill"])
        self.read_button.connect("clicked", lambda *_: self.read())
        # Adw.Spinner needs libadwaita 1.6; Ubuntu 24.04 (CI) has 1.5.
        self.spinner = (Adw.Spinner(visible=False) if hasattr(Adw, "Spinner")
                        else Gtk.Spinner(spinning=True, visible=False))
        self.import_button = Gtk.Button(label=_("Import…"), sensitive=False,
                                        css_classes=["pill", "suggested-action"])
        self.import_button.connect("clicked", self._on_import)
        bar.append(self.read_button)
        bar.append(self.spinner)
        bar.append(self.import_button)
        return bar

    def send(self, wait=False):
        from pensum.ui import sync_send
        sync_send.send(self, wait)

    def _kind(self):
        return sync_source.kind(self)

    def _on_kind_changed(self, *_):
        sync_source.on_kind_changed(self)

    # --- reading --------------------------------------------------------

    def _source(self):
        return sync_source.source(self)

    def _encryption_password(self, key):
        return sync_source.encryption_password(self, key)

    def read(self, wait=False):
        """Read the folder in a thread; `wait` reads at once (tests)."""
        self.banner.set_revealed(False)
        try:
            source, key = self._source()
            password = self._encryption_password(key)
        except SyncError as error:
            self._show_error(str(error))
            return
        self.read_button.set_sensitive(False)
        self.import_button.set_sensitive(False)
        self.spinner.set_visible(True)

        def work():
            stale = False
            try:
                result = reader.read(source, password)
                # Git Sync: Day Planner's last send did not reach the desktop.
                stale = bool(getattr(source, "is_stale", None) and source.is_stale())
            except SyncError as error:
                result = error
            if wait:
                self._done(key, result, stale)
            else:
                GLib.idle_add(self._done, key, result, stale)

        if wait:
            work()
        else:
            threading.Thread(target=work, daemon=True).start()

    def _done(self, key, result, stale=False):
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
        if stale:
            self._show_error(_("Your last sent changes did not reach Super "
                               "Productivity. Send Changes sends them again."))
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
            text = _("More than the folder keeps")
        else:
            text = str(found.count)
        self.rows["changes"].set_label(text)
        when = snapshot.last_modified // 1000
        stamp = GLib.DateTime.new_from_unix_local(when).format("%x %H:%M") if when else ""
        self.result.set_description(
            (_("Last synced {stamp}.").format(stamp=stamp) + " " if stamp else "") +
            _("Reading does not change the folder."))
        self.result.set_visible(True)
        self.import_button.set_sensitive(True)
        log.info("sync page: %d tasks shown, %d changes since last read",
                 counts.open_tasks + counts.done_tasks, found.count)

    # --- import ---------------------------------------------------------

    def _on_import(self, *args):
        from pensum.ui.dialogs import confirm_dialog
        confirm_dialog(self.window, _("Replace All Tasks?"),
                       _("Your tasks, projects and tracked time are replaced by "
                         "the ones in the sync folder. A copy of the current data "
                         "is kept in the backups folder. The sync folder is not "
                         "changed."), _("Replace"), self.import_now)

    def import_now(self):
        if self.snapshot is None:
            return
        window = self.window
        window.flush()
        ds = window.files.import_data(self.snapshot.data, window.ds)
        version = self.snapshot.sync_version
        self.snapshot = None
        window.replace_dataset(ds)
        from pensum.ui.sync_send import keep_base
        keep_base(window, self.source_key, version)
        window.toast(_("Sync folder imported"))
        log.info("imported sync folder: %d tasks", len(ds.data["task"]["ids"]))
