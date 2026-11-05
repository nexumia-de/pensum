"""Short syntax in the add field, with Super Productivity's characters."""
import pytest

from pensum.store import contexts, defaults, short_syntax, tasks, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000  # Thursday, 2026-05-28
TODAY = "2026-05-28"


@pytest.fixture
def ds():
    ds = Dataset(defaults.fresh_dataset(NOW))
    contexts.add_project(ds, "Website Relaunch", entity_id="web")
    contexts.add_tag(ds, "calls", NOW, entity_id="calls")
    return ds


@pytest.mark.parametrize("text, title, expect", [
    ("Call Bob #calls", "Call Bob", {"tag_titles": ["calls"]}),
    ("Fix menu +Website", "Fix menu", {"project_id": "web"}),
    ("Fix menu +website relaunch #urgent", "Fix menu",
     {"project_id": "web", "tag_titles": ["urgent"]}),
    ("Write 1h 30m", "Write", {"estimate": 5_400_000}),
    ("Write 10m/1h", "Write", {"spent": 600_000, "estimate": 3_600_000}),
    ("Pay p1", "Pay", {"priority": 3}),
    ("Pay @tomorrow", "Pay", {"due_day": "2026-05-29"}),
    ("Pay @fri", "Pay", {"due_day": "2026-05-29"}),
    ("Pay @thu", "Pay", {"due_day": "2026-06-04"}),
    ("Meet @today 14:30", "Meet", {"due_day": TODAY, "due_time": (14, 30)}),
    ("Room #42 stays", "Room #42 stays", {}),
    ("mail me@home", "mail me@home", {}),
    ("Buy +garden tools", "Buy +garden tools", {}),
])
def test_parse(ds, text, title, expect):
    parsed = short_syntax.parse(ds, text, TODAY)
    assert parsed.title == title
    for key, value in expect.items():
        assert getattr(parsed, key) == value, key


def test_switches_off(ds):
    ds.config["shortSyntax"]["isEnableTag"] = False
    assert short_syntax.parse(ds, "a #calls", TODAY).title == "a #calls"


def test_apply(ds):
    parsed = short_syntax.parse(ds, "Call Bob +web #calls #new 20m p2 @tomorrow", TODAY)
    task = tasks.add_task(ds, parsed.title, Context.today(), NOW)
    short_syntax.apply(ds, task, parsed, NOW)
    assert task["title"] == "Call Bob" and task["projectId"] == "web"
    assert task["tagIds"][0] == "calls" and len(task["tagIds"]) == 2
    assert task["timeEstimate"] == 1_200_000 and task["priority"] == 2
    assert task["dueDay"] == "2026-05-29"
    assert validate.problems(ds.data) == []
