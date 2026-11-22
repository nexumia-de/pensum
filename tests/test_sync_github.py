"""A sync folder in a GitHub repository kept by Git Sync (pensum.sync.github,
docs/git-sync.md), against tests/github_fake.py on a real bare
repository. The desktop's side (the plugin in nexumia-de/tabularium) is
played with git commands: it pushes main and fast-forwards main to
`day-planner`. Super Productivity itself is in tests/real_app
(run_sync.sh, scenario git)."""
import copy
import shutil
import subprocess

import pytest

from pensum.store import tasks, validate
from pensum.store.dataset import Dataset
from pensum.sync import SyncError, reader, writer
from pensum.sync.github import GitHub, parse_repository
from pensum.sync.local import LocalFolder
from pensum.sync.webdav import Changed

from conftest import FIXTURES
from github_fake import serve

NOW = 1_795_400_000_000
TOKEN = "test"
REPO = "test/sync"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=T", "-c", "user.email=t@t",
                           *args], check=True, capture_output=True, text=True).stdout.strip()


class Desktop:
    """The sync folder on the desktop: a clone that only the plugin pushes."""

    def __init__(self, tmp_path):
        self.origin = tmp_path / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        self.folder = tmp_path / "desktop"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.folder)], check=True,
                       capture_output=True)
        git(self.folder, "checkout", "-q", "-B", "main")
        shutil.copy(FIXTURES / "sync" / "sync-data.json", self.folder / "sync-data.json")
        self.push("Super Productivity sync")

    def push(self, message):
        git(self.folder, "add", "-A")
        git(self.folder, "commit", "-q", "-m", message)
        git(self.folder, "push", "-q", "origin", "HEAD:main")

    def take_handoff(self):
        """The plugin's prepare step: fast-forward to day-planner."""
        git(self.folder, "fetch", "-q", "origin")
        git(self.folder, "merge", "-q", "--ff-only", "origin/day-planner")
        git(self.folder, "push", "-q", "origin", "HEAD:main")

    def ref(self, branch):
        return git(self.origin, "rev-parse", f"refs/heads/{branch}")


@pytest.fixture
def env(tmp_path):
    desktop = Desktop(tmp_path)
    server, api = serve(desktop.origin, token=TOKEN, repository=REPO)
    yield desktop, (lambda: GitHub(REPO, TOKEN, api=api)), api
    server.shutdown()


def edit(snapshot, title="Renamed on the phone", which=0):
    base = copy.deepcopy(snapshot.data)
    ds = Dataset(copy.deepcopy(snapshot.data))
    task = [t for t in ds.tasks.values() if not t.get("isDone") and not t.get("parentId")][which]
    tasks.update(ds, task["id"], title=title)
    return base, ds, task["id"]


def test_parse_repository():
    assert parse_repository(" owner/name ") == "owner/name"
    assert parse_repository("https://github.com/owner/name.git") == "owner/name"
    assert parse_repository("github.com/owner/name/") == "owner/name"
    for bad in ("owner", "owner/name/x", "/name", "owner/ na", ""):
        with pytest.raises(SyncError):
            parse_repository(bad)


def test_reads_main_like_the_folder(env):
    desktop, github, _api = env
    read = reader.read(github())
    on_disk = reader.read(LocalFolder(desktop.folder))
    assert read.data == on_disk.data and read.sync_version == on_disk.sync_version
    assert github().state()["pending"] is False


def test_send_hands_over_on_day_planner_and_leaves_main(env):
    desktop, github, _api = env
    main_before = desktop.ref("main")
    snapshot = reader.read(github())
    base, ds, task = edit(snapshot)
    sent = writer.send(github(), None, ds.data, base, snapshot.sync_version, "PensumT1", NOW)
    assert (sent.count, sent.sync_version) == (1, snapshot.sync_version + 1)
    assert sent.data["task"]["entities"][task]["title"] == "Renamed on the phone"
    assert desktop.ref("main") == main_before
    assert git(desktop.origin, "rev-parse", "day-planner^") == main_before
    assert git(desktop.origin, "log", "-1", "--format=%an", "day-planner") == "Day Planner"
    # Until the desktop takes it, reads and the next send build on it.
    pending = github()
    assert pending.state()["pending"] is True
    assert reader.read(pending).sync_version == sent.sync_version
    base2, ds2, task2 = edit(reader.read(github()), "Second edit", which=1)
    writer.send(github(), None, ds2.data, base2, sent.sync_version, "PensumT1", NOW + 1)
    assert git(desktop.origin, "rev-list", "--count", "main..day-planner") == "2"
    # The desktop fast-forwards; afterwards Day Planner reads main again.
    desktop.take_handoff()
    delivered = github()
    assert delivered.state() == {"view": desktop.ref("main"), "handoff": desktop.ref("main"),
                                 "pending": False, "stale": None}
    data = reader.read(delivered).data
    assert data["task"]["entities"][task]["title"] == "Renamed on the phone"
    assert data["task"]["entities"][task2]["title"] == "Second edit"
    assert validate.problems(data) == []


def test_a_send_after_delivery_starts_from_main(env):
    desktop, github, _api = env
    snapshot = reader.read(github())
    base, ds, _task = edit(snapshot)
    sent = writer.send(github(), None, ds.data, base, snapshot.sync_version, "PensumT1", NOW)
    desktop.take_handoff()
    # Super Productivity syncs on the desktop and pushes on top.
    (desktop.folder / "note.txt").write_text("sp")
    desktop.push("Super Productivity sync")
    base2, ds2, _task2 = edit(reader.read(github()), "Later", which=1)
    writer.send(github(), None, ds2.data, base2, sent.sync_version, "PensumT1", NOW + 1)
    assert git(desktop.origin, "rev-parse", "day-planner^") == desktop.ref("main")


def test_stale_send_is_detected_and_sent_again(env):
    """The desktop synced on top of the old main before taking the send:
    the send is reported and goes out again with the new edits."""
    from pensum.ui.sync_send import _stale_base
    desktop, github, _api = env
    snapshot = reader.read(github())
    base, ds, first = edit(snapshot)
    sent = writer.send(github(), None, ds.data, base, snapshot.sync_version, "PensumT1", NOW)
    phone = Dataset(copy.deepcopy(sent.data))
    # Super Productivity changes another task and syncs outside the plugin.
    sp = reader.read(LocalFolder(desktop.folder))
    sp_base, sp_ds, sp_task = edit(sp, "Changed on the desktop", which=2)
    writer.send(LocalFolder(desktop.folder), None, sp_ds.data, sp_base, sp.sync_version,
                "SuperPr1", NOW + 5)
    desktop.push("Super Productivity sync (outside Git Sync)")

    stale = github()
    assert stale.is_stale()
    assert reader.read(stale).data["task"]["entities"][first]["title"] != "Renamed on the phone"
    version, base_data = _stale_base(stale, None)
    assert version == snapshot.sync_version and base_data == snapshot.data
    tasks.update(phone, phone.tasks[first]["id"], notes="and a note")
    again = writer.send(stale, None, phone.data, base_data, version, "PensumT1", NOW + 10)
    assert again.count == 1  # the renamed task, with the new note, in one op
    assert git(desktop.origin, "rev-parse", "day-planner^") == desktop.ref("main")
    desktop.take_handoff()
    data = reader.read(LocalFolder(desktop.folder)).data
    assert data["task"]["entities"][first]["title"] == "Renamed on the phone"
    assert data["task"]["entities"][first]["notes"] == "and a note"
    assert data["task"]["entities"][sp_task]["title"] == "Changed on the desktop"
    assert validate.problems(data) == []
    assert not github().is_stale()


def test_concurrent_writes_and_wrong_token_are_refused(env):
    desktop, github, api = env
    snapshot = reader.read(github())
    first, second = github(), github()
    first.state(), second.state()
    base, ds, _task = edit(snapshot)
    writer.send(first, None, ds.data, base, snapshot.sync_version, "PensumT1", NOW)
    with pytest.raises(Changed):
        writer.send(second, None, ds.data, base, snapshot.sync_version, "PensumT1", NOW)
    with pytest.raises(SyncError, match="refused the token"):
        reader.read(GitHub(REPO, "wrong", api=api))


def test_folder_in_the_repository_and_empty_repository(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    server, api = serve(origin, token=TOKEN, repository=REPO)
    try:
        with pytest.raises(SyncError, match="No Super Productivity sync files"):
            reader.read(GitHub(REPO, TOKEN, api=api))
        work = tmp_path / "work"
        subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True,
                       capture_output=True)
        (work / "sp").mkdir()
        shutil.copy(FIXTURES / "sync" / "sync-data.json", work / "sp" / "sync-data.json")
        git(work, "checkout", "-q", "-B", "main")
        git(work, "add", "-A")
        git(work, "commit", "-q", "-m", "sync")
        git(work, "push", "-q", "origin", "main")
        read = reader.read(GitHub(REPO, TOKEN, "/sp/", api=api))
        assert read.data == reader.read(LocalFolder(work / "sp")).data
    finally:
        server.shutdown()


def test_sync_page_reads_and_sends_through_github(app, tmp_path, env, monkeypatch):
    import os
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        pytest.skip("needs a display")
    from journey_support import fresh, iterate, window_with
    from pensum.sync import github as github_module
    desktop, github, api = env
    monkeypatch.setattr(github_module, "API", api)
    window = window_with(app, tmp_path, fresh())
    window.show_sync()
    iterate()
    page = window.nav.get_visible_page()
    page.kind_row.set_selected(2)
    assert page.repo_row.get_visible() and not page.url_row.get_visible()
    page.repo_row.set_text(REPO)
    page.read(wait=True)
    assert page.banner.get_revealed() and "access token" in page.banner.get_title()
    page.token_row.set_text(TOKEN)
    page.read(wait=True)
    iterate()
    assert not page.banner.get_revealed() and page.snapshot is not None
    page.import_now()
    assert window.settings.sync_kind == "github"
    assert window.settings.sync_github_repo == REPO
    task = next(t for t in window.ds.tasks.values() if not t.get("isDone"))
    tasks.update(window.ds, task["id"], title="Sent through GitHub")
    page.send(wait=True)
    iterate()
    assert not page.banner.get_revealed()
    desktop.take_handoff()
    data = reader.read(LocalFolder(desktop.folder)).data
    assert data["task"]["entities"][task["id"]]["title"] == "Sent through GitHub"
    window.close()
    iterate()
