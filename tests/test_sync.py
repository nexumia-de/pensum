"""Reading a Super Productivity sync folder (pensum.sync): the envelope,
v2 and v3 files, WebDAV with GET only, the changes since the last read,
and an import that keeps validate.problems() empty. The files written by
a real Super Productivity are checked by tests/real_app (run_sync.sh)."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pensum.store import validate
from pensum.store.dataset import Dataset
from pensum.store.files import Files
from pensum.sync import SyncError, changes, crypto, envelope, reader, summary
from pensum.sync.local import LocalFolder
from pensum.sync.webdav import WebDav, file_url

from conftest import FIXTURES

REAL = FIXTURES / "sync" / "sync-data.json"


def sp_state():
    """Super Productivity's own test backup as the `state` of a sync file."""
    return json.loads((FIXTURES / "test-backup-with-archives.json").read_text())["data"]


def op(sv, entity="TASK", ids=("active-task-1",), kind="UPD"):
    return {"id": f"op-{sv}-{ids[0]}", "a": "TU", "o": kind, "e": entity,
            "d": ids[0], "ds": list(ids), "p": {}, "c": "B_test", "v": {"B_test": sv},
            "t": 1, "s": 4, "sv": sv}


def v2_file(state, sync_version=3, ops=(), **extra):
    payload = {"version": 2, "syncVersion": sync_version, "schemaVersion": 4,
               "vectorClock": {"B_test": sync_version}, "lastModified": 1794497373508,
               "clientId": "B_test", "state": state, "recentOps": list(ops),
               "oldestOpSyncVersion": 1, "oldestBatchComplete": True, **extra}
    return "pf_2__" + json.dumps(payload)


def folder(tmp_path, files):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return LocalFolder(tmp_path)


# --- envelope -------------------------------------------------------------

def test_envelope_plain():
    payload, version = envelope.decode('pf_2__{"a": 1}')
    assert payload == {"a": 1} and version == 2


@pytest.mark.parametrize("text, message", [
    ("{}", "not in Super Productivity's format"),
    ("pf_C2__H4sIAAAA", "damaged \\(gzip\\)"),
    ("pf_E2__AAAA", "encrypted. Enter"),
    ("pf_2__not json", "no JSON"),
    ("pf_2__[1]", "damaged"),
])
def test_envelope_refuses(text, message):
    with pytest.raises(SyncError, match=message):
        envelope.decode(text)


# Made independently of Pensum, with Node's WebCrypto (PBKDF2, AES-GCM)
# and hash-wasm (Argon2id, the library Super Productivity uses), from the
# layout in pensum/sync/crypto.py. Password "correct horse".
PLAIN = {"hello": "wörld", "n": 1}
PASSWORD = "correct horse"
ARGON2_COMPRESSED = (
    "pf_CE2__QtZ3oYX14Qkdo8wdlRum5//FZMUlzb89joPTWYTwaYhmwHJK+ZnOMQtfmQFomqZmApqTU"
    "fdPRXQpuB4QKsMqGz/+KmJsmnnMhpZYhh3/n2knBnKV0bAUCxZlDA/QF6cxVzgPaHFwkRk=")
LEGACY = ("pf_E2__/LjFIQe75KCFqkQ5cFD7QcxdjVnSNgQAPtXOja79VDRbTgiVJrdOteNMSSJOCI"
          "qfI+o7Tg==")


def test_compressed():
    import base64
    import gzip
    text = "pf_C2__" + base64.b64encode(gzip.compress(json.dumps(PLAIN).encode())).decode()
    assert envelope.decode(text)[0] == PLAIN


def test_argon2id_key_matches_hash_wasm():
    assert crypto.argon2id(b"pw", b"0123456789abcdef").hex() == \
        "1aceaf0dca7f8157074f4e838d645ff9ca519c27590d032763bee4c2c4235e3a"


def test_encrypted_and_compressed():
    cache = {}
    assert envelope.decode(ARGON2_COMPRESSED, PASSWORD, cache)[0] == PLAIN
    assert len(cache) == 1  # the key is derived once per salt


def test_encrypted_legacy_pbkdf2():
    assert envelope.decode(LEGACY, PASSWORD)[0] == PLAIN


@pytest.mark.parametrize("text", [ARGON2_COMPRESSED, LEGACY])
def test_wrong_password(text):
    with pytest.raises(crypto.WrongPassword):
        envelope.decode(text, "wrong")


def test_encrypted_needs_password():
    with pytest.raises(envelope.NeedsPassword):
        envelope.decode(LEGACY)


def test_wrong_password_is_not_a_missing_v3_snapshot(tmp_path):
    files = v3_files(sp_state())
    files["sync-state__4__abc.json"] = LEGACY
    with pytest.raises(crypto.WrongPassword):
        reader.read(folder(tmp_path, files), "wrong")


# --- v2 -------------------------------------------------------------------

def test_reads_v2_state_with_archives(tmp_path):
    snapshot = reader.read(folder(tmp_path, {"sync-data.json": v2_file(sp_state())}))
    assert snapshot.format == "v2" and snapshot.sync_version == 3
    assert snapshot.data["task"]["ids"] == ["active-task-1"]
    assert snapshot.data["archiveYoung"]["task"]["ids"]
    assert validate.problems(snapshot.data) == []


def test_reads_archives_kept_next_to_state(tmp_path):
    state = sp_state()
    young = state.pop("archiveYoung")
    snapshot = reader.read(folder(tmp_path, {
        "sync-data.json": v2_file(state, archiveYoung=young)}))
    assert snapshot.data["archiveYoung"] == young


def test_reads_file_written_by_super_productivity():
    """A sync-data.json written by Super Productivity 20.0.0 itself (made
    by tests/real_app/sp_sync.mjs with test tasks)."""
    snapshot = reader.read(LocalFolder(REAL.parent))
    assert snapshot.format == "v2"
    assert snapshot.ops and all("sv" in o for o in snapshot.ops)
    assert validate.problems(snapshot.data) == []
    titles = {t["title"] for t in snapshot.data["task"]["entities"].values()}
    assert "Sync test: water the plants" in titles


@pytest.mark.parametrize("files, message", [
    ({}, "No Super Productivity sync files"),
    ({"__meta_": "x"}, "16 or older"),
    ({"sync-data.json": 'pf_2__{"version": 3, "format": "split"}'}, "operations file is missing"),
    ({"sync-data.json": 'pf_2__{"version": 1}'}, "Unknown sync file version"),
    ({"sync-data.json": 'pf_2__{"version": 2, "state": null}'}, "holds no data"),
    ({"sync-data.json": 'pf_2__{"version": 2, "state": {"task": {}}}'}, "can't be opened"),
])
def test_v2_refuses(tmp_path, files, message):
    with pytest.raises(SyncError, match=message):
        reader.read(folder(tmp_path, files))


# --- v3 -------------------------------------------------------------------

def v3_files(state, snapshot_version=4, ops=()):
    ref = {"syncVersion": snapshot_version, "vectorClock": {"B_test": 9},
           "file": f"sync-state__{snapshot_version}__abc.json"}
    ops_file = {"version": 3, "syncVersion": 6, "schemaVersion": 4,
                "vectorClock": {"B_test": 12}, "lastModified": 2, "clientId": "B_test",
                "recentOps": list(ops), "snapshotRef": ref}
    state_file = {"version": 3, "syncVersion": snapshot_version, "schemaVersion": 4,
                  "vectorClock": {"B_test": 9}, "lastModified": 1, "clientId": "B_test",
                  "state": state}
    return {"sync-ops.json": "pf_3__" + json.dumps(ops_file),
            ref["file"]: "pf_3__" + json.dumps(state_file),
            "sync-data.json": 'pf_2__{"version": 3, "format": "split"}'}


def test_reads_v3_with_current_snapshot(tmp_path):
    snapshot = reader.read(folder(tmp_path, v3_files(sp_state(), ops=[op(3), op(4)])))
    assert snapshot.format == "v3" and snapshot.sync_version == 6
    assert snapshot.data["task"]["ids"] == ["active-task-1"]


def test_v3_falls_back_to_fixed_snapshot(tmp_path):
    files = v3_files(sp_state())
    files["sync-state.json"] = files.pop("sync-state__4__abc.json")
    assert reader.read(folder(tmp_path, files)).format == "v3"


def test_v3_refuses_ops_newer_than_snapshot(tmp_path):
    """Those ops would need Super Productivity's reducers (issue #31)."""
    with pytest.raises(SyncError, match="not in its snapshot"):
        reader.read(folder(tmp_path, v3_files(sp_state(), ops=[op(4), op(5)])))


def test_v3_refuses_snapshot_that_does_not_match(tmp_path):
    files = v3_files(sp_state())
    name = "sync-state__4__abc.json"
    files[name] = files[name].replace('"syncVersion": 4', '"syncVersion": 3')
    with pytest.raises(SyncError, match="snapshot is missing"):
        reader.read(folder(tmp_path, files))


# --- changes and summary --------------------------------------------------

def test_changes_since_last_read(tmp_path):
    ops = [op(1, ids=("a",)), op(2, ids=("b", "c"), kind="DEL"),
           op(3, entity="PROJECT", ids=("p",)), op(3, ids=("d",))]
    snapshot = reader.read(folder(tmp_path, {"sync-data.json": v2_file(sp_state(), 3, ops)}))
    found = changes.since(snapshot, 1)
    assert found.count == 3 and found.complete
    assert found.task_ids == {"b", "c", "d"}
    assert found.by_entity == {"TASK": 2, "PROJECT": 1}
    assert changes.since(snapshot, 3).count == 0
    assert changes.since(snapshot, None).count == 0


def test_changes_beyond_recent_ops_are_incomplete(tmp_path):
    snapshot = reader.read(folder(tmp_path, {"sync-data.json": v2_file(
        sp_state(), 30, [op(30)], oldestOpSyncVersion=25)}))
    assert not changes.since(snapshot, 10).complete
    assert changes.since(snapshot, 24).complete


def test_summary():
    data = sp_state()
    counts = summary.summarize(data)
    assert counts.open_tasks + counts.done_tasks == len(data["task"]["ids"])
    assert counts.archived_tasks == len(data["archiveYoung"]["task"]["ids"]) + \
        len(data["archiveOld"]["task"]["ids"])


# --- import ---------------------------------------------------------------

def test_import_from_sync_keeps_dataset_valid(tmp_path):
    snapshot = reader.read(LocalFolder(REAL.parent))
    files = Files(tmp_path / "data")
    current = Dataset(sp_state())
    ds = files.import_data(snapshot.data, current)
    assert validate.problems(ds.data) == []
    assert validate.problems(files.load().data) == []
    assert len(list(files.backups.iterdir())) == 1  # the data before


def test_reading_leaves_folder_unchanged(tmp_path):
    (tmp_path / "sync-data.json").write_bytes(REAL.read_bytes())
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    reader.read(LocalFolder(tmp_path))
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    assert before == after


# --- WebDAV ---------------------------------------------------------------

class DavStub(BaseHTTPRequestHandler):
    files = {}
    methods = []

    def _handle(self):
        type(self).methods.append((self.command, self.path))
        if self.headers.get("Authorization") != "Basic " + base64.b64encode(
                b"user:secret pass").decode():
            self.send_response(401)
            self.end_headers()
            return
        body = self.files.get(self.path)
        if self.command != "GET":
            self.send_response(405)
            self.end_headers()
        elif body is None:
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    do_GET = do_PUT = do_PROPFIND = do_DELETE = do_MKCOL = _handle

    def log_message(self, *args):
        pass


@pytest.fixture
def dav():
    DavStub.files, DavStub.methods = {}, []
    server = ThreadingHTTPServer(("127.0.0.1", 0), DavStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/remote.php/dav/files/user/"
    server.shutdown()


def test_webdav_reads_with_get_only(dav):
    DavStub.files["/remote.php/dav/files/user/super%20productivity/sync-data.json"] = \
        REAL.read_bytes()
    source = WebDav(dav, "user", "secret pass", "/super productivity/")
    snapshot = reader.read(source)
    assert snapshot.format == "v2"
    assert {m for m, _ in DavStub.methods} == {"GET"}


def test_webdav_wrong_password(dav):
    with pytest.raises(SyncError, match="user name or password"):
        reader.read(WebDav(dav, "user", "wrong", "super-productivity"))


def test_webdav_empty_folder(dav):
    with pytest.raises(SyncError, match="No Super Productivity sync files"):
        reader.read(WebDav(dav, "user", "secret pass", "super-productivity"))


def test_webdav_unreachable():
    with pytest.raises(SyncError, match="Can't reach"):
        reader.read(WebDav("http://127.0.0.1:9/", "u", "p"))


@pytest.mark.parametrize("base, folder, url", [
    ("https://x.org/dav", "super-productivity", "https://x.org/dav/super-productivity/f"),
    ("https://x.org/dav/", "/a/b/", "https://x.org/dav/a/b/f"),
    ("https://x.org/dav/", "", "https://x.org/dav/f"),
])
def test_file_url(base, folder, url):
    assert file_url(base, folder, "f") == url


def test_file_url_needs_scheme():
    with pytest.raises(SyncError, match="https://"):
        file_url("cloud.example.org", "", "f")


def test_reads_encrypted_file_written_by_super_productivity():
    """Compressed and encrypted by Super Productivity 20.0.0 itself
    (tests/real_app/sp_sync.mjs, password "test password")."""
    source = LocalFolder(FIXTURES / "sync-encrypted")
    assert (FIXTURES / "sync-encrypted" / "sync-data.json").read_text().startswith("pf_CE2__")
    snapshot = reader.read(source, "test password")
    assert validate.problems(snapshot.data) == []
    titles = {t["title"] for t in snapshot.data["task"]["entities"].values()}
    assert "Sync test: water the plants" in titles
    with pytest.raises(crypto.WrongPassword):
        reader.read(source, "wrong")
    with pytest.raises(envelope.NeedsPassword):
        reader.read(source)
