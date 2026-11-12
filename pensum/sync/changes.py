"""What changed in a sync folder since Pensum last read it, from the
operations in `recentOps` (compact ops: `o` op type, `e` entity type,
`d`/`ds` entity ids, `sv` the syncVersion an op arrived in;
compact-operation.types.ts in Super Productivity 20.0.0)."""
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class Changes:
    count: int = 0
    # False when the file no longer holds every op since that version.
    complete: bool = True
    by_entity: Counter = field(default_factory=Counter)
    task_ids: set = field(default_factory=set)


def since(snapshot, sync_version):
    """The operations that arrived after `sync_version`."""
    changes = Changes()
    if sync_version is None or sync_version >= snapshot.sync_version:
        return changes
    oldest = snapshot.oldest_op_sync_version
    if oldest is not None and oldest > sync_version + 1:
        changes.complete = False
    for op in snapshot.ops:
        if (op.get("sv") or 0) <= sync_version:
            continue
        changes.count += 1
        entity = op.get("e") or "?"
        changes.by_entity[entity] += 1
        if entity == "TASK":
            ids = list(op.get("ds") or ([op["d"]] if op.get("d") else []))
            if op.get("o") == "DEL":
                # Deleting a task deletes its subtasks with one op that
                # names only the parent; its payload carries the task.
                ids += _subtask_ids(op.get("p"))
            changes.task_ids.update(i for i in ids if isinstance(i, str))
    return changes


def _subtask_ids(payload):
    task = ((payload or {}).get("actionPayload") or {}).get("task") \
        if isinstance(payload, dict) else None
    subs = task.get("subTaskIds") if isinstance(task, dict) else None
    return subs if isinstance(subs, list) else []
