"""The dataset as it was read from a sync folder into Day Planner, the
base that Day Planner's own edits are measured against when it sends
them (#30, pensum.sync.writer). Kept next to the data file as
`sync-base.json` with the folder's key and syncVersion; a base of
another folder does not count. No GTK."""
import json
import os

NAME = "sync-base.json"


def _path(files):
    return files.directory / NAME


def save(files, key, sync_version, data):
    path = _path(files)
    temporary = path.with_name(NAME + ".tmp")
    temporary.write_text(json.dumps({"source": key, "syncVersion": sync_version,
                                     "data": data}, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def load(files, key):
    """(syncVersion, dataset) of the base for this folder, or None."""
    try:
        found = json.loads(_path(files).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(found, dict) or found.get("source") != key:
        return None
    return int(found.get("syncVersion") or 0), found.get("data")
