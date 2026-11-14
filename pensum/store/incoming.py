"""Before an import replaces the dataset: what the current dataset has
that the file lacks, and keeping a plugin's records that exist only on
this device through the import. No GTK.

Without sync (M4) an import replaces everything, so this is a warning,
not a merge: tasks are never merged; plugin records are kept one entry
id at a time, the way Super Productivity merges plugin data in sync."""
import copy
from dataclasses import dataclass

TASK_SOURCES = ("task", "archiveYoung", "archiveOld")


def _tasks(data):
    """Every task by id: live ones and both archives (a task finished
    since the other side's export counts as the same task)."""
    found = {}
    for source in TASK_SOURCES:
        part = data.get(source) or {}
        if source != "task":
            part = part.get("task") or {}
        entities = part.get("entities")
        if isinstance(entities, dict):
            for task_id, task in entities.items():
                if isinstance(task, dict):
                    found.setdefault(task_id, task)
    return found


def changed_at(task):
    """The newest moment the task records: made, changed or done."""
    return max((value for value in (task.get(key) for key in ("created", "modified", "doneOn"))
                if isinstance(value, (int, float)) and not isinstance(value, bool)),
               default=0)


def _comparable(task):
    """Finish Day drops these fields; a task is the same without them."""
    return {key: value for key, value in task.items()
            if key not in ("dueDay", "dueWithTime", "reminderId", "_hideSubTasksMode")}


def _entries(data):
    entries = data.get("pluginUserData")
    return entries if isinstance(entries, list) else []


def records(data, prefix):
    """Entry id → stored text of a plugin's records (`''` withdrawn)."""
    return {entry["id"]: entry.get("data") for entry in _entries(data)
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            and entry["id"].startswith(prefix)}


@dataclass(frozen=True)
class Loss:
    """What importing the file would lose of the current dataset."""
    tasks: tuple = ()        # ids of tasks made, changed or done after the file's version
    records: tuple = ()      # entry ids of records whose newer value the file replaces
    completions: tuple = ()  # (task id, doneOn) of lost completions of a journey's task
    unrelated: bool = False  # the file shares no task with the current dataset

    def __bool__(self):
        return bool(self.tasks or self.records)


def compare(current, incoming, prefix="", journey=frozenset()):
    """What the current dataset has that `incoming` lacks.

    A task is lost when the file lacks it or holds a different version,
    and the current one was made, changed or done later than the file's
    version (a missing task: later than the file's newest change; older
    ones were deleted on the other side). When the two share no task at
    all, the file is another dataset and every current task is lost.
    A record of `prefix` present on both sides with different values is
    lost when the file is older than the current dataset; records only
    here are kept (keep_records), so they are not lost. `journey` holds
    the ids of the journey's tasks and repeat rules: their lost
    completions are listed on their own."""
    mine, theirs = _tasks(current), _tasks(incoming)
    unrelated = bool(mine) and not (mine.keys() & theirs.keys())
    newest_theirs = max(map(changed_at, theirs.values()), default=0)
    newest_mine = max(map(changed_at, mine.values()), default=0)
    lost = []
    for task_id, task in mine.items():
        other = theirs.get(task_id)
        if unrelated:
            lost.append(task_id)
        elif other is None:
            if changed_at(task) > newest_theirs:
                lost.append(task_id)
        elif _comparable(task) != _comparable(other) and changed_at(task) > changed_at(other):
            lost.append(task_id)
    completions = tuple(
        (task_id, mine[task_id]["doneOn"]) for task_id in lost
        if mine[task_id].get("isDone") and isinstance(mine[task_id].get("doneOn"), (int, float))
        and (task_id in journey or mine[task_id].get("repeatCfgId") in journey))
    lost_records = ()
    if prefix and (lost or newest_mine > newest_theirs):
        here, there = records(current, prefix), records(incoming, prefix)
        lost_records = tuple(sorted(key for key, value in here.items()
                                    if key in there and there[key] != value))
    return Loss(tuple(lost), lost_records,
                tuple(sorted(completions, key=lambda item: item[1])), unrelated)


def keep_records(current, incoming, prefix):
    """Add the records of `prefix` that only the current dataset has to
    `incoming`; a record on both sides keeps the file's value (also a
    withdrawn one, `''`). Returns the kept entry ids."""
    there = records(incoming, prefix)
    kept = [entry for entry in _entries(current)
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            and entry["id"].startswith(prefix) and entry["id"] not in there]
    if kept:
        if not isinstance(incoming.get("pluginUserData"), list):
            incoming["pluginUserData"] = []
        incoming["pluginUserData"].extend(copy.deepcopy(kept))
    return [entry["id"] for entry in kept]
