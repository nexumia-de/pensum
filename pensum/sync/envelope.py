"""The envelope of every sync file: `pf_` + `C` if compressed + `E` if
encrypted + a model version + `__`, then the payload (Super
Productivity's sync-file-prefix.ts, read at 20.0.0); decryption and
decompression in pensum.sync.crypto."""
import json
import re

from pensum.i18n import _
from pensum.sync import SyncError, crypto

PREFIX = re.compile(r"^pf_(C)?(E)?(\d+(?:\.\d+)?)__")


class NeedsPassword(SyncError):
    """The files are encrypted and no password was given."""


def flags(text):
    """(compressed, encrypted, model version) of a sync file's prefix."""
    match = PREFIX.match(text)
    if not match:
        raise SyncError(_("A sync file is not in Super Productivity's format."))
    compressed, encrypted, version = match.groups()
    return bool(compressed), bool(encrypted), version


def encode(payload, version, compressed=False, encrypted=False, password=None):
    """A sync file as Super Productivity writes it: compressed before
    encrypted, the prefix naming both (#30)."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if compressed:
        body = crypto.compress(body)
    if encrypted:
        if not password:
            raise NeedsPassword(_("The sync files are encrypted. Enter the "
                                  "encryption password set in Super Productivity."))
        body = crypto.encrypt(body, password)
    return f"pf_{'C' if compressed else ''}{'E' if encrypted else ''}{version}__{body}"


def decode(text, password=None, cache=None):
    """The JSON object a sync file carries, and its model version.
    `cache` keeps derived keys between the files of one read."""
    match = PREFIX.match(text)
    if not match:
        raise SyncError(_("A sync file is not in Super Productivity's format."))
    compressed, encrypted, version = match.groups()
    body = text[match.end():]
    if encrypted:
        if not password:
            raise NeedsPassword(_("The sync files are encrypted. Enter the "
                                  "encryption password set in Super Productivity."))
        body = crypto.decrypt(body, password, cache)
    if compressed:
        body = crypto.decompress(body)
    try:
        payload = json.loads(body)
    except ValueError as error:
        raise SyncError(_("A sync file is damaged (no JSON).")) from error
    if not isinstance(payload, dict):
        raise SyncError(_("A sync file is damaged."))
    return payload, float(version)
