"""Folders in the menu tree as Super Productivity keeps them (#27,
pensum/store/menu_tree.py)."""
import pytest

from pensum.store import contexts, defaults, menu_tree, validate
from pensum.store.dataset import Dataset

NOW = 1_780_000_000_000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def ids(ds):
    return [p["id"] for p in ds.projects()]


def test_folders_hold_lists_and_close(ds):
    a = contexts.add_project(ds, "A")["id"]
    b = contexts.add_project(ds, "B")["id"]
    inbox = ds.default_project_id()
    assert menu_tree.add_folder(ds, "project", "   ") is None
    work = menu_tree.add_folder(ds, "project", " Work ")
    assert work == {"k": "f", "id": work["id"], "name": "Work", "isExpanded": True, "children": []}
    assert len(work["id"]) == 36
    menu_tree.move_to_folder(ds, "project", b, work["id"])
    assert menu_tree.folder_of(ds, "project", b) == work["id"]
    assert menu_tree.folder_of(ds, "project", a) is None
    entries = menu_tree.entries(ds, "project", ids(ds))
    assert ("folder", work, 0) in entries and ("item", b, 1) in entries
    assert ("item", a, 0) in entries and ("item", inbox, 0) in entries
    sub = menu_tree.add_folder(ds, "project", "Sub", work["id"])
    assert menu_tree.folders(ds, "project") == [(work["id"], "Work", 0), (sub["id"], "Sub", 1)]
    menu_tree.move_to_folder(ds, "project", b, sub["id"])
    assert work["children"] == [sub] and sub["children"] == [{"k": "p", "id": b}]
    assert menu_tree.set_expanded(ds, "project", work["id"], False)
    assert [e[1] for e in menu_tree.entries(ds, "project", ids(ds)) if e[0] == "item"] \
        == [i for i in ids(ds) if i != b]
    assert menu_tree.rename_folder(ds, "project", work["id"], "Job")
    menu_tree.move_to_folder(ds, "project", b, None)
    assert menu_tree.folder_of(ds, "project", b) is None
    assert validate.problems(ds.data) == []


def test_deleting_a_folder_keeps_its_lists_in_the_menu(ds):
    a = contexts.add_project(ds, "A")["id"]
    folder = menu_tree.add_folder(ds, "project", "F")
    menu_tree.move_to_folder(ds, "project", a, folder["id"])
    assert menu_tree.delete_folder(ds, "project", folder["id"])
    assert menu_tree.folders(ds, "project") == []
    assert a in ids(ds)
    tag = contexts.add_tag(ds, "T")["id"]
    tags_folder = menu_tree.add_folder(ds, "tag", "Tags")
    menu_tree.move_to_folder(ds, "tag", tag, tags_folder["id"])
    assert ds.data["menuTree"]["tagTree"][-1]["children"] == [{"k": "t", "id": tag}]
    assert validate.problems(ds.data) == []
