"""The cross-model checks Super Productivity runs on every import
(is-related-model-data-valid.ts), so Pensum never writes a dataset that
it would refuse. Returns the problems found; empty means valid. No GTK."""
from pensum.store.backup import CORE_SLICES
from pensum.store.defaults import TODAY_ID, slices


def problems(data):
    found = []
    for name in list(slices()) + ["globalConfig"]:
        if data.get(name) is None:
            found.append(f"missing slice {name}")
    if found:
        return found
    tasks = data["task"]["entities"]
    project_ids = set(data["project"]["entities"])
    tag_ids = set(data["tag"]["entities"])
    repeat_ids = set(data["taskRepeatCfg"]["entities"])
    for name in CORE_SLICES[:3]:
        ids, entities = data[name]["ids"], data[name]["entities"]
        if set(ids) != set(entities) or len(ids) != len(set(ids)):
            found.append(f"{name}: ids and entities differ")
    for project in data["project"]["entities"].values():
        for tid in project.get("taskIds", []) + project.get("backlogTaskIds", []):
            task = tasks.get(tid)
            if not task:
                found.append(f"project {project['id']}: missing task {tid}")
            elif task.get("projectId") != project["id"]:
                found.append(f"task {tid}: projectId differs from project {project['id']}")
        for nid in project.get("noteIds", []):
            note = data["note"]["entities"].get(nid)
            if not note or note.get("projectId") != project["id"]:
                found.append(f"project {project['id']}: bad note {nid}")
    for task in tasks.values():
        if task.get("projectId") and task["projectId"] not in project_ids:
            found.append(f"task {task['id']}: unknown project")
        for tag_id in task.get("tagIds", []):
            if tag_id not in tag_ids or tag_id == TODAY_ID:
                found.append(f"task {task['id']}: bad tag {tag_id}")
        if task.get("repeatCfgId") and task["repeatCfgId"] not in repeat_ids:
            found.append(f"task {task['id']}: unknown repeat config")
        if not task.get("parentId") and not task.get("projectId") and not task.get("tagIds"):
            found.append(f"task {task['id']}: neither project nor tag")
        if task.get("parentId") and task["parentId"] not in tasks:
            found.append(f"task {task['id']}: missing parent")
        for sub_id in task.get("subTaskIds", []):
            if sub_id not in tasks:
                found.append(f"task {task['id']}: missing subtask {sub_id}")
        for key in ("doneOn", "parentId", "remindAt", "repeatCfgId"):
            if key in task and task[key] is None:
                found.append(f"task {task['id']}: {key} is null")
    for tag in data["tag"]["entities"].values():
        if tag["id"] == TODAY_ID:
            continue  # stale ids in Today's order are harmless
        for tid in tag.get("taskIds", []):
            if tid not in tasks:
                found.append(f"tag {tag['id']}: missing task {tid}")
    for nid in data["note"]["todayOrder"]:
        if nid not in data["note"]["entities"]:
            found.append(f"note order: missing note {nid}")
    for archive in ("archiveYoung", "archiveOld"):
        other = "archiveOld" if archive == "archiveYoung" else "archiveYoung"
        here = data[archive]["task"]["entities"]
        there = data[other]["task"]["entities"]
        for task in here.values():
            if task.get("parentId") and task["parentId"] not in here \
                    and task["parentId"] not in there:
                found.append(f"{archive} task {task['id']}: missing parent")
    return found
