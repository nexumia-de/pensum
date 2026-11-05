"""Reading and writing Super Productivity backups."""
import json

import pytest

from pensum.store import autobackup, backup, defaults, validate
from pensum.store.dataset import Dataset
from pensum.store.files import Files


def test_reads_exported_backup_with_archives(sp_backup):
    data = backup.read(sp_backup)
    assert data["task"]["ids"] == ["active-task-1"]
    assert data["archiveYoung"]["task"]["ids"]
    assert validate.problems(data) == []


def test_reads_bare_dataset_of_desktop_backups(frozen_state):
    data = backup.read(frozen_state)
    assert set(data["task"]["entities"]) == {"task-1", "task-2", "task-3"}


def test_round_trip_keeps_every_field(sp_backup, tmp_path):
    original = json.loads(sp_backup.read_text())
    out = tmp_path / "export.json"
    backup.write(out, backup.read(sp_backup), now=1)
    written = json.loads(out.read_text())
    assert written["crossModelVersion"] == defaults.CROSS_MODEL_VERSION
    for name, value in original["data"].items():
        assert written["data"][name] == value, name
    # Slices the file lacks get their empty state, as in Super Productivity.
    assert written["data"]["section"] == defaults.slices()["section"]


@pytest.mark.parametrize("text, message", [
    ("no json", "no JSON"),
    ('{"crossModelVersion": 9, "timestamp": 1, "data": {}}', "newer"),
    ('{"crossModelVersion": 3, "timestamp": 1, "data": {}}', "old data model"),
    ('{"task": {}}', "missing"),
])
def test_refuses_what_it_cannot_open(text, message):
    with pytest.raises(backup.BackupError, match=message):
        backup.parse(text)


def test_fresh_dataset_is_valid_and_complete():
    data = defaults.fresh_dataset(now=1)
    assert validate.problems(data) == []
    assert data["project"]["ids"] == [defaults.INBOX_ID]
    assert data["tag"]["ids"] == [defaults.TODAY_ID]
    assert data["globalConfig"]["tasks"]["defaultProjectId"] == defaults.INBOX_ID


def test_files_save_load_import_export(sp_backup, tmp_path):
    files = Files(tmp_path / "pensum")
    ds = files.load()
    files.save(ds)
    assert files.path.exists() and autobackup.listing(files.backups)
    imported = files.import_file(sp_backup, ds)
    assert "active-task-1" in imported.tasks
    assert "active-task-1" in files.load().tasks
    out = tmp_path / "out.json"
    files.export_file(out, imported)
    assert backup.read(out)["task"]["ids"] == ["active-task-1"]


def test_broken_data_file_falls_back_to_newest_backup(tmp_path):
    files = Files(tmp_path / "pensum")
    ds = files.load()
    files.save(ds)
    files.path.write_text("{broken")
    assert isinstance(files.load(), Dataset)
    assert files.path.with_suffix(".json.bad").exists()


def test_autobackup_keeps_recent_and_daily(tmp_path):
    from datetime import datetime, timedelta
    start = datetime(2026, 1, 1, 12)
    for i in range(60):
        autobackup.write(tmp_path, {"n": i}, start + timedelta(days=i))
    names = [p.name for p in autobackup.listing(tmp_path)]
    assert len(names) == autobackup.KEEP_RECENT
    assert names[0].startswith("2026-03-01")
