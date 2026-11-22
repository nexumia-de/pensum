"""Project notes as Super Productivity keeps them: the slice `note`
(`{ids, entities, todayOrder}`, a note `{id, projectId, isPinnedToToday,
content, created, modified}`) listed by `project.noteIds`. Rules of its
note and project reducers (read at commit 9980fd76): a new note goes to
the top of `note.ids`, of its project's `noteIds` and, when pinned, of
`todayOrder`; pinning prepends a note that is not listed yet, unpinning
removes it; deleting removes it from all three. Optional fields
(`imgUrl`, `isLock`, `backgroundColor`) are kept as read. No GTK."""
from pensum.store import dates
from pensum.store.ids import new_id


def _slice(ds):
    return ds.data["note"]


def of_project(ds, project_id):
    """A project's notes in its `noteIds` order."""
    project = ds.project_entities.get(project_id) or {}
    entities = _slice(ds)["entities"]
    return [entities[i] for i in project.get("noteIds", ()) if i in entities]


def pinned(ds):
    """The notes pinned to Today, in `todayOrder`."""
    entities = _slice(ds)["entities"]
    return [entities[i] for i in _slice(ds)["todayOrder"]
            if i in entities and entities[i].get("isPinnedToToday")]


def add(ds, project_id, content="", pinned_to_today=False, now=None):
    now = now or dates.now_ms()
    note = {"id": new_id(), "projectId": project_id,
            "isPinnedToToday": bool(pinned_to_today), "content": content,
            "created": now, "modified": now}
    state = _slice(ds)
    state["entities"][note["id"]] = note
    state["ids"].insert(0, note["id"])
    if note["isPinnedToToday"]:
        state["todayOrder"].insert(0, note["id"])
    project = ds.project_entities.get(project_id)
    if project is not None:
        project["noteIds"] = [note["id"]] + list(project.get("noteIds", ()))
    return note


def set_content(ds, note_id, content, now=None):
    note = _slice(ds)["entities"].get(note_id)
    if note is None or note.get("content") == content:
        return False
    note["content"] = content
    note["modified"] = now or dates.now_ms()
    return True


def set_pinned(ds, note_id, value, now=None):
    state = _slice(ds)
    note = state["entities"].get(note_id)
    if note is None:
        return False
    note["isPinnedToToday"] = bool(value)
    note["modified"] = now or dates.now_ms()
    if not value:
        state["todayOrder"] = [i for i in state["todayOrder"] if i != note_id]
    elif note_id not in state["todayOrder"]:
        state["todayOrder"].insert(0, note_id)
    return True


def delete(ds, note_id):
    state = _slice(ds)
    note = state["entities"].pop(note_id, None)
    if note is None:
        return False
    state["ids"] = [i for i in state["ids"] if i != note_id]
    state["todayOrder"] = [i for i in state["todayOrder"] if i != note_id]
    project = ds.project_entities.get(note.get("projectId"))
    if project is not None:
        project["noteIds"] = [i for i in project.get("noteIds", ()) if i != note_id]
    return True


def title(note):
    """The first line of a note without Markdown heading marks, for lists."""
    for line in (note.get("content") or "").splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line
    return ""
