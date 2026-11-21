"""Sections inside a list, as Super Productivity keeps them: the slice
`section` with `{id, contextId, contextType, title, isExpanded, taskIds}`.
A project and Today can have sections, other tags cannot. A section's
`taskIds` say which top-level tasks are in it and in which order; the
tasks stay in the list's own order (`project.taskIds`, `TODAY.taskIds`)
as well. No GTK."""
from pensum.store.defaults import TODAY_ID
from pensum.store.ids import new_id

MAX_TITLE = 200


def _key(context):
    """(contextType, contextId) of a list that can have sections, or None."""
    if context is None:
        return None
    if context.kind == "project":
        return "PROJECT", context.id
    if context.kind == "today":
        return "TAG", TODAY_ID
    return None


def can_have(context):
    return _key(context) is not None


def _entities(ds):
    return ds.data["section"]["entities"]


def of_context(ds, context):
    """A list's sections in their order (their places in `section.ids`)."""
    key = _key(context)
    if key is None:
        return []
    entities = _entities(ds)
    return [entities[i] for i in ds.data["section"]["ids"]
            if i in entities
            and (entities[i].get("contextType"), entities[i].get("contextId")) == key]


def section_of(ds, context, task_id):
    """The section of a list that holds a task, or None."""
    for section in of_context(ds, context):
        if task_id in section.get("taskIds", ()):
            return section
    return None


def group(ds, context, tasks):
    """(tasks in no section, [(section, its tasks)]) the way the list shows
    them: a section's tasks follow its `taskIds`, the others the list."""
    by_id = {t["id"]: t for t in tasks}
    placed, groups = set(), []
    for section in of_context(ds, context):
        ids = [i for i in section.get("taskIds", ()) if i in by_id and i not in placed]
        placed.update(ids)
        groups.append((section, [by_id[i] for i in ids]))
    return [t for t in tasks if t["id"] not in placed], groups


def is_expanded(section):
    """Open unless said otherwise: the field is optional."""
    return section.get("isExpanded", True) is not False


def _title(title):
    return title.strip()[:MAX_TITLE] if isinstance(title, str) else ""


def add(ds, context, title, entity_id=None):
    """A new, open, empty section at the end of the list's sections."""
    key = _key(context)
    if key is None:
        return None
    section = {"id": entity_id or new_id(), "contextId": key[1], "contextType": key[0],
               "title": _title(title), "isExpanded": True, "taskIds": []}
    _entities(ds)[section["id"]] = section
    ds.data["section"]["ids"].append(section["id"])
    return section


def rename(ds, section_id, title):
    _entities(ds)[section_id]["title"] = _title(title)


def set_expanded(ds, section_id, expanded):
    _entities(ds)[section_id]["isExpanded"] = bool(expanded)


def delete(ds, section_id):
    """Only the section goes: its tasks stay in the list, in no section."""
    if _entities(ds).pop(section_id, None) is not None:
        ids = ds.data["section"]["ids"]
        while section_id in ids:
            ids.remove(section_id)


def _after_anchor(ids, task_id, after_id):
    """Super Productivity's anchor rule (moveItemAfterAnchor): the id right
    after the anchor, at the start without one; in place when the anchor is
    gone and the id is in the list, else at the end."""
    rest = [i for i in ids if i != task_id]
    if after_id is None:
        return [task_id] + rest
    if after_id not in rest:
        return list(ids) if task_id in ids else rest + [task_id]
    place = rest.index(after_id) + 1
    return rest[:place] + [task_id] + rest[place:]


def place(ds, section_id, task_id, after_id=None, source_id=None):
    """Put a task into a section after `after_id` (None: first), also to
    move it inside the section (addTaskToSection). `source_id` is the
    section it was in; the list's own order does not change."""
    entities = _entities(ds)
    source = entities.get(source_id) if source_id and source_id != section_id else None
    if source and task_id in source.get("taskIds", ()):
        source["taskIds"][:] = [i for i in source["taskIds"] if i != task_id]
    target = entities.get(section_id)
    if target is not None:
        target.setdefault("taskIds", [])[:] = _after_anchor(target["taskIds"], task_id,
                                                            after_id)


def take_out(ds, section_id, task_id, context, after_id=None):
    """Take a task out of its section and put it after `after_id` (None:
    first) in the list's own order (removeTaskFromSection)."""
    section = _entities(ds).get(section_id)
    if section is not None and task_id in section.get("taskIds", ()):
        section["taskIds"][:] = [i for i in section["taskIds"] if i != task_id]
    key = _key(context)
    if key is None:
        return
    source = ds.project_entities if key[0] == "PROJECT" else ds.tag_entities
    entity = source.get(key[1])
    if entity is not None:
        entity.setdefault("taskIds", [])[:] = _after_anchor(entity["taskIds"], task_id,
                                                            after_id)


def strip(ds, task_ids, project_id=None, today=False):
    """Take tasks out of sections: of every list (a task that is deleted,
    archived), of one project (a task that leaves it) or of Today (a task
    that leaves Today's order)."""
    gone = set(task_ids)
    for section in _entities(ds).values():
        if project_id is not None and (section.get("contextType"),
                                       section.get("contextId")) != ("PROJECT", project_id):
            continue
        if today and (section.get("contextType"),
                      section.get("contextId")) != ("TAG", TODAY_ID):
            continue
        if any(i in gone for i in section.get("taskIds", ())):
            section["taskIds"][:] = [i for i in section["taskIds"] if i not in gone]
