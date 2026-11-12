"""An import over newer local data (#47): what the current dataset has
that the file lacks, keeping QuestArc's records that exist only here,
and a consistent dataset after every path."""
import copy

import pytest

from pensum import demo
from pensum.game import records
from pensum.store import backup, incoming, tasks, validate
from pensum.store.dataset import Context, Dataset
from pensum.store.files import Files

# Later than every moment in the demo dataset (its instances are made at noon).
LATER = 6 * 3_600_000


@pytest.fixture
def now():
    return demo.demo_now()


@pytest.fixture
def local(now):
    return demo.create(now)


def journey_task(ds):
    binding = records.load(ds)["binding:demo:focus-15"]
    return binding["taskId"]


def export(ds):
    """The file another device would import: a copy of the dataset."""
    return Dataset(copy.deepcopy(ds.data))


def compare(current, file):
    return incoming.compare(current.data, file.data, records.PREFIX,
                            records.journey_ids(current))


def changed_after_export(local, now):
    """The file is yesterday's export; since then this device added a
    task, ticked off the journey's task, changed a setting record and
    answered a weekly look back (a record only here)."""
    file = export(local)
    later = now + LATER
    added = tasks.add_task(local, "Added after the export", Context.today(), later)
    tasks.set_done(local, journey_task(local), True, later)
    records.write(local, {"settings": {"mode": "calm"},
                          "checkin:demo:2026-W45": {"answer": 4}})
    return file, added


def test_older_file_loses_tasks_completions_and_changed_records(local, now):
    file, added = changed_after_export(local, now)
    loss = compare(local, file)
    assert set(loss.tasks) == {added["id"], journey_task(local)}
    assert [task_id for task_id, _ in loss.completions] == [journey_task(local)]
    assert loss.records == ("questarc:settings",)
    assert not loss.unrelated
    # The record only here is not lost: the import keeps it.
    assert "questarc:checkin:demo:2026-W45" not in loss.records


def test_newer_file_loses_nothing(local, now):
    file = export(local)
    later = now + LATER
    tasks.add_task(file, "Added on the other device", Context.today(), later)
    tasks.set_done(file, journey_task(file), True, later)
    records.write(file, {"settings": {"mode": "calm"}})
    assert not compare(local, file)


def test_same_data_loses_nothing(local):
    assert not compare(local, export(local))


def test_task_deleted_on_the_other_side_is_not_a_loss(local, now):
    file = export(local)
    victim = next(iter(file.data["task"]["ids"]))
    tasks.delete(file, victim)
    tasks.add_task(file, "Later change there", Context.today(), now + LATER)
    assert not compare(local, file)


def test_unrelated_file_loses_every_task(local, sp_backup):
    file = Dataset(backup.read(sp_backup))
    loss = compare(local, file)
    assert loss.unrelated
    assert set(loss.tasks) == set(incoming._tasks(local.data))
    # The journey's archived completions are among them.
    assert loss.completions


def test_withdrawn_record_in_the_file_stays_withdrawn(local, now, tmp_path):
    file = export(local)
    records.write(file, {"stage:demo:focus-15": ""})
    tasks.add_task(local, "Newer here", Context.today(), now + LATER)
    records.write(local, {"note:local-only": {"seen": True}})
    loss = compare(local, file)
    assert "questarc:stage:demo:focus-15" in loss.records
    files = Files(tmp_path / "pensum")
    imported = files.import_dataset(file, local, records.PREFIX)
    stored = incoming.records(imported.data, records.PREFIX)
    assert stored["questarc:stage:demo:focus-15"] == ""
    assert "stage:demo:focus-15" not in records.load(imported)
    assert records.load(imported)["note:local-only"] == {"seen": True}


def test_import_keeps_local_records_and_takes_the_files_values(local, now, tmp_path):
    file, _ = changed_after_export(local, now)
    files = Files(tmp_path / "pensum")
    imported = files.import_dataset(file, local, records.PREFIX)
    kept = records.load(imported)
    assert kept["checkin:demo:2026-W45"] == {"answer": 4}  # only here: kept
    assert kept["settings"] == {"mode": "rpg"}  # on both sides: the file's
    ids = [e["id"] for e in imported.data["pluginUserData"]]
    assert len(ids) == len(set(ids))
    # Saved as imported, and the current data is in the backups folder.
    assert records.load(files.load())["checkin:demo:2026-W45"] == {"answer": 4}
    assert any(files.backups.iterdir())


def test_other_plugins_are_not_merged(local, now):
    file = export(local)
    local.data["pluginUserData"].append({"id": "other:x", "data": "{}"})
    assert incoming.keep_records(local.data, file.data, records.PREFIX) == []
    assert all(e["id"] != "other:x" for e in file.data["pluginUserData"])


def test_file_without_plugin_data_gets_the_records(local):
    file = export(local)
    del file.data["pluginUserData"]
    kept = incoming.keep_records(local.data, file.data, records.PREFIX)
    assert kept and records.load(file) == records.load(local)


@pytest.mark.parametrize("make_file", ["older", "newer", "unrelated", "withdrawn"])
def test_every_import_path_keeps_the_dataset_valid(make_file, local, now, sp_backup,
                                                   tmp_path):
    if make_file == "older":
        file, _ = changed_after_export(local, now)
    elif make_file == "newer":
        file = export(local)
        tasks.add_task(file, "There", Context.today(), now + LATER)
    elif make_file == "unrelated":
        file = Dataset(backup.read(sp_backup))
    else:
        file = export(local)
        records.write(file, {"run:demo": ""})
        records.write(local, {"note:local-only": {"seen": True}})
    compare(local, file)
    imported = Files(tmp_path / "pensum").import_dataset(file, local, records.PREFIX)
    assert validate.problems(imported.data) == []
    assert validate.problems(local.data) == []
