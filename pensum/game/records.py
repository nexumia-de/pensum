"""QuestArc's choice records, one plugin-data entry each, in the dataset's
`pluginUserData` slice: entity id `questarc:<key>`, the value as JSON
text, `GZ1:<base64 gzip>` from 1024 characters on, an empty string for
a withdrawn record (QuestArc docs/data-model.md §2, Super Productivity
plugin-data-codec). No GTK."""
import base64
import gzip
import json

PLUGIN_ID = "questarc"
PREFIX = f"{PLUGIN_ID}:"
SENTINEL = "GZ1:"
COMPRESS_FROM = 1024
MAX_DECOMPRESSED = 2 * 1024 * 1024


def _entries(ds):
    entries = ds.data.get("pluginUserData")
    if not isinstance(entries, list):
        entries = ds.data["pluginUserData"] = []
    return entries


def decode(text):
    if not isinstance(text, str) or not text.startswith(SENTINEL):
        return text
    try:
        raw = gzip.decompress(base64.b64decode(text[len(SENTINEL):]))
    except (ValueError, OSError):
        return ""
    return raw[:MAX_DECOMPRESSED].decode("utf-8", "replace")


def encode(text):
    if len(text) < COMPRESS_FROM:
        return text
    packed = gzip.compress(text.encode("utf-8"), mtime=0)
    return SENTINEL + base64.b64encode(packed).decode("ascii")


def load(ds):
    """Key → parsed value of every non-empty record; text that is not
    JSON is passed on, so the engine reports it."""
    found = {}
    for entry in _entries(ds):
        entry_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(entry_id, str) or not entry_id.startswith(PREFIX):
            continue
        text = decode(entry.get("data"))
        if not text:
            continue
        try:
            found[entry_id[len(PREFIX):]] = json.loads(text)
        except ValueError:
            found[entry_id[len(PREFIX):]] = text
    return found


def write(ds, changes):
    """Write record changes as the engine's actions return them; `''`
    withdraws a record."""
    entries = _entries(ds)
    by_id = {e.get("id"): e for e in entries if isinstance(e, dict)}
    for key, value in changes.items():
        data = "" if value == "" else encode(json.dumps(value, separators=(",", ":")))
        entry_id = PREFIX + key
        if entry_id in by_id:
            by_id[entry_id]["data"] = data
        else:
            entry = {"id": entry_id, "data": data}
            entries.append(entry)
            by_id[entry_id] = entry


def journey_ids(ds):
    """Ids of the tasks and repeat rules a journey's stages are bound to
    (`binding:<run>:<stage>` records)."""
    found = set()
    for key, value in load(ds).items():
        if key.startswith("binding:") and isinstance(value, dict):
            found.update(v for v in (value.get("taskId"), value.get("repeatCfgId"))
                         if isinstance(v, str) and v)
    return frozenset(found)
