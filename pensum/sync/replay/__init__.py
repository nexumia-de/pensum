"""Apply Super Productivity's operations to a dataset, read-only (#30):
the rules its reducers follow when another device's op is replayed,
transcribed from Super Productivity 20.0.0 (root-store/meta/
task-shared-meta-reducers/, features/tasks/store/task.reducer*.ts,
features/config/store/global-config.reducer.ts). Only the actions
listed in SUPPORTED are applied; any other op makes the whole replay
fail with Unsupported, never a guess. No GTK."""
import copy

from pensum.store import dates
from pensum.sync import SyncError
from pensum.sync.replay import config, ops, tasks


class Unsupported(SyncError):
    """An op Pensum can't apply yet."""

    def __init__(self, action, detail=""):
        self.action = action
        super().__init__(f"The data contains a change Pensum can't apply yet "
                         f"({action}{': ' + detail if detail else ''}).")


SUPPORTED = {
    "[Task Shared] addTask": tasks.add_task,
    "[Task Shared] updateTask": tasks.update_task,
    "[Task Shared] deleteTask": tasks.delete_task,
    "[Task] Add SubTask": tasks.add_subtask,
    "[Global Config] Update Global Config Section": config.update_section,
}


def apply(data, operations, now_ms=None):
    """A new dataset: `data` with `operations` (compact or full ops, in
    order) applied. Raises Unsupported for an op outside SUPPORTED."""
    data = copy.deepcopy(data)
    now_ms = dates.now_ms() if now_ms is None else now_ms
    for op in operations:
        action, payload = ops.unpack(op)
        handler = SUPPORTED.get(action)
        if handler is None:
            raise Unsupported(action)
        try:
            handler(data, payload, now_ms)
        except tasks.Refused as refused:
            raise Unsupported(action, str(refused)) from refused
    return data
