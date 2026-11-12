"""Reading a Super Productivity sync folder, read-only
(docs/super-productivity-sync.md): the sources (a local folder, WebDAV),
the file envelope, the v2 and v3 files and the operations in them. Pensum
never writes to a sync folder. No GTK."""


class SyncError(Exception):
    """The folder can't be read; the message says why, for the user."""
