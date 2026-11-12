"""Read Super Productivity's export of each imported file back into
Pensum and check it (docs/dev-environment.md, real app):

- pensum.store opens it and validate.problems() is empty;
- counts and field values are as make_exports.py wrote them
  (<name>.expect.json);
- the data equals Pensum's file except where Super Productivity owns the
  difference (SP_OWNED below).

    python3 tests/real_app/check_round_trip.py DIR NAME...

Prints paths, ids and counts, never titles or notes. Exits 1 on a
difference.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pensum.store import backup, validate  # noqa: E402

# What Super Productivity may change on import or export: (path pattern,
# kinds of difference), with why. A value Pensum wrote never changes.
SP_OWNED = [
    # A newer Super Productivity fills settings it added and drops ones it
    # retired (typia auto-fix); Pensum keeps the section as read.
    (r"^globalConfig\.", {"added", "removed"}),
    # loadAllData stops the timer, keeps the last tracked task and sets
    # its own load flags and defaults (task.reducer.ts).
    (r"^task\.(currentTaskId|lastCurrentTaskId|selectedTaskId|isDataLoaded"
     r"|taskDetailTargetPanel)$", {"added", "changed"}),
    (r"^task\.dismissedCalendarAutoImportEventIdsByProvider$", {"added"}),
    # Bookkeeping of its archive flush and planner dialog.
    (r"^archive(Young|Old)\.(lastFlush|lastTimeTrackingFlush)$", {"added", "changed"}),
    (r"^planner\.addPlannedTasksDialogLastShown$", {"added", "changed"}),
    # Slices a newer Super Productivity adds.
    (r"^[a-zA-Z]+$", {"added"}),
]
TREES = (("projectTree", "project"), ("tagTree", "tag"))


def diff(a, b, path=""):
    """Paths where a and b differ: added, removed or changed values."""
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            sub = f"{path}.{key}" if path else key
            if key not in a:
                yield sub, "added"
            elif key not in b:
                yield sub, "removed"
            else:
                yield from diff(a[key], b[key], sub)
    elif a != b:
        yield path, "changed"


def owned(path, kind, written, data):
    if any(re.search(pattern, path) and kind in kinds for pattern, kinds in SP_OWNED):
        return True
    # Its menu fills an empty tree with every project or tag when it first
    # shows them (magic-nav-config.service.ts, initializeProjectTree).
    for tree, slice_name in TREES:
        if path == f"menuTree.{tree}" and not written["menuTree"][tree]:
            nodes = data["menuTree"][tree]
            return all(n.get("id") in data[slice_name]["entities"] for n in nodes)
    return False


def check(directory, name):
    written = backup.read(directory / f"{name}.json")
    expect = json.loads((directory / f"{name}.expect.json").read_text())
    errors = []
    try:
        data = backup.read(directory / f"{name}.sp.json")
    except backup.BackupError as error:
        return [f"Pensum can't open Super Productivity's export: {error}"]
    found = validate.problems(data)
    errors += [f"problem: {problem}" for problem in found[:5]]
    for key, slice_name in (("tasks", "task"), ("projects", "project"),
                            ("tags", "tag"), ("repeatCfgs", "taskRepeatCfg")):
        got = len(data[slice_name]["ids"])
        if got != expect[key]:
            errors.append(f"{key}: {got}, expected {expect[key]}")
    entities = data["task"]["entities"]
    for item in expect["fields"]:
        task = entities.get(item["id"])
        if task is None:
            errors.append(f"task {item['id']} missing")
        elif task.get(item["field"]) != item["value"]:
            errors.append(f"task {item['id']}: {item['field']} differs")
    young = data["archiveYoung"]["task"]["ids"]
    errors += [f"archived task {i} missing" for i in expect["archived"] if i not in young]
    errors += [f"deleted project {i} is back" for i in expect["missingProjects"]
               if i in data["project"]["entities"]]
    plugin = len(data.get("pluginUserData") or [])
    if plugin != expect["pluginUserData"]:
        errors.append(f"pluginUserData: {plugin}, expected {expect['pluginUserData']}")
    found_differences = list(diff(written, data))
    differences = [(p, kind) for p, kind in found_differences
                   if not owned(p, kind, written, data)]
    errors += [f"{kind}: {p}" for p, kind in differences[:20]]
    owned_count = len(found_differences) - len(differences)
    print(f"{name}: {len(data['task']['ids'])} tasks, {len(data['project']['ids'])} projects, "
          f"{len(found)} problems, {len(differences)} differences "
          f"({owned_count} in Super Productivity's own fields)")
    return errors


def main(argv):
    directory = Path(argv[1])
    failed = False
    for name in argv[2:]:
        for error in check(directory, name):
            failed = True
            print(f"FAIL: {name}: {error}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
