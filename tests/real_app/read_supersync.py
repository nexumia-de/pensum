"""SuperSync probe, Pensum's side (#34, docs/dev-environment.md, SuperSync
probe): download the test account's operations (GET only), decrypt them
with pensum.sync.crypto and report what a reader would have to do.

    python3 tests/real_app/read_supersync.py [PASSWORD]

The access token is a network secret the proxy adds to requests to
sync.super-productivity.com. Prints counts, ids and action types, never
titles. Exits 1 when a payload does not decrypt or the newest full-state
op is not a valid dataset.
"""
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
for toolkit in (ROOT.parent / "phosh-toolkit", ROOT / ".phosh-toolkit"):
    sys.path.insert(0, str(toolkit / "lib"))

from pensum.store import backup, validate  # noqa: E402
from pensum.sync import crypto  # noqa: E402

URL = "https://sync.super-productivity.com/api/sync/ops?sinceSeq={}&limit=500"
FULL_STATE = {"SYNC_IMPORT", "BACKUP_IMPORT", "REPAIR"}


def download():
    ops, seq = [], 0
    while True:
        request = urllib.request.Request(URL.format(seq), method="GET",
                                         headers={"Authorization": "Bearer proxy-injected"})
        with urllib.request.urlopen(request, timeout=30) as response:
            page = json.load(response)
        ops += page["ops"]
        if not page.get("hasMore") or not page["ops"]:
            return ops, page.get("latestSeq")
        seq = page["ops"][-1]["serverSeq"]


def main(password):
    ops, latest = download()
    print(f"{len(ops)} ops, latest server seq {latest}")
    cache, full, later = {}, None, Counter()
    for entry in ops:
        op = entry["op"]
        payload = op["payload"]
        if op.get("isPayloadEncrypted"):
            payload = crypto.decrypt(payload, password, cache)
        payload = json.loads(payload) if isinstance(payload, str) else payload
        if op["opType"] in FULL_STATE:
            full, later = (entry["serverSeq"], payload), Counter()
        else:
            later[f'{op["opType"]} {op["actionType"]}'] += 1
    if full is None:
        print("no full-state op: the whole history would have to be replayed")
        return 1
    seq, payload = full
    state = payload.get("appDataComplete", payload)
    data = backup.parse(json.dumps(state))
    problems = validate.problems(data)
    print(f"newest full-state op at seq {seq}: {len(data['task']['ids'])} tasks, "
          f"{len(problems)} problems")
    print(f"{sum(later.values())} later ops to replay:")
    for kind, count in sorted(later.items()):
        print(f"  {count} × {kind}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "test password"))
