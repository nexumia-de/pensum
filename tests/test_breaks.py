"""The break reminder's counter and the breaks counted in timeTracking
(#20, pensum/store/breaks.py)."""
import pytest

from pensum.store import breaks, defaults, validate
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000
MIN = 60 * 1000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_reminder_after_an_hour_of_tracked_work_and_snooze():
    counter, cfg = breaks.Counter(), {}
    counter.tick(60 * MIN, True)
    assert not counter.due(NOW, cfg)  # more than the minimum, not equal
    counter.tick(1000, True)
    assert counter.due(NOW, cfg)
    counter.snooze(NOW, cfg)
    assert not counter.due(NOW + 14 * MIN, cfg)
    assert counter.due(NOW + 15 * MIN, cfg)
    assert not counter.due(NOW, {"takeABreak": {"isTakeABreakEnabled": False}})
    assert not counter.due(NOW + 15 * MIN, {"takeABreak": {"takeABreakMinWorkingTime": 90 * MIN}})


def test_ten_minutes_without_a_task_reset_the_counter():
    counter = breaks.Counter()
    counter.tick(50 * MIN, True)
    counter.tick(10 * MIN, False)
    assert counter.worked == 50 * MIN  # not more than ten minutes yet
    counter.tick(1000, False)
    assert counter.worked == 0
    counter.tick(5 * MIN, True)
    counter.tick(30 * MIN, False)  # a reset fires once per untracked stretch
    assert counter.worked == 0


def test_a_break_counts_on_the_active_list(ds):
    day = ds.today(NOW)
    assert breaks.add_break(ds, Context.today(), day, 5 * MIN)
    assert breaks.add_break(ds, Context.today(), day, 7 * MIN)
    project = ds.default_project_id()
    assert breaks.add_break(ds, Context("project", project), day, 3 * MIN)
    assert not breaks.add_break(ds, Context.today(), day, 0)
    assert ds.data["timeTracking"]["tag"]["TODAY"][day] == {"b": 2, "bt": 12 * MIN}
    assert ds.data["timeTracking"]["project"][project][day] == {"b": 1, "bt": 3 * MIN}
    assert breaks.breaks_on(ds, day) == (3, 15 * MIN)
    assert validate.problems(ds.data) == []
