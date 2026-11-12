"""The envelope of every sync file: `pf_` + `C` if compressed + `E` if
encrypted + a model version + `__`, then the payload (Super
Productivity's sync-file-prefix.ts, read at 20.0.0)."""
import json
import re

from pensum.sync import SyncError

PREFIX = re.compile(r"^pf_(C)?(E)?(\d+(?:\.\d+)?)__")


def decode(text):
    """The JSON object a sync file carries, and its model version."""
    match = PREFIX.match(text)
    if not match:
        raise SyncError("A sync file is not in Super Productivity's format.")
    compressed, encrypted, version = match.groups()
    if encrypted:
        raise SyncError("The sync files are encrypted. Pensum can't read "
                        "encrypted sync files yet.")
    if compressed:
        raise SyncError("The sync files are compressed. Pensum can't read "
                        "compressed sync files yet; switch compression off in "
                        "Super Productivity's sync settings.")
    try:
        payload = json.loads(text[match.end():])
    except ValueError as error:
        raise SyncError("A sync file is damaged (no JSON).") from error
    if not isinstance(payload, dict):
        raise SyncError("A sync file is damaged.")
    return payload, float(version)
