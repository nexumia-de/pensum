"""Moves inside one id list, as Super Productivity's helpers make them
(`util/array-move.ts`, `work-context-meta.helper.ts`, read at commit
9980fd76): the menu's one step up or down, to the start or the end, and a
drop after an anchor. The step functions return a new list (the same one
when nothing moves); `kept` are the ids a step stops at, the not-done
tasks, the others are passed over. No GTK."""


def _at(ids, old, new):
    moved = list(ids)
    moved.insert(new, moved.pop(old))
    return moved


def left_until(ids, task_id, kept):
    """Before the nearest kept id above; first when there is none."""
    if task_id not in ids:
        return ids
    old = ids.index(task_id)
    new = old - 1
    while new > 0 and ids[new] not in kept:
        new -= 1
    return _at(ids, old, new) if new >= 0 else ids


def right_until(ids, task_id, kept):
    """After the nearest kept id below; unmoved when there is none."""
    if task_id not in ids:
        return ids
    old = ids.index(task_id)
    new = old + 1
    while new < len(ids) and ids[new] not in kept:
        new += 1
    return _at(ids, old, new) if new < len(ids) else ids


def undone_up(ids, task_id, undone):
    """A list's own order, one up (moveUndoneTaskUpInList): as
    `left_until`, unless the not-done task right above in `undone` is
    missing from `ids`; then into its slot, after the nearest earlier one."""
    if task_id not in undone or undone[0] == task_id or task_id not in ids:
        return left_until(ids, task_id, set(undone))
    own, old = undone.index(task_id), ids.index(task_id)
    stop = old - 1
    while stop >= 0 and ids[stop] not in undone:
        stop -= 1
    if stop < 0 or undone.index(ids[stop]) >= own - 1:
        return left_until(ids, task_id, set(undone))
    return ids if stop + 1 == old else _at(ids, old, stop + 1)


def undone_down(ids, task_id, undone):
    """The mirror of `undone_up` (moveUndoneTaskDownInList)."""
    if task_id not in undone or undone[-1] == task_id or task_id not in ids:
        return right_until(ids, task_id, set(undone))
    own, old = undone.index(task_id), ids.index(task_id)
    stop = old + 1
    while stop < len(ids) and ids[stop] not in undone:
        stop += 1
    if stop >= len(ids) or undone.index(ids[stop]) <= own + 1:
        return right_until(ids, task_id, set(undone))
    return ids if stop - 1 == old else _at(ids, old, stop - 1)


def to_start(ids, task_id):
    return _at(ids, ids.index(task_id), 0) if task_id in ids else ids


def to_end(ids, task_id):
    return _at(ids, ids.index(task_id), len(ids) - 1) if task_id in ids else ids


def swap(ids, task_id, step):
    """A subtask one place up or down (arrayMoveLeft, arrayMoveRight)."""
    if task_id not in ids:
        return ids
    old = ids.index(task_id)
    return _at(ids, old, old + step) if 0 <= old + step < len(ids) else ids


def after_anchor(ids, task_id, after_id):
    """A drop (moveItemAfterAnchor), in place: right after the anchor,
    first without one. An anchor that is gone leaves a listed id where it
    is and appends a new one."""
    rest = [i for i in ids if i != task_id]
    if after_id is None:
        ids[:] = [task_id] + rest
    elif after_id in rest:
        place = rest.index(after_id) + 1
        ids[:] = rest[:place] + [task_id] + rest[place:]
    elif task_id not in ids:
        ids.append(task_id)
