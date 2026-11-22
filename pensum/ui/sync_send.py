"""Sending Day Planner's task edits to the sync folder from the sync page
(#30, pensum.sync.writer): **Send Changes** works in a thread and then
takes the folder's data as Day Planner's, so both show the same; the
base for the next send is kept (pensum.sync.base). With Git Sync a send
that did not reach the desktop is sent again (pensum.sync.github). Logs
counts only."""
import copy
import logging
import threading

from gi.repository import GLib

from pensum.i18n import _
from pensum.store.dataset import Dataset
from pensum.sync import SyncError, base, reader, writer

log = logging.getLogger("pensum.sync")


def keep_base(window, key, sync_version):
    """After an import or a send: what Day Planner holds now is the base."""
    try:
        base.save(window.files, key, sync_version, window.ds.data)
    except OSError as error:
        log.warning("sync base not saved: %s", error)


def send(page, wait=False):
    window, s = page.window, page.settings
    try:
        source, key = page._source()
        password = page._encryption_password(key)
    except SyncError as error:
        page._show_error(str(error))
        return
    found = base.load(window.files, key)
    if found is None:
        page._show_error(_("Read the folder and import it once before sending changes."))
        return
    if not s.sync_client_id:
        s.sync_client_id = writer.new_client_id()
        window.save_settings()
    window.flush()
    version, base_data = found
    local = copy.deepcopy(window.ds.data)
    page.send_button.set_sensitive(False)
    page.spinner.set_visible(True)

    def work():
        try:
            base_version, base_dataset = _stale_base(source, password) or (version, base_data)
            result = writer.send(source, password, local, base_dataset, base_version,
                                 s.sync_client_id)
        except SyncError as error:
            result = error
        if wait:
            _done(page, key, result)
        else:
            GLib.idle_add(_done, page, key, result)

    if wait:
        work()
    else:
        threading.Thread(target=work, daemon=True).start()


def _stale_base(source, password):
    """Git Sync (pensum.sync.github): when Day Planner's last send did not
    reach the desktop, the data it was built on is the base again, so the
    edits of that send go out once more with the new ones."""
    stale = getattr(source, "stale_base", None)
    at = stale() if stale else None
    if at is None:
        return None
    snapshot = reader.read(at, password)
    log.info("last send not delivered; sending again from syncVersion %d",
             snapshot.sync_version)
    return snapshot.sync_version, snapshot.data


def _done(page, key, result):
    window = page.window
    page.send_button.set_sensitive(True)
    page.spinner.set_visible(False)
    if isinstance(result, SyncError):
        page._show_error(str(result))
        return GLib.SOURCE_REMOVE
    if result.count:
        window.ds.data.clear()
        window.ds.data.update(Dataset(result.data).data)
        window.changed()
        window.flush()
        page.settings.sync_seen_source, page.settings.sync_seen_version = key, result.sync_version
        window.save_settings()
        keep_base(window, key, result.sync_version)
    window.toast(_("No changes to send") if not result.count else
                 _("1 change sent") if result.count == 1 else
                 _("{count} changes sent").format(count=result.count))
    log.info("sent %d changes, syncVersion %d", result.count, result.sync_version)
    return GLib.SOURCE_REMOVE
