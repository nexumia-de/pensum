"""Sending Day Planner's task edits to a sync folder (#30,
pensum.sync.writer): what counts as sendable, the ops and the file
written, refusals, encryption, WebDAV's conditional PUT, and the sync
page's Send Changes. Super Productivity reading what Pensum wrote is
checked by tests/real_app (run_sync.sh, round 3)."""
import copy
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pensum.store import tasks, tracking, validate
from pensum.store.dataset import Dataset
from pensum.sync import crypto, envelope, reader, replay, writer
from pensum.sync.local import LocalFolder
from pensum.sync.webdav import Changed, WebDav

from conftest import FIXTURES

NOW = 1_795_400_000_000
CLIENT = "PensumT1"


@pytest.fixture
def folder(tmp_path):
    shutil.copy(FIXTURES / "sync" / "sync-data.json", tmp_path / "sync-data.json")
    return LocalFolder(tmp_path)


def edited(snapshot):
    """The base and a copy with a new title, an estimate and a task done."""
    base = copy.deepcopy(snapshot.data)
    ds = Dataset(copy.deepcopy(snapshot.data))
    first, second = [t for t in ds.tasks.values()
                     if not t.get("isDone") and not t.get("parentId")][:2]
    tasks.update(ds, first["id"], title="Renamed in Pensum")
    tasks.set_estimate(ds, first["id"], 3_600_000)
    tasks.set_done(ds, second["id"], True)
    return base, ds, first["id"], second["id"]


def test_encrypt_and_compress_round_trip():
    text = envelope.encode({"x": "ü"}, "2", compressed=True, encrypted=True, password="pw")
    assert text.startswith("pf_CE2__")
    assert envelope.decode(text, "pw")[0] == {"x": "ü"}
    with pytest.raises(crypto.WrongPassword):
        envelope.decode(text, "other")
    assert envelope.encode({"x": 1}, "2") == 'pf_2__{"x":1}'


def test_only_title_notes_done_and_estimate_are_sendable(folder):
    snapshot = reader.read(folder)
    base, ds, first, second = edited(snapshot)
    changes, blocked = writer.local_changes(base, ds.data)
    assert blocked == []
    assert dict(changes) == {first: {"title": "Renamed in Pensum", "timeEstimate": 3_600_000},
                             second: {"isDone": True,
                                      "doneOn": ds.tasks[second]["doneOn"]}}
    tracking.add_time(ds, first, 60_000)
    assert writer.local_changes(base, ds.data)[1]  # time tracked: not sendable yet
    added = Dataset(copy.deepcopy(base))
    from pensum.store.dataset import Context
    tasks.add_task(added, "New", Context.today())
    assert writer.local_changes(base, added.data)[1]


def test_send_writes_ops_after_the_folders_clock(folder):
    snapshot = reader.read(folder)
    base, ds, first, second = edited(snapshot)
    before = envelope.decode(folder.read("sync-data.json"))[0]
    sent = writer.send(folder, None, ds.data, base, snapshot.sync_version, CLIENT, NOW)
    assert (sent.count, sent.sync_version) == (2, before["syncVersion"] + 1)
    after = envelope.decode(folder.read("sync-data.json"))[0]
    assert after["syncVersion"] == before["syncVersion"] + 1
    assert after["clientId"] == CLIENT and after["lastModified"] == NOW
    ops = after["recentOps"][-2:]
    assert after["recentOps"][:-2] == before["recentOps"]
    for op in ops:
        assert (op["a"], op["o"], op["e"], op["c"], op["sv"], op["s"]) == (
            "HU", "UPD", "TASK", CLIENT, after["syncVersion"], before["schemaVersion"])
        assert op["ds"] == [op["d"]] and op["p"]["entityChanges"] == []
        assert op["id"][14] == "7"  # UUID version 7
        for client, count in before["vectorClock"].items():
            assert op["v"][client] == count  # after everything the folder had
    assert [op["v"][CLIENT] for op in ops] == [1, 2]
    assert after["vectorClock"] == ops[-1]["v"]
    # `state` is what Super Productivity's reducers make of the ops.
    assert after["state"] == replay.apply(before["state"], ops, NOW)
    read = reader.read(folder)
    assert read.data["task"]["entities"][first]["title"] == "Renamed in Pensum"
    assert read.data["task"]["entities"][second]["isDone"] is True
    assert validate.problems(read.data) == []
    assert sent.data == read.data


def test_nothing_to_send_writes_nothing(folder):
    snapshot = reader.read(folder)
    text = folder.read("sync-data.json")
    sent = writer.send(folder, None, snapshot.data, snapshot.data, snapshot.sync_version, CLIENT)
    assert sent.count == 0 and folder.read("sync-data.json") == text


def test_blocked_changes_write_nothing(folder):
    snapshot = reader.read(folder)
    base, ds, first, _second = edited(snapshot)
    tracking.add_time(ds, first, 60_000)
    text = folder.read("sync-data.json")
    with pytest.raises(writer.Blocked, match="Not sendable"):
        writer.send(folder, None, ds.data, base, snapshot.sync_version, CLIENT)
    assert folder.read("sync-data.json") == text


def test_a_conflict_with_the_folder_writes_nothing(folder):
    snapshot = reader.read(folder)
    base, ds, first, _second = edited(snapshot)
    # The folder moved on since the base and changed the same task.
    payload = envelope.decode(folder.read("sync-data.json"))[0]
    payload["syncVersion"] += 1
    payload["recentOps"].append({"id": "x", "a": "HU", "o": "UPD", "e": "TASK", "d": first,
                                 "ds": [first], "p": {}, "c": "B_other", "v": {"B_other": 99},
                                 "t": 1, "s": 4, "sv": payload["syncVersion"]})
    (folder.path / "sync-data.json").write_text(envelope.encode(payload, "2"))
    with pytest.raises(writer.Blocked, match="same tasks"):
        writer.send(folder, None, ds.data, base, snapshot.sync_version, CLIENT)
    # Another task changed in the folder: Pensum's edits still go.
    payload["recentOps"][-1]["d"] = payload["recentOps"][-1]["ds"][0] = "someone-else"
    (folder.path / "sync-data.json").write_text(envelope.encode(payload, "2"))
    sent = writer.send(folder, None, ds.data, base, snapshot.sync_version, CLIENT)
    assert sent.sync_version == payload["syncVersion"] + 1


def test_a_file_changed_after_reading_is_not_overwritten(folder):
    text, version = folder.read_versioned("sync-data.json")
    (folder.path / "sync-data.json").write_text(text + " ")
    with pytest.raises(Changed):
        folder.write("sync-data.json", text, version)


def test_encrypted_folder_stays_encrypted(tmp_path):
    shutil.copy(FIXTURES / "sync-encrypted" / "sync-data.json", tmp_path / "sync-data.json")
    folder = LocalFolder(tmp_path)
    snapshot = reader.read(folder, "test password")
    base, ds, first, _second = edited(snapshot)
    writer.send(folder, "test password", ds.data, base, snapshot.sync_version, CLIENT)
    assert folder.read("sync-data.json").startswith("pf_CE2__")
    read = reader.read(folder, "test password")
    assert read.data["task"]["entities"][first]["title"] == "Renamed in Pensum"


# --- WebDAV: PUT only on the ETag read -------------------------------------

class DavStub(BaseHTTPRequestHandler):
    files, etags, methods = {}, {}, []

    def do_GET(self):
        type(self).methods.append(("GET", None))
        body = self.files.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("ETag", self.etags[self.path])
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        type(self).methods.append(("PUT", self.headers.get("If-Match")))
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.headers.get("If-Match") != self.etags.get(self.path):
            self.send_response(412)
            self.end_headers()
            return
        self.files[self.path] = body
        self.etags[self.path] = f'"{len(type(self).methods)}"'
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args):
        pass


def test_webdav_puts_on_the_etag_it_read(folder):
    path = "/dav/super-productivity/sync-data.json"
    DavStub.files = {path: (folder.path / "sync-data.json").read_bytes()}
    DavStub.etags, DavStub.methods = {path: '"1"'}, []
    server = ThreadingHTTPServer(("127.0.0.1", 0), DavStub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        source = WebDav(f"http://127.0.0.1:{server.server_port}/dav/", "u", "p")
        snapshot = reader.read(source)
        base, ds, _first, _second = edited(snapshot)
        writer.send(source, None, ds.data, base, snapshot.sync_version, CLIENT)
        assert ("PUT", '"1"') in DavStub.methods
        text, version = source.read_versioned("sync-data.json")
        DavStub.etags[path] = '"changed"'
        with pytest.raises(Changed):
            source.write("sync-data.json", text, version)
    finally:
        server.shutdown()


# --- the sync page --------------------------------------------------------

def test_sync_page_sends_changes(app, tmp_path):
    """Import once, edit a task, Send Changes: the folder has the edit,
    Day Planner shows the folder's data, the base follows."""
    import os
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        pytest.skip("needs a display")
    from journey_support import fresh, iterate, window_with
    from pensum.sync import base
    folder = tmp_path / "sync"
    shutil.copytree(FIXTURES / "sync", folder)
    window = window_with(app, tmp_path, fresh())
    window.settings.sync_kind = "local"
    window.settings.sync_local_path = str(folder)
    window.show_sync()
    iterate()
    page = window.nav.get_visible_page()
    page.send(wait=True)  # nothing imported yet
    assert page.banner.get_revealed() and "import it once" in page.banner.get_title()
    page.read(wait=True)
    page.import_now()
    version = page.settings.sync_seen_version
    assert base.load(window.files, page.source_key)[0] == version
    task = next(t for t in window.ds.tasks.values() if not t.get("isDone"))
    tasks.update(window.ds, task["id"], title="Sent from the page")
    page.send(wait=True)
    iterate()
    read = reader.read(LocalFolder(folder))
    assert read.sync_version == version + 1
    assert read.data["task"]["entities"][task["id"]]["title"] == "Sent from the page"
    assert base.load(window.files, page.source_key)[0] == version + 1
    assert validate.problems(window.ds.data) == []
    window.close()
    iterate()
