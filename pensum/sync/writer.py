"""Send Day Planner's task edits to a Super Productivity sync folder (#30,
docs/decisions/sync-writing.md): the first writing step, for one Day
Planner and one Super Productivity on a v2 or v3 folder.

- What is sent: changes of a task's title, notes, done state and
  estimate since the folder was last read into Day Planner (the base),
  each as the op Super Productivity itself writes for such an edit,
  `[Task Shared] updateTask` (code HU, payload `{actionPayload: {task:
  {id, changes}}, entityChanges: []}`; read in its sync files at
  20.0.0). Any other difference to the base (a new or deleted task,
  tracked time, a moved task, another slice) is not sent: nothing is
  written and the reasons are told.
- How: the ops go to the end of `recentOps` with `sv` = the new
  `syncVersion` (previous + 1); their vector clock is the folder's
  clock with Day Planner's own counter raised, so they follow
  everything the folder had. In a v2 file `state` becomes the old state
  with the ops applied by `pensum.sync.replay`, the same rules Super
  Productivity's reducers apply; in v3 only `sync-ops.json` changes
  (the snapshot stays). Compression and encryption stay as they were.
  The file is replaced only if it is still the version read (WebDAV
  If-Match, else the content compared).
- When the folder changed since the base, the changes since are in
  `recentOps`; if one of them names a task Day Planner changed, nothing
  is sent (a conflict; read and import the folder first).
No GTK."""
import copy
import secrets
import time
from dataclasses import dataclass

from pensum.i18n import _
from pensum.sync import SyncError, envelope, reader, replay

WRITABLE = ("title", "notes", "isDone", "timeEstimate")
FOLLOWS = ("modified", "doneOn")  # change along with the writable ones
LOCAL_ONLY = {"task": ("currentTaskId", "lastCurrentTaskId")}
MAX_RECENT_OPS = 2000  # FILE_BASED_SYNC_CONSTANTS.MAX_RECENT_OPS
MAX_CLOCK_ENTRIES = 20
ID_ALPHABET = "useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict"


class Blocked(SyncError):
    """Day Planner has changes it can't send yet, or the folder conflicts."""


@dataclass
class Sent:
    count: int
    sync_version: int
    data: dict  # the folder's dataset after the send, as Day Planner reads it


def new_client_id():
    return "".join(secrets.choice(ID_ALPHABET) for _i in range(8))


def uuid7(now_ms=None):
    """A UUID version 7 (time-ordered), as Super Productivity's op ids."""
    ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    value = (ms & ((1 << 48) - 1)) << 80 | 0x7 << 76 | secrets.randbits(12) << 64 \
        | 0b10 << 62 | secrets.randbits(62)
    text = f"{value:032x}"
    return f"{text[:8]}-{text[8:12]}-{text[12:16]}-{text[16:20]}-{text[20:]}"


# --- what changed --------------------------------------------------------

def _without(slice_, name):
    if not isinstance(slice_, dict):
        return slice_
    return {k: v for k, v in slice_.items() if k not in LOCAL_ONLY.get(name, ())}


def local_changes(base, local):
    """([(task id, {field: value})], [reasons nothing can be sent])."""
    blocked = []
    for name in sorted(set(base) | set(local)):
        if name == "task" or _without(base.get(name), name) == _without(local.get(name), name):
            continue
        blocked.append(_("changes in {part}").format(part=name))
    before, after = base["task"]["entities"], local["task"]["entities"]
    if set(before) != set(after):
        blocked.append(_("tasks added or deleted"))
    changes = []
    for task_id in [i for i in local["task"]["ids"] if i in before and i in after]:
        old, new = before[task_id], after[task_id]
        fields = {k for k in set(old) | set(new) if old.get(k) != new.get(k)} - set(FOLLOWS)
        other = sorted(fields - set(WRITABLE))
        if other:
            blocked.append(_("a task's {fields}").format(fields=", ".join(other)))
            continue
        if fields:
            change = {k: new.get(k) for k in sorted(fields)}
            if "isDone" in change and change["isDone"]:
                change["doneOn"] = new.get("doneOn")
            changes.append((task_id, change))
    return changes, list(dict.fromkeys(blocked))


def build_ops(changes, clock, client_id, schema_version, now_ms):
    """Compact `updateTask` ops, each after the folder's clock."""
    clock = dict(clock or {})
    found = []
    for task_id, change in changes:
        clock[client_id] = clock.get(client_id, 0) + 1
        if len(clock) > MAX_CLOCK_ENTRIES:
            keep = sorted((k for k in clock if k != client_id), key=lambda k: -clock[k])
            clock = {k: clock[k] for k in keep[:MAX_CLOCK_ENTRIES - 1]} | {
                client_id: clock[client_id]}
        found.append({"id": uuid7(now_ms), "a": "HU", "o": "UPD", "e": "TASK",
                      "p": {"actionPayload": {"task": {"id": task_id, "changes": change}},
                            "entityChanges": []},
                      "c": client_id, "v": dict(clock), "t": now_ms, "s": schema_version,
                      "d": task_id, "ds": [task_id]})
    return found, clock


def _touched(op):
    return set(op.get("ds") or ()) | ({op["d"]} if op.get("d") else set())


def _append(payload, ops, sync_version):
    recent = list(payload.get("recentOps") or []) + [dict(op, sv=sync_version) for op in ops]
    while len(recent) > MAX_RECENT_OPS:  # trim whole batches (#10973)
        first = recent[0].get("sv")
        recent = [op for op in recent if op.get("sv") != first]
    payload["recentOps"] = recent
    if recent:
        payload["oldestOpSyncVersion"] = recent[0].get("sv", sync_version)
        payload["oldestBatchComplete"] = True


# --- sending -------------------------------------------------------------

def send(source, password, local, base, base_version, client_id, now_ms=None):
    """Write Day Planner's task edits since `base` (the dataset read at
    `base_version`) to the folder. Returns Sent; raises Blocked, or
    SyncError when the folder can't be read or written."""
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    changes, blocked = local_changes(base, local)
    if blocked:
        raise Blocked(_("Day Planner can send only changed titles, notes, done "
                        "states and estimates so far. Not sendable: {reasons}. "
                        "Export a backup to keep them.").format(reasons="; ".join(blocked)))
    if not changes:
        return Sent(0, base_version, base)
    name = reader.OPS_FILE
    text, version = source.read_versioned(name)
    if text is None:
        name = reader.SYNC_FILE
        text, version = source.read_versioned(name)
    if text is None:
        raise SyncError(_("No Super Productivity sync files in this folder."))
    compressed, encrypted, model = envelope.flags(text)
    payload, _version = envelope.decode(text, password)
    if payload.get("version") == 3 and payload.get("format") == "split":
        raise SyncError(_("The folder was moved to split sync files; read it again."))
    current = int(payload.get("syncVersion") or 0)
    if current != base_version:
        since = [op for op in payload.get("recentOps") or [] if (op.get("sv") or 0) > base_version]
        if (payload.get("oldestOpSyncVersion") or 1) > base_version + 1:
            raise Blocked(_("The sync folder changed more than it keeps track of. "
                            "Read it and import it first."))
        mine = {task_id for task_id, _c in changes}
        if any(_touched(op) & mine for op in since):
            raise Blocked(_("Super Productivity changed the same tasks. Read the "
                            "folder and import it first."))
    ops, clock = build_ops(changes, payload.get("vectorClock"), client_id,
                           payload.get("schemaVersion") or 1, now_ms)
    new = copy.deepcopy(payload)
    new_version = current + 1
    _append(new, ops, new_version)
    new.update(syncVersion=new_version, vectorClock=clock, lastModified=now_ms,
               clientId=client_id)
    if name == reader.SYNC_FILE:
        new["state"] = replay.apply(payload["state"], ops, now_ms)
    source.write(name, envelope.encode(new, model, compressed, encrypted, password), version)
    data = reader.read(source, password).data
    return Sent(len(ops), new_version, data)
