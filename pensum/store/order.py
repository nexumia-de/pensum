"""The order of tasks in a list: the id lists Super Productivity keeps for
it (`project.taskIds` and `backlogTaskIds`, `tag.taskIds`, `TODAY.taskIds`,
a parent's `subTaskIds`, a section's `taskIds`). Moving a task rewrites
those that order it and nothing else. No GTK."""
from pensum.store import sections
from pensum.store.defaults import TODAY_ID


def _context_order(ds, context, today):
    """The stored order a list's moves change, with every shown task in it."""
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


def _lists(ds, task_id, context, today):
    """(the stored id list a task's moves change, the ids shown from it in
    their order); (None, []) when the list does not order the task."""
    task = ds.tasks.get(task_id)
    if not task:
        return None, []
    parent = ds.tasks.get(task.get("parentId"))
    if parent:
        return parent["subTaskIds"], list(parent["subTaskIds"])
    if context is None:
        return None, []
    if context.kind == "project":
        backlog = ds.project_entities.get(context.id, {}).get("backlogTaskIds", [])
        if task_id in backlog:
            return backlog, list(backlog)
    visible = ds.top_level_ids(context, today)
    if task_id not in visible:
        return None, []
    section = sections.section_of(ds, context, task_id)
    if section is not None:
        return section["taskIds"], [i for i in section["taskIds"] if i in visible]
    visible = _no_section(ds, context, visible)
    if task_id not in visible:
        return None, []
    return _context_order(ds, context, today), visible


def _no_section(ds, context, visible):
    """The shown tasks that are in no section and that the list orders."""
    placed = {i for s in sections.of_context(ds, context) for i in s.get("taskIds", ())}
    visible = [i for i in visible if i not in placed]
    if context.kind == "today":
        # Today shows the tasks with a time by their time, not by this order.
        visible = [i for i in visible if not ds.has_time(ds.tasks[i])]
    return visible


def siblings(ds, task_id, context, today=None):
    """The ids a task can be moved among, in their order, itself included."""
    return _lists(ds, task_id, context, today)[1]


def _place(order, task_id, neighbour, after):
    order.remove(task_id)
    order.insert(order.index(neighbour) + (1 if after else 0), task_id)


def move(ds, task_id, context, offset, today=None):
    """Move a task by `offset` places among the tasks a list shows (or, for
    a subtask, among its parent's subtasks); a large offset moves it to the
    top or the bottom. Returns True when it moved."""
    order, visible = _lists(ds, task_id, context, today)
    if order is None:
        return False
    index = visible.index(task_id)
    target = max(0, min(len(visible) - 1, index + offset))
    if target == index:
        return False
    _place(order, task_id, visible[target], after=offset > 0)
    if sections.section_of(ds, context, task_id) is not None:
        # Inside a section Super Productivity moves the task in the list's
        # own order as well, so both orders agree.
        own = _context_order(ds, context, today)
        if task_id in own and visible[target] in own:
            _place(own, task_id, visible[target], after=offset > 0)
    return True


def sectionable(ds, task_id, context, today=None):
    """A top-level task of the list's main part: only those are in sections."""
    task = ds.tasks.get(task_id)
    return bool(task) and not task.get("parentId") and sections.can_have(context) \
        and task_id in ds.top_level_ids(context, today)


def move_to(ds, task_id, context, target_id, today=None):
    """Move a task to the place of another task of the same list (dropping
    it there); the tasks between them close the gap. As Super Productivity
    stores a drop (`moveItemAfterAnchor`): the task goes right after the
    task now shown before it, or to the start of the id list when it is
    shown first. A drop on a task of another section, or of none, moves
    the task there. Returns True when it moved."""
    if target_id == task_id:
        return False
    if sectionable(ds, task_id, context, today) and sectionable(ds, target_id,
                                                                  context, today):
        source = sections.section_of(ds, context, task_id)
        target = sections.section_of(ds, context, target_id)
        if (source or {}).get("id") != (target or {}).get("id"):
            return _to_other_group(ds, task_id, context, target_id, source, target, today)
    order, visible = _lists(ds, task_id, context, today)
    if order is None or target_id not in visible:
        return False
    place = visible.index(target_id)
    visible.remove(task_id)
    order.remove(task_id)
    order.insert(order.index(visible[place - 1]) + 1 if place else 0, task_id)
    return True


def _to_other_group(ds, task_id, context, target_id, source, target, today):
    """A drop on a task of another section (addTaskToSection) or of no
    section (removeTaskFromSection): the task takes the target's place."""
    shown = _lists(ds, target_id, context, today)[1]
    if target_id not in shown:
        return False
    place = shown.index(target_id)
    after_id = shown[place - 1] if place else None
    if target is not None:
        sections.place(ds, target["id"], task_id, after_id, (source or {}).get("id"))
    else:
        sections.take_out(ds, source["id"], task_id, context, after_id)
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
