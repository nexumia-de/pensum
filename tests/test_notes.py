"""Project notes as Super Productivity's note and project reducers keep
them (#24, pensum/store/notes.py)."""
import pytest

from pensum.store import contexts, defaults, notes, validate
from pensum.store.dataset import Dataset

NOW = 1_780_000_000_000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def valid(ds):
    assert validate.problems(ds.data) == []


def test_add_pin_edit_delete_keep_the_lists_in_step(ds):
    project = contexts.add_project(ds, "Garden")
    first = notes.add(ds, project["id"], "# Seeds\nbuy them", now=NOW)
    second = notes.add(ds, project["id"], "Water", pinned_to_today=True, now=NOW + 1)
    valid(ds)
    assert first == {"id": first["id"], "projectId": project["id"], "isPinnedToToday": False,
                     "content": "# Seeds\nbuy them", "created": NOW, "modified": NOW}
    # New notes go on top, as addNote does.
    assert project["noteIds"] == [second["id"], first["id"]]
    assert ds.data["note"]["ids"][:2] == [second["id"], first["id"]]
    assert ds.data["note"]["todayOrder"] == [second["id"]]
    assert [n["id"] for n in notes.of_project(ds, project["id"])] == [second["id"], first["id"]]
    assert notes.title(first) == "Seeds"

    assert notes.set_pinned(ds, first["id"], True, NOW + 2)
    assert ds.data["note"]["todayOrder"] == [first["id"], second["id"]]
    assert [n["id"] for n in notes.pinned(ds)] == [first["id"], second["id"]]
    notes.set_pinned(ds, first["id"], True, NOW + 3)  # already listed: no second entry
    assert ds.data["note"]["todayOrder"].count(first["id"]) == 1
    notes.set_pinned(ds, second["id"], False, NOW + 4)
    assert ds.data["note"]["todayOrder"] == [first["id"]]
    valid(ds)

    assert notes.set_content(ds, first["id"], "Seeds", NOW + 5)
    assert first["modified"] == NOW + 5
    assert not notes.set_content(ds, first["id"], "Seeds", NOW + 6)

    assert notes.delete(ds, first["id"])
    assert first["id"] not in ds.data["note"]["entities"]
    assert first["id"] not in ds.data["note"]["ids"]
    assert ds.data["note"]["todayOrder"] == []
    assert project["noteIds"] == [second["id"]]
    valid(ds)


def test_deleting_the_project_takes_its_notes(ds):
    project = contexts.add_project(ds, "Garden")
    note = notes.add(ds, project["id"], "x", pinned_to_today=True, now=NOW)
    contexts.delete_project(ds, project["id"])
    assert note["id"] not in ds.data["note"]["entities"]
    assert ds.data["note"]["todayOrder"] == []
    valid(ds)
