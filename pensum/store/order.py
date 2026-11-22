"""The order of tasks in a list: the id lists Super Productivity keeps for
it (`project.taskIds` and `backlogTaskIds`, `tag.taskIds`, `TODAY.taskIds`,
a parent's `subTaskIds`, a section's `taskIds`). Moving a task rewrites
those that order it, by the rules of Super Productivity's reducers
(docs/super-productivity-data.md, Order), and nothing else. No GTK."""
from pensum.store import list_moves, sections
from pensum.store.defaults import TODAY_ID


def _context_order(ds, context, today):
    """The stored order of a list's main part, with every shown task in it."""
    if context.kind == "project":
        return ds.project_entities[context.id]["taskIds"]
    if context.kind == "tag":
        order = ds.tag_entities[context.id]["taskIds"]
    elif TODAY_ID in ds.tag_entities:
        order = ds.tag_entities[TODAY_ID]["taskIds"]
    else:
        order = []
    for i in ds.top_level_ids(context, today):
        if i not in order:
            order.append(i)
    return order


def _is_done(ds, task_id):
    return bool((ds.tasks.get(task_id) or {}).get("isDone"))


def _place_of(ds, task_id, context, today):
    """Where a task is ordered: ("sub", parent), ("backlog", project),
    ("section", section) for an open task in a section, ("list", None) for
    another task of the list's main part, or (None, None)."""
    task = ds.tasks.get(task_id)
    if not task:
        return None, None
    parent = ds.tasks.get(task.get("parentId"))
    if parent:
        return "sub", parent
    if context is None:
        return None, None
    if context.kind == "project":
        project = ds.project_entities.get(context.id, {})
        if task_id in project.get("backlogTaskIds", []):
            return "backlog", project
    if task_id not in ds.top_level_ids(context, today):
        return None, None
    section = sections.section_of(ds, context, task_id)
    if section is not None and not task.get("isDone"):
        return "section", section
    return "list", None


def siblings(ds, task_id, context, today=None):
    """The ids a task is shown and moved among, in their order, itself
    included: a parent's subtasks, a backlog, the open tasks of a section,
    the open tasks in no section, or the done tasks. Empty when the list
    does not order the task (an overdue task, or one Today lists by time)."""
    kind, owner = _place_of(ds, task_id, context, today)
    if kind == "sub":
        return list(owner["subTaskIds"])
    if kind == "backlog":
        return list(owner["backlogTaskIds"])
    if kind is None:
        return []
    shown = ds.top_level_ids(context, today)
    if kind == "section":
        return [i for i in owner["taskIds"] if i in shown and not _is_done(ds, i)]
    if _is_done(ds, task_id):
        return [i for i in shown if _is_done(ds, i)]
    placed = {i for s in sections.of_context(ds, context) for i in s.get("taskIds", ())}
    shown = [i for i in shown if i not in placed and not _is_done(ds, i)]
    if context.kind == "today":
        # Today shows the tasks with a time by their time, not by this order.
        shown = [i for i in shown if not ds.has_time(ds.tasks[i])]
    return shown if task_id in shown else []


def _not_done(ds, ids):
    """Super Productivity's not-done ids of a list: every id whose task is
    not done, ids without a task included."""
    return [i for i in ids if not _is_done(ds, i)]


def _step(ds, task_id, context, today, kind, owner, how):
    """One menu move as Super Productivity applies it; `how` is "up",
    "down", "top" or "bottom". Changes the stored lists in place."""
    if kind == "sub":
        ids = owner["subTaskIds"]
        ids[:] = {"up": lambda: list_moves.swap(ids, task_id, -1),
                  "down": lambda: list_moves.swap(ids, task_id, 1),
                  "top": lambda: list_moves.to_start(ids, task_id),
                  "bottom": lambda: list_moves.to_end(ids, task_id)}[how]()
        return
    if kind == "backlog":
        ids = owner["backlogTaskIds"]
        kept = set(_not_done(ds, ids))
        ids[:] = {"up": lambda: list_moves.left_until(ids, task_id, kept),
                  "down": lambda: list_moves.right_until(ids, task_id, kept),
                  "top": lambda: list_moves.to_start(ids, task_id),
                  "bottom": lambda: list_moves.to_end(ids, task_id)}[how]()
        return
    own = _context_order(ds, context, today)
    undone = _not_done(ds, own)
    # The section that lists the task moves it too, done or not; the list's
    # own order always does (section-shared.reducer.ts, then the project's
    # or tag's reducer).
    section = sections.section_of(ds, context, task_id)
    if section is not None:
        ids = section["taskIds"]
        kept = set(undone)
        ids[:] = {"up": lambda: list_moves.left_until(ids, task_id, kept),
                  "down": lambda: list_moves.right_until(ids, task_id, kept),
                  "top": lambda: list_moves.to_start(ids, task_id),
                  "bottom": lambda: list_moves.to_end(ids, task_id)}[how]()
    own[:] = {"up": lambda: list_moves.undone_up(own, task_id, undone),
              "down": lambda: list_moves.undone_down(own, task_id, undone),
              "top": lambda: list_moves.to_start(own, task_id),
              "bottom": lambda: list_moves.to_end(own, task_id)}[how]()


def _stored(ds, context, today, kind, owner, task_id):
    """The id lists a menu move can change, to compare and to put back."""
    if kind == "sub":
        return [owner["subTaskIds"]]
    if kind == "backlog":
        return [owner["backlogTaskIds"]]
    found = [_context_order(ds, context, today)]
    section = sections.section_of(ds, context, task_id)
    if section is not None:
        found.append(section["taskIds"])
    return found


def move(ds, task_id, context, offset, today=None):
    """Move a task one place up (-1) or down (1) among the tasks it is shown
    with, or with a large offset to the top or the bottom, by Super
    Productivity's menu moves. Where its step passes only tasks that are
    shown elsewhere (done ones, sectioned ones, Today's timed ones), the
    step is repeated until the task has passed a shown one. Returns True
    when it moved; nothing is written when it could not."""
    kind, owner = _place_of(ds, task_id, context, today)
    shown = siblings(ds, task_id, context, today)
    if kind is None or task_id not in shown or len(shown) < 2 or not offset:
        return False
    lists = _stored(ds, context, today, kind, owner, task_id)
    before = [list(ids) for ids in lists]
    if abs(offset) >= len(shown):
        how = "top" if offset < 0 else "bottom"
        if shown[0 if offset < 0 else -1] == task_id:
            return False
        _step(ds, task_id, context, today, kind, owner, how)
        return [list(ids) for ids in lists] != before
    how = "up" if offset < 0 else "down"
    for _ in range(abs(offset)):
        was = siblings(ds, task_id, context, today)
        for _ in range(sum(len(ids) for ids in lists) + 1):
            last = [list(ids) for ids in lists]
            _step(ds, task_id, context, today, kind, owner, how)
            if siblings(ds, task_id, context, today) != was \
                    or [list(ids) for ids in lists] == last:
                break
    if siblings(ds, task_id, context, today) == shown:
        for ids, old in zip(lists, before):
            ids[:] = old
        return False
    return True


def sectionable(ds, task_id, context, today=None):
    """A top-level task of the list's main part: only those are in sections."""
    task = ds.tasks.get(task_id)
    return bool(task) and not task.get("parentId") and sections.can_have(context) \
        and task_id in ds.top_level_ids(context, today)


def move_to(ds, task_id, context, target_id, today=None):
    """Move a task to the place of another task it is shown with (dropping
    it there); the tasks between them close the gap. A drop on an open task
    of another section, or of none, moves the task there. Returns True
    when it moved."""
    if target_id == task_id:
        return False
    kind, owner = _place_of(ds, task_id, context, today)
    target_kind, target_owner = _place_of(ds, target_id, context, today)
    shown = siblings(ds, target_id, context, today)
    if kind is None or target_id not in shown:
        return False
    if task_id not in shown:
        return _to_other_group(ds, task_id, context, target_id, shown,
                               (kind, owner), (target_kind, target_owner), today)
    place = shown.index(target_id)
    shown.remove(task_id)
    after_id = shown[place - 1] if place else None
    if kind == "sub":
        list_moves.after_anchor(owner["subTaskIds"], task_id, after_id)
    elif kind == "backlog":
        list_moves.after_anchor(owner["backlogTaskIds"], task_id, after_id)
    elif kind == "section":
        sections.place(ds, owner["id"], task_id, after_id, owner["id"])
    else:
        list_moves.after_anchor(_context_order(ds, context, today), task_id, after_id)
    return True


def _to_other_group(ds, task_id, context, target_id, shown, source, target, today):
    """A drop on an open task of another section (addTaskToSection) or of
    no section (removeTaskFromSection): the task takes the target's place."""
    open_kinds = ("section", "list")
    if source[0] not in open_kinds or target[0] not in open_kinds \
            or _is_done(ds, task_id) or _is_done(ds, target_id):
        return False
    place = shown.index(target_id)
    after_id = shown[place - 1] if place else None
    source_id = source[1]["id"] if source[0] == "section" else None
    if target[0] == "section":
        sections.place(ds, target[1]["id"], task_id, after_id, source_id)
    elif source_id is not None:
        sections.take_out(ds, source_id, task_id, context, after_id)
    else:
        return False
    return True


def to_section(ds, task_id, context, section_id, first=False, today=None):
    """Move a task into a section of its list, last or first in it, or with
    None out of its section, where it keeps its place in the list's own
    order. Returns True when it moved."""
    if not sectionable(ds, task_id, context, today):
        return False
    source = sections.section_of(ds, context, task_id)
    if (source or {}).get("id") == section_id:
        return False
    if section_id is None:
        own = _context_order(ds, context, today)
        place = own.index(task_id) if task_id in own else 0
        sections.take_out(ds, source["id"], task_id, context,
                          own[place - 1] if place else None)
        return True
    target = next((s for s in sections.of_context(ds, context)
                   if s["id"] == section_id), None)
    if target is None:
        return False
    ids = [i for i in target.get("taskIds", ()) if i != task_id]
    sections.place(ds, section_id, task_id, None if first or not ids else ids[-1],
                   (source or {}).get("id"))
    return True
