"""The WebDAV password and the sync encryption password in the system keyring (libsecret; in the Flatpak
through the Secret portal), never in Pensum's own files. When no keyring
is available the password is used once and not remembered."""
import logging

log = logging.getLogger("pensum.sync")

SCHEMA_NAME = "de.nexumia.Pensum.WebDav"


def _secret():
    try:
        import gi
        gi.require_version("Secret", "1")
        from gi.repository import Secret
    except (ImportError, ValueError):
        return None
    return Secret


def _schema(Secret):
    return Secret.Schema.new(SCHEMA_NAME, Secret.SchemaFlags.NONE,
                             {"url": Secret.SchemaAttributeType.STRING,
                              "user": Secret.SchemaAttributeType.STRING})


def lookup(url, user):
    """The stored password, or None."""
    Secret = _secret()
    if Secret is None:
        return None
    try:
        return Secret.password_lookup_sync(_schema(Secret), {"url": url, "user": user}, None)
    except Exception as error:  # GLib.Error: no keyring, locked, cancelled
        log.info("keyring lookup failed: %s", type(error).__name__)
        return None


def store(url, user, password):
    """True when the keyring took the password."""
    Secret = _secret()
    if Secret is None:
        return False
    try:
        return Secret.password_store_sync(
            _schema(Secret), {"url": url, "user": user}, Secret.COLLECTION_DEFAULT,
            "Day Planner: sync folder", password, None)
    except Exception as error:
        log.info("keyring store failed: %s", type(error).__name__)
        return False
