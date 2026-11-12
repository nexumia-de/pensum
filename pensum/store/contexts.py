"""Changes to projects and tags, including the menu tree that orders
them. No GTK."""
from pensum.store import dates, defaults, tasks
from pensum.store.defaults import INBOX_ID, TODAY_ID
from pensum.store.ids import new_id


def _tree(ds, name):
    return ds.data["menuTree"].setdefault(name, [])


def _drop_node(nodes, node_id):
    for node in list(nodes):
        if node.get("k") == "f":
            _drop_node(node.setdefault("children", []), node_id)
        elif node.get("id") == node_id:
            nodes.remove(node)


def add_project(ds, title, now=None, entity_id=None):
    project = defaults.get("project")
    project.update(id=entity_id or new_id(), title=title.strip())
    ds.project_entities[project["id"]] = project
    ds.data["project"]["ids"].append(project["id"])
    tree = _tree(ds, "projectTree")
    if tree:
        tree.append({"id": project["id"], "k": "p"})
    return project


def add_tag(ds, title, now=None, entity_id=None):
    tag = defaults.get("tag")
    tag.update(id=entity_id or new_id(), title=title.strip(),
               created=now or dates.now_ms())
    ds.tag_entities[tag["id"]] = tag
    ds.data["tag"]["ids"].append(tag["id"])
    # Super Productivity's addTag appends the tag to the tag tree, also to
    # an empty one (menu-tree.reducer.ts). A new project goes into the
    # project tree only when it has one; its menu fills an empty tree.
    tree = _tree(ds, "tagTree")
    if not any(n.get("k") == "t" and n.get("id") == tag["id"] for n in tree):
        tree.append({"id": tag["id"], "k": "t"})
    return tag


def rename(ds, kind, context_id, title):
    source = ds.project_entities if kind == "project" else ds.tag_entities
    source[context_id]["title"] = title.strip()


def set_archived(ds, project_id, archived):
    if project_id == INBOX_ID:
        return
    ds.project_entities[project_id]["isArchived"] = bool(archived)


def delete_project(ds, project_id):
    """Delete a project with its tasks and notes; the Inbox stays."""
    if project_id == INBOX_ID or project_id not in ds.project_entities:
        return
    project = ds.project_entities[project_id]
    for task_id in [i for i, t in ds.tasks.items()
                    if t.get("projectId") == project_id and not t.get("parentId")]:
        tasks.delete(ds, task_id)
    for note_id in project.get("noteIds", ()):
        ds.data["note"]["entities"].pop(note_id, None)
        _remove(ds.data["note"]["ids"], note_id)
        _remove(ds.data["note"]["todayOrder"], note_id)
    for archive in ("archiveYoung", "archiveOld"):
        entities = ds.data[archive]["task"]["entities"]
        for task_id in [i for i, t in entities.items() if t.get("projectId") == project_id]:
            entities.pop(task_id)
            _remove(ds.data[archive]["task"]["ids"], task_id)
    ds.project_entities.pop(project_id)
    _remove(ds.data["project"]["ids"], project_id)
    ds.data["timeTracking"].get("project", {}).pop(project_id, None)
    _drop_node(_tree(ds, "projectTree"), project_id)
    sections = ds.data["section"]
    for section_id in [i for i, s in sections["entities"].items()
                       if s.get("contextId") == project_id]:
        sections["entities"].pop(section_id)
        _remove(sections["ids"], section_id)
    if (ds.config.get("tasks") or {}).get("defaultProjectId") == project_id:
        ds.config["tasks"]["defaultProjectId"] = INBOX_ID


def delete_tag(ds, tag_id):
    """Delete a tag; its tasks stay and lose the tag. A task that would be
    left without project and tag moves to the default project."""
    if tag_id == TODAY_ID or tag_id not in ds.tag_entities:
        return
    for archive in ("task", "archiveYoung", "archiveOld"):
        entities = (ds.data[archive] if archive == "task"
                    else ds.data[archive]["task"])["entities"]
        for task in entities.values():
            if tag_id in task.get("tagIds", ()):
                task["tagIds"] = [t for t in task["tagIds"] if t != tag_id]
                if archive == "task" and not task.get("projectId") \
                        and not task.get("parentId") and not task["tagIds"]:
                    task["projectId"] = ds.default_project_id()
                    ds.project_entities[task["projectId"]]["taskIds"].append(task["id"])
    ds.tag_entities.pop(tag_id)
    _remove(ds.data["tag"]["ids"], tag_id)
    ds.data["timeTracking"].get("tag", {}).pop(tag_id, None)
    _drop_node(_tree(ds, "tagTree"), tag_id)


def _remove(values, value):
    while value in values:
        values.remove(value)
