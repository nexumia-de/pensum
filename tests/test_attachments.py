"""Task attachments as Super Productivity's task reducer and edit dialog
keep them (#25, pensum/store/attachments.py)."""
import pytest

from pensum.store import attachments, defaults, tasks, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_add_and_delete_links(ds):
    task = tasks.add_task(ds, "Plants", Context.today(), NOW)
    task["attachments"] = [{"id": "c", "type": "COMMAND", "path": "rm -rf ~", "title": "Run"}]
    link = attachments.add(ds, task["id"], " example.com/x ", "Shop", now=NOW + 1)
    assert link == {"type": "LINK", "path": "http://example.com/x", "id": link["id"],
                    "title": "Shop"}
    assert attachments.add(ds, task["id"], "//cdn.example/a.png", kind="IMG")["path"] == \
        "http://cdn.example/a.png"
    assert attachments.add(ds, task["id"], "https://a.example")["path"] == "https://a.example"
    assert "title" not in attachments.of_task(task)[-1]
    assert attachments.add(ds, task["id"], "   ") is None
    assert [a["type"] for a in attachments.of_task(task)] == ["COMMAND", "LINK", "IMG", "LINK"]
    assert task["modified"] >= NOW + 1
    assert attachments.delete(ds, task["id"], link["id"], NOW + 2)
    assert not attachments.delete(ds, task["id"], link["id"], NOW + 3)
    assert task["attachments"][0] == {"id": "c", "type": "COMMAND", "path": "rm -rf ~",
                                      "title": "Run"}
    assert validate.problems(ds.data) == []


def test_commands_and_strange_schemes_never_open():
    assert not attachments.can_open({"type": "COMMAND", "path": "ls"})
    assert not attachments.can_open({"type": "LINK", "path": "javascript:alert(1)"})
    assert not attachments.can_open({"type": "NOTE", "path": "text"})
    assert attachments.can_open({"type": "LINK", "path": "https://example.com"})
    assert attachments.can_open({"type": "FILE", "path": "/home/me/plan.pdf"})
    assert attachments.label({"path": "https://example.com"}) == "https://example.com"
