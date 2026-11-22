"""The next days and moving tasks between them (#26, pensum/store/planner.py)."""
import pytest

from pensum.store import dates, defaults, planner, planning, tasks, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000
MIN = 60 * 1000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_seven_days_with_their_tasks_and_estimates(ds):
    today = ds.today(NOW)
    tomorrow = dates.shift_day(today, 1)
    inbox = Context("project", ds.default_project_id())
    a = tasks.add_task(ds, "a", Context.today(), NOW)
    b = tasks.add_task(ds, "b", inbox, NOW)
    c = tasks.add_task(ds, "c", inbox, NOW)
    planning.schedule_day(ds, b["id"], tomorrow, NOW)
    planning.schedule_day(ds, c["id"], tomorrow, NOW)
    tasks.set_estimate(ds, b["id"], 30 * MIN, NOW)
    tasks.set_estimate(ds, c["id"], 15 * MIN, NOW)
    found = planner.days(ds, today)
    assert [d for d, _, _ in found] == [dates.shift_day(today, i) for i in range(7)]
    assert [t["id"] for t in found[0][1]] == [a["id"]]
    assert [t["id"] for t in found[1][1]] == [b["id"], c["id"]]  # planner.days order
    assert found[1][2] == 45 * MIN
    assert all(not tasks_ for _, tasks_, _ in found[2:])

    later = dates.shift_day(today, 3)
    assert planner.move(ds, b["id"], later, NOW)
    assert not planner.move(ds, b["id"], later, NOW)
    found = planner.days(ds, today)
    assert [t["id"] for t in found[1][1]] == [c["id"]]
    assert [t["id"] for t in found[3][1]] == [b["id"]]
    assert ds.data["planner"]["days"][later] == [b["id"]]
    assert b["id"] not in ds.data["planner"]["days"].get(tomorrow, [])
    assert planner.move(ds, c["id"], today, NOW)
    assert [t["id"] for t in planner.days(ds, today)[0][1]] == [a["id"], c["id"]]
    assert validate.problems(ds.data) == []
