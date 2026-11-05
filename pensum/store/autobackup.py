"""Automatic backups next to the data file, named and kept like Super
Productivity's desktop backups (backups/YYYY-MM-DD_HHMMSS.json, the bare
dataset; the newest 30 plus one per day for 21 days). No GTK."""
import json
from datetime import datetime
from pathlib import Path

KEEP_RECENT = 30
KEEP_DAILY_DAYS = 21
MIN_INTERVAL_S = 15 * 60


def backup_name(moment=None):
    return (moment or datetime.now()).strftime("%Y-%m-%d_%H%M%S") + ".json"


def listing(directory):
    """Backup files, newest first."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    return sorted((p for p in directory.glob("*.json") if p.is_file()),
                  key=lambda p: p.name, reverse=True)


def due(directory, moment=None):
    """True when the newest backup is older than the interval."""
    files = listing(directory)
    if not files:
        return True
    moment = moment or datetime.now()
    try:
        newest = datetime.strptime(files[0].stem, "%Y-%m-%d_%H%M%S")
    except ValueError:
        return True
    return (moment - newest).total_seconds() >= MIN_INTERVAL_S


def write(directory, data, moment=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / backup_name(moment)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")),
                   encoding="utf-8")
    tmp.replace(path)
    prune(directory)
    return path


def prune(directory):
    files = listing(directory)
    keep = set(files[:KEEP_RECENT])
    days = []
    for path in files:
        day = path.name[:10]
        if day not in days:
            days.append(day)
            if len(days) <= KEEP_DAILY_DAYS:
                keep.add(path)
    for path in files:
        if path not in keep:
            path.unlink(missing_ok=True)
