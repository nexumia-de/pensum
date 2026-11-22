"""The day's evaluation in the slice `metric` (#23, pensum/store/metric.py)."""
import pytest

from pensum.store import defaults, metric, validate
from pensum.store.dataset import Dataset

NOW = 1_780_000_000_000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_impact_energy_and_reflection_upsert_the_day(ds):
    day = ds.today(NOW)
    metric.set_impact(ds, day, 3)
    entity = ds.data["metric"]["entities"][day]
    assert entity == {"id": day, "focusSessions": [], "remindTomorrow": False,
                      "reflections": [], "impactOfWork": 3}
    metric.set_energy(ds, day, 2)
    assert entity["energyCheckin"] == 2
    with pytest.raises(ValueError):
        metric.set_impact(ds, day, 5)
    with pytest.raises(ValueError):
        metric.set_energy(ds, day, 0)
    assert metric.set_reflection(ds, day, "  Good day  ", now=NOW)
    assert entity["reflections"] == [{"text": "Good day", "created": NOW}]
    assert metric.set_reflection(ds, day, "Better", now=NOW + 5)
    assert entity["reflections"] == [{"text": "Better", "created": NOW}]  # first save's time
    assert not metric.set_reflection(ds, day, " Better ", now=NOW + 6)
    assert metric.set_reflection(ds, day, "   ", now=NOW + 7)
    assert entity["reflections"] == []
    assert ds.data["metric"]["ids"] == [day]
    assert validate.problems(ds.data) == []
