"""The sync test's Pensum side (docs/dev-environment.md, sync test): read
the WebDAV folder Super Productivity synced to (sp_sync.mjs) with
pensum.sync and check, for round N:

- reading over WebDAV and from the folder on disk gives the same data,
  and every file in the folder is byte-identical before and after;
- counts and field values equal Super Productivity's own export after
  the sync (roundN.sp.json) and the tasks it shows (roundN.ui.json), and
  the test tasks are in the state sp_sync.mjs left them;
- validate.problems() is empty, also after an import;
- round 2: the changes since round 1 (recentOps) name every task Super
  Productivity changed, and wrong decodes fail these checks: the first
  snapshot kept, recentOps ignored, the previous file (.bak).

    python3 tests/real_app/check_sync.py DIR 1|2

PENSUM_DAV_URL is the WebDAV server (default http://127.0.0.1:2345/),
PENSUM_DAV_ROOT its directory on disk (default DIR/dav), PENSUM_DAV_FOLDER
the sync folder (default super-productivity); with PENSUM_SYNC_PASSWORD
the files must be compressed and encrypted, a wrong password must fail.
Prints ids and counts, never titles. Exits 1 on a difference.
"""
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
# The shared package: a sibling checkout, or CI's .phosh-toolkit.
for toolkit in (ROOT.parent / "phosh-toolkit", ROOT / ".phosh-toolkit"):
    sys.path.insert(0, str(toolkit / "lib"))

from pensum.store import backup, validate  # noqa: E402
from pensum.store.dataset import Dataset  # noqa: E402
from pensum.store.files import Files  # noqa: E402
from pensum.sync import SyncError, changes, crypto, envelope, reader, replay  # noqa: E402
from pensum.sync.local import LocalFolder  # noqa: E402
from pensum.sync.webdav import WebDav  # noqa: E402

FOLDER = os.environ.get("PENSUM_DAV_FOLDER") or "super-productivity"
PASSWORD = os.environ.get("PENSUM_SYNC_PASSWORD") or None
SPLIT = os.environ.get("PENSUM_SYNC_SPLIT") == "1"
TASK_FIELDS = ("title", "isDone", "projectId", "tagIds", "parentId", "subTaskIds",
               "timeEstimate", "timeSpent", "doneOn", "notes", "dueDay", "created")
CONTEXT_FIELDS = ("title", "taskIds")
# The test tasks (sp_sync.mjs) and their state after each round:
# True done, False open, None gone; "parent" names the parent's key.
T = {
    "plants": "Sync test: water the plants",
    "letter": "Sync test: write the letter",
    "bike": "Sync test: fix the bike",
    "bikeRenamed": "Sync test: fix the bike and the bell",
    "bread": "Sync test: bake bread",
    "call": "Sync test: call the plumber",
    "sub": "Sync test: buy flour",
}
EXPECT = {
    "1": {"plants": False, "letter": True, "bike": False, "bikeRenamed": None,
          "bread": False, "sub": ("bread", False), "call": None},
    "2": {"plants": True, "letter": True, "bike": None, "bikeRenamed": False,
          "bread": None, "sub": None, "call": False},
}


def hashes(directory):
    return {str(p.relative_to(directory)): (hashlib.sha256(p.read_bytes()).hexdigest(),
                                            p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(directory.rglob("*")) if p.is_file()}


def ids(data, name):
    return set(data[name]["ids"])


def compare(read, sp):
    """Differences between Pensum's read and Super Productivity's export,
    by slice, id and field."""
    found = []
    for name in ("task", "project", "tag"):
        if ids(read, name) != ids(sp, name):
            found.append(f"{name} ids: {len(ids(read, name))} read, "
                         f"{len(ids(sp, name))} in Super Productivity")
    for archive in ("archiveYoung", "archiveOld"):
        a, b = set(read[archive]["task"]["ids"]), set(sp[archive]["task"]["ids"])
        if a != b:
            found.append(f"{archive} task ids: {len(a)} read, {len(b)} in Super Productivity")
    for tid in ids(read, "task") & ids(sp, "task"):
        r, s = read["task"]["entities"][tid], sp["task"]["entities"][tid]
        for key in TASK_FIELDS:
            if r.get(key) != s.get(key):
                found.append(f"task {tid}: {key}")
    for name in ("project", "tag"):
        for cid in ids(read, name) & ids(sp, name):
            r, s = read[name]["entities"][cid], sp[name]["entities"][cid]
            for key in CONTEXT_FIELDS:
                if r.get(key) != s.get(key):
                    found.append(f"{name} {cid}: {key}")
    return found


def by_title(data):
    return {t["title"]: t for t in data["task"]["entities"].values()}


def expected_state(data, round_, ui):
    found = []
    tasks = by_title(data)
    archived = {t.get("title") for a in ("archiveYoung", "archiveOld")
                for t in data[a]["task"]["entities"].values()}
    for key, want in EXPECT[round_].items():
        task = tasks.get(T[key])
        parent = None
        if isinstance(want, tuple):
            parent, want = want
        if want is None:
            if task is not None or T[key] in archived:
                found.append(f"test task {key}: should be gone")
            continue
        if task is None:
            found.append(f"test task {key}: missing")
            continue
        if bool(task.get("isDone")) != want:
            found.append(f"test task {key}: isDone {task.get('isDone')}")
        if parent and task.get("parentId") != (tasks.get(T[parent]) or {}).get("id"):
            found.append(f"test task {key}: parent")
    # What Super Productivity shows in Today: open and done as read.
    for title in ui["open"]:
        if title not in tasks or tasks[title].get("isDone"):
            found.append("a task shown open is not open in the read data")
    for title in ui["done"]:
        if title not in tasks or not tasks[title].get("isDone"):
            found.append("a task shown done is not done in the read data")
    shown = set(ui["open"]) | set(ui["done"])
    for key, want in EXPECT[round_].items():
        if want is not None and T[key] not in shown:
            found.append(f"test task {key}: not shown by Super Productivity")
    return found


# What the test changes in round 2. Not timestamps: Super Productivity
# itself moved a done task's doneOn by a few ms between rounds, with no op.
CHANGE_FIELDS = ("title", "isDone", "projectId", "tagIds", "parentId", "subTaskIds")


def changed_tasks(before, after):
    """Task ids Super Productivity added, removed or changed between rounds."""
    a, b = before["task"]["entities"], after["task"]["entities"]
    return {tid for tid in set(a) | set(b)
            if tid not in a or tid not in b
            or any(a[tid].get(k) != b[tid].get(k) for k in CHANGE_FIELDS)}


# Replay (#30) against what Super Productivity itself holds. Not compared:
# `modified` (the time of replay), and `doneOn` within a second: the device
# that completes a task keeps its own clock's doneOn in its state while
# the op carries a few ms later value, which every other device (and
# Super Productivity itself after a reload) applies.
DONE_ON_DRIFT_MS = 1000


def compare_states(replayed, real):
    found = []
    a, b = replayed["task"], real["task"]
    if a["ids"] != b["ids"]:
        found.append(f"task order: {len(a['ids'])} replayed, {len(b['ids'])} real")
    for tid in set(a["entities"]) | set(b["entities"]):
        x, y = a["entities"].get(tid), b["entities"].get(tid)
        if x is None or y is None:
            found.append(f"task {tid}: {'missing' if x is None else 'extra'} after replay")
            continue
        for key in (set(x) | set(y)) - {"modified"}:
            if key == "doneOn" and isinstance(x.get(key), int) and isinstance(y.get(key), int) \
                    and abs(x[key] - y[key]) <= DONE_ON_DRIFT_MS:
                continue
            if x.get(key) != y.get(key):
                found.append(f"task {tid}: {key}")
    for name, keys in (("project", ("taskIds", "backlogTaskIds")), ("tag", ("taskIds",)),
                       ("section", ("taskIds",))):
        for cid in set(replayed[name]["entities"]) | set(real[name]["entities"]):
            x = replayed[name]["entities"].get(cid) or {}
            y = real[name]["entities"].get(cid) or {}
            for key in keys:
                if x.get(key) != y.get(key):
                    found.append(f"{name} {cid}: {key}")
    days = lambda d: {k: v for k, v in ((d.get("planner") or {}).get("days") or {}).items() if v}
    if days(replayed) != days(real):
        found.append("planner days")
    return found


def follows(snapshot, seen, expected):
    found = changes.since(snapshot, seen)
    problems = []
    if not found.complete:
        problems.append("recentOps do not reach back to round 1")
    missing = expected - found.task_ids
    if missing:
        problems.append(f"{len(missing)} changed tasks not in the ops since round 1")
    if found.count == 0:
        problems.append("no ops since round 1")
    return problems, found


def main(directory, round_):
    directory = Path(directory)
    dav = Path(os.environ.get("PENSUM_DAV_ROOT") or directory / "dav")
    url = os.environ.get("PENSUM_DAV_URL", "http://127.0.0.1:2345/")
    failures = []

    def check(what, problems):
        if problems:
            failures.extend(f"{what}: {p}" for p in problems)
            for p in problems[:20]:
                print(f"FAIL: {what}: {p}")
        else:
            print(f"ok: {what}")

    before = hashes(dav)
    over_webdav = reader.read(WebDav(url, "test", "test", FOLDER), PASSWORD)
    on_disk = reader.read(LocalFolder(dav / FOLDER), PASSWORD)
    after = hashes(dav)
    check("folder unchanged by reading", [] if before == after else
          [f"{len(set(before.items()) ^ set(after.items()))} file entries differ"])
    check("WebDAV and disk read the same",
          [] if over_webdav.data == on_disk.data
          and over_webdav.sync_version == on_disk.sync_version else ["data differ"])
    snapshot = over_webdav
    print(f"round {round_}: {snapshot.format}, syncVersion {snapshot.sync_version}, "
          f"{len(snapshot.data['task']['ids'])} tasks, {len(snapshot.ops)} recent ops, "
          f"{len(before)} files in the folder")

    main_file = "sync-ops.json" if SPLIT else "sync-data.json"
    prefix = (dav / FOLDER / main_file).read_text()[:8]
    want = "pf_CE" if PASSWORD else ("pf_3__" if SPLIT else "pf_2__")
    check(f"format {'v3' if SPLIT else 'v2'}",
          [] if snapshot.format == ("v3" if SPLIT else "v2") else [snapshot.format])
    check(f"files written {'compressed and encrypted' if PASSWORD else 'plain'}",
          [] if prefix.startswith(want) else [f"prefix {prefix[:6]!r}"])
    if PASSWORD:
        try:
            reader.read(LocalFolder(dav / FOLDER), "wrong password")
            check("a wrong password fails", ["it was accepted"])
        except crypto.WrongPassword:
            check("a wrong password fails", [])
        try:
            reader.read(LocalFolder(dav / FOLDER))
            check("no password fails", ["it was accepted"])
        except SyncError:
            check("no password fails", [])

    sp = backup.read(directory / f"round{round_}.sp.json")
    ui = json.loads((directory / f"round{round_}.ui.json").read_text())
    check("same as Super Productivity's export", compare(snapshot.data, sp))
    check("test tasks and what Super Productivity shows",
          expected_state(snapshot.data, round_, ui))
    check("validate.problems() of the read data", validate.problems(snapshot.data))
    with tempfile.TemporaryDirectory() as tmp:
        files = Files(Path(tmp) / "data")
        current = Dataset(backup.parse((ROOT / "tests/fixtures/test-backup.json").read_text()))
        imported = files.import_data(snapshot.data, current)
        check("validate.problems() after the import",
              validate.problems(imported.data) + validate.problems(files.load().data))

    state_file = directory / f"round{round_}.pensum.json"
    state_file.write_text(json.dumps({"syncVersion": snapshot.sync_version,
                                      "data": snapshot.data}))
    if round_ == "2":
        first = json.loads((directory / "round1.pensum.json").read_text())
        sp1 = backup.read(directory / "round1.sp.json")
        expected = changed_tasks(sp1, sp)
        problems, found = follows(snapshot, first["syncVersion"], expected)
        check(f"recentOps since round 1 ({found.count} ops, {len(expected)} tasks "
              "changed in Super Productivity)", problems)
        # Replay (#30): round 1's data plus the ops since must give what
        # Super Productivity holds now.
        since = [op for op in snapshot.ops if (op.get("sv") or 0) > first["syncVersion"]]
        replayed = replay.apply(first["data"], since)
        check(f"round 1 + {len(since)} ops replayed = round 2",
              compare_states(replayed, snapshot.data))
        # Wrong decodes and wrong replays must fail the same checks.
        wrong = {"the first snapshot kept": compare(first["data"], sp)}
        for code, what in (("HD", "deletes"), ("HU", "updates"), ("HA", "adds")):
            if any(op.get("a") == code for op in since):
                bad = replay.apply(first["data"], [op for op in since if op.get("a") != code])
                wrong[f"replay without {what}"] = compare_states(bad, snapshot.data)
        no_ops = reader.Snapshot(**{**snapshot.__dict__, "ops": []})
        wrong["recentOps ignored"] = follows(no_ops, first["syncVersion"], expected)[0]
        bak = dav / FOLDER / "sync-data.json.bak"
        if bak.exists():
            payload, _ = envelope.decode(bak.read_text(), PASSWORD)
            wrong["the previous file (.bak)"] = compare(
                backup.parse(json.dumps(payload["state"])), sp)
        else:
            print("note: Super Productivity wrote no sync-data.json.bak")
        for what, problems in wrong.items():
            if problems:
                print(f"ok: wrong decode caught: {what} ({len(problems)} differences)")
            else:
                failures.append(f"wrong decode not caught: {what}")
                print(f"FAIL: wrong decode not caught: {what}")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("1", "2"):
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
