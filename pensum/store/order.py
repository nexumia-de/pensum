"""The order of tasks in a list: the id lists Super Productivity keeps for
it (`project.taskIds` and `backlogTaskIds`, `tag.taskIds`, `TODAY.taskIds`,
a parent's `subTaskIds`). Moving a task rewrites one of them and nothing
else. No GTK."""
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
    if context.kind == "today":
        # Today shows the tasks with a time by their time, not by this order.
        visible = [i for i in visible if not ds.has_time(ds.tasks[i])]
    if task_id not in visible:
        return None, []
    return _context_order(ds, context, today), visible


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
    return True


def move_to(ds, task_id, context, target_id, today=None):
    """Move a task to the place of another task of the same list (dropping
    it there); the tasks between them close the gap. As Super Productivity
    stores a drop (`moveItemAfterAnchor`): the task goes right after the
    task now shown before it, or to the start of the id list when it is
    shown first. Returns True when it moved."""
    order, visible = _lists(ds, task_id, context, today)
    if order is None or target_id == task_id or target_id not in visible:
        return False
    place = visible.index(target_id)
    visible.remove(task_id)
    order.remove(task_id)
    order.insert(order.index(visible[place - 1]) + 1 if place else 0, task_id)
    return True
