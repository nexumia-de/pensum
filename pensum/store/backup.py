"""Super Productivity backup files: read a backup (the "Export data" file,
an automatic backup, or Pensum's own data file) and write one that
Super Productivity can import. No GTK."""
import json
import os
from pathlib import Path

from pensum.store import defaults

# Slices a backup must carry; the others are filled with their empty
# state, as Super Productivity does (withDefaultModelSlices).
CORE_SLICES = ("task", "project", "tag", "globalConfig")


class BackupError(Exception):
    """The file is not a backup Pensum can open; the message says why."""


def parse(text):
    """The dataset (AppDataComplete) from a backup's JSON text."""
    try:
        raw = json.loads(text)
    except ValueError as error:
        raise BackupError("The file is not a Super Productivity backup "
                          "(no JSON).") from error
    if not isinstance(raw, dict):
        raise BackupError("The file is not a Super Productivity backup.")
    if "data" in raw and "crossModelVersion" in raw:
        version = raw.get("crossModelVersion")
        if not isinstance(version, (int, float)):
            raise BackupError("The backup has no data model version.")
        if version > defaults.CROSS_MODEL_VERSION:
            raise BackupError(
                f"The backup was made by a newer Super Productivity (data "
                f"model {version}). Update Pensum to open it.")
        if version < defaults.CROSS_MODEL_VERSION:
            raise BackupError(
                f"The backup uses the old data model {version}. Import it "
                f"into Super Productivity once and export it again.")
        data = raw["data"]
    else:
        # Automatic backups of the desktop app hold the bare dataset.
        data = raw
    if not isinstance(data, dict):
        raise BackupError("The file is not a Super Productivity backup.")
    missing = [name for name in CORE_SLICES if not isinstance(data.get(name), dict)]
    if missing:
        raise BackupError("The file is not a Super Productivity backup "
                          f"(missing {', '.join(missing)}).")
    if not isinstance(data["task"].get("entities"), dict):
        raise BackupError("The backup uses an old data model. Import it into "
                          "Super Productivity once and export it again.")
    for name, empty in defaults.slices().items():
        if data.get(name) is None:
            data[name] = empty
    return data


def read(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise BackupError(f"The file can't be read: {error}") from error
    return parse(text)


def dumps(data, now):
    """The JSON text of a complete backup (CompleteBackup), as Super
    Productivity's "Export data" writes it."""
    return json.dumps({"timestamp": now, "lastUpdate": now,
                       "crossModelVersion": defaults.CROSS_MODEL_VERSION,
                       "data": data}, ensure_ascii=False, separators=(",", ":"))


def write(path, data, now):
    """Write atomically: a crash leaves the old file or the new one."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        handle.write(dumps(data, now))
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)
