"""Read the dataset from a sync folder: v2 (`sync-data.json`) or v3
(`sync-ops.json` and the snapshot it names). Facts from Super
Productivity 20.0.0 (file-based-sync-format.ts,
file-based-sync-adapter.service.ts, file-based-sync-data.ts); see
docs/super-productivity-sync.md.

v2: every upload rewrites `state` with the uploader's full state after
its operations, so `state` is the current dataset and `recentOps` says
what changed. v3: the snapshot is rewritten only on compaction; the
operations after it are replayed with pensum.sync.replay (#30), and a
folder with an op Pensum can't apply yet is refused."""
import json
import logging
from dataclasses import dataclass, field

from pensum.store import backup
from pensum.sync import SyncError, crypto, envelope, replay

log = logging.getLogger("pensum.sync")

SYNC_FILE = "sync-data.json"
OPS_FILE = "sync-ops.json"
STATE_FILE = "sync-state.json"
STATE_BACKUP_FILE = "sync-state.json.bak"
LEGACY_META_FILE = "__meta_"


@dataclass
class Snapshot:
    format: str  # "v2" or "v3"
    sync_version: int
    last_modified: int  # ms since the epoch
    client_id: str
    data: dict  # the dataset (AppDataComplete), archives included
    ops: list = field(default_factory=list)  # recentOps, oldest first
    oldest_op_sync_version: int | None = None


def read(source, password=None):
    """The newest dataset in the folder; raises SyncError. `password`
    decrypts encrypted files."""
    cache = {}

    def decode(text):
        return envelope.decode(text, password, cache)

    ops_text = source.read(OPS_FILE)
    if ops_text is not None:
        return _read_split(source, ops_text, decode)
    text = source.read(SYNC_FILE)
    if text is None:
        if source.read(LEGACY_META_FILE) is not None:
            raise SyncError("The folder was written by Super Productivity 16 "
                            "or older. Sync it with a current Super "
                            "Productivity first.")
        raise SyncError("No Super Productivity sync files in this folder.")
    payload, _ = decode(text)
    if payload.get("version") == 3 and payload.get("format") == "split":
        raise SyncError("The folder uses Surgical sync, but its operations "
                        "file is missing.")
    if payload.get("version") != 2:
        raise SyncError(f"Unknown sync file version {payload.get('version')!r}.")
    snapshot = _snapshot("v2", payload, payload)
    log.info("read sync v2: syncVersion %s, %d tasks, %d recent ops",
             snapshot.sync_version, len(snapshot.data["task"]["ids"]),
             len(snapshot.ops))
    return snapshot


def _read_split(source, ops_text, decode):
    ops_file, _ = decode(ops_text)
    ref = ops_file.get("snapshotRef")
    if ops_file.get("version") != 3 or not isinstance(ref, dict):
        raise SyncError("The Surgical sync operations file is damaged.")
    names = [n for n in (ref.get("file"), STATE_FILE, STATE_BACKUP_FILE) if n]
    state_file = None
    for name in names:
        text = source.read(name)
        if text is None:
            continue
        try:
            candidate, _ = decode(text)
        except (envelope.NeedsPassword, crypto.WrongPassword):
            raise
        except SyncError:
            continue
        if candidate.get("syncVersion") == ref.get("syncVersion") \
                and candidate.get("vectorClock") == ref.get("vectorClock"):
            state_file = candidate
            break
    if state_file is None:
        raise SyncError("The Surgical sync snapshot is missing.")
    newer = [op for op in ops_file.get("recentOps") or []
             if (op.get("sv") or 0) > ref["syncVersion"]]
    snapshot = _snapshot("v3", ops_file, state_file)
    if newer:
        log.info("sync v3: replaying %d ops after snapshot %s", len(newer),
                 ref["syncVersion"])
        snapshot.data = replay.apply(snapshot.data, newer)
    log.info("read sync v3: syncVersion %s, %d tasks, %d recent ops",
             snapshot.sync_version, len(snapshot.data["task"]["ids"]),
             len(snapshot.ops))
    return snapshot


def _snapshot(fmt, head, holder):
    state = holder.get("state")
    if not isinstance(state, dict):
        raise SyncError("The sync file holds no data.")
    state = dict(state)
    # Older versions keep the archives next to `state`, 20.0 inside it.
    for name in ("archiveYoung", "archiveOld"):
        if state.get(name) is None and isinstance(holder.get(name), dict):
            state[name] = holder[name]
    try:
        data = backup.parse(json.dumps(state))
    except backup.BackupError as error:
        raise SyncError(f"The synced data can't be opened: {error}") from error
    ops = head.get("recentOps")
    return Snapshot(format=fmt,
                    sync_version=int(head.get("syncVersion") or 0),
                    last_modified=int(head.get("lastModified") or 0),
                    client_id=str(head.get("clientId") or ""),
                    data=data,
                    ops=ops if isinstance(ops, list) else [],
                    oldest_op_sync_version=head.get("oldestOpSyncVersion"))
