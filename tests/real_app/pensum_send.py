"""The sync test's writing step (#30, docs/super-productivity-sync.md):
after round 2, Pensum takes the folder's data as its base, edits test
tasks the way its UI does (a new title, done, an estimate) and sends
them with pensum.sync.writer over WebDAV (or GitHub, test_source.py); Super Productivity's round 3
must then show them. Also checks that the file it wrote reads back with
the edits, one syncVersion further, and that a second send with no new
edits writes nothing.

    python3 tests/real_app/pensum_send.py DIR

Same environment as check_sync.py. Prints ids and counts, never titles.
Exits 1 on a difference."""
import copy
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for toolkit in (ROOT.parent / "phosh-toolkit", ROOT / ".phosh-toolkit"):
    sys.path.insert(0, str(toolkit / "lib"))

from pensum.store import tasks, validate  # noqa: E402
from pensum.store.dataset import Dataset  # noqa: E402
from pensum.sync import reader, writer  # noqa: E402
from test_source import sync_source  # noqa: E402

PASSWORD = os.environ.get("PENSUM_SYNC_PASSWORD") or None
CALL = "Sync test: call the plumber"
CALL_RENAMED = "Sync test: call the plumber at nine"
BIKE = "Sync test: fix the bike and the bell"
ESTIMATE = 30 * 60 * 1000


def by_title(data):
    return {t["title"]: t for t in data["task"]["entities"].values()}


def main(directory):
    directory = Path(directory)
    snapshot = reader.read(sync_source()[0], PASSWORD)
    base = copy.deepcopy(snapshot.data)
    ds = Dataset(copy.deepcopy(snapshot.data))
    found = by_title(ds.data)
    call, bike = found[CALL]["id"], found[BIKE]["id"]
    tasks.update(ds, call, title=CALL_RENAMED)
    tasks.set_estimate(ds, call, ESTIMATE)
    tasks.set_done(ds, bike, True)
    failures = []
    client = writer.new_client_id()
    sent = writer.send(sync_source()[0], PASSWORD, ds.data, base, snapshot.sync_version, client)
    print(f"sent {sent.count} ops, syncVersion {snapshot.sync_version} -> {sent.sync_version}")
    after = reader.read(sync_source()[0], PASSWORD)
    now = by_title(after.data)
    problems = []
    if sent.count != 2 or after.sync_version != snapshot.sync_version + 1:
        problems.append("ops or syncVersion")
    if CALL_RENAMED not in now or now[CALL_RENAMED].get("timeEstimate") != ESTIMATE:
        problems.append("the renamed task with its estimate")
    if not now.get(BIKE, {}).get("isDone"):
        problems.append("the task marked done")
    mine = [op for op in after.ops if op.get("c") == client]
    if len(mine) != 2 or any(op.get("sv") != after.sync_version for op in mine):
        problems.append("Pensum's ops in recentOps")
    problems += validate.problems(after.data)
    again = writer.send(sync_source()[0], PASSWORD, after.data, after.data, after.sync_version,
                        client)
    if again.count or reader.read(sync_source()[0], PASSWORD).sync_version != after.sync_version:
        problems.append("a send without edits wrote")
    for p in problems:
        print(f"FAIL: {p}")
        failures.append(p)
    if not problems:
        print("ok: Pensum's edits written and read back")
    (directory / "sent.pensum.json").write_text(json.dumps({"syncVersion": after.sync_version,
                                                            "client": client}))
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
