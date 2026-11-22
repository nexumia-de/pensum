"""Focus sessions by Super Productivity's strategies, logged in
`metric.focusSessions` (#19, pensum/store/focus.py, metric.py)."""
import pytest

from pensum.store import defaults, focus, metric, validate
from pensum.store.dataset import Dataset

NOW = 1_780_000_000_000
MIN = 60 * 1000


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def test_pomodoro_has_a_longer_break_after_every_fourth_session(ds):
    config = {"pomodoro": {"duration": 25 * MIN, "breakDuration": 5 * MIN,
                           "longerBreakDuration": 15 * MIN, "cyclesBeforeLongerBreak": 4}}
    session = focus.Session("Pomodoro", config, NOW)
    t = NOW
    breaks = []
    for _ in range(4):
        assert session.phase == "work" and session.remaining(t) == 25 * MIN
        t += 25 * MIN
        assert session.is_due(t)
        worked, has_break = session.end_work(t)
        assert worked == 25 * MIN and has_break
        breaks.append(session.length)
        t += session.length
        session.end_break(t)
    assert breaks == [5 * MIN, 5 * MIN, 5 * MIN, 15 * MIN]
    assert session.cycle == 5 and session.phase == "work"


def test_pomodoro_reads_the_defaults_for_missing_settings():
    assert focus.pomodoro_config({})["duration"] == 25 * MIN
    assert focus.pomodoro_config({"pomodoro": {"duration": 50 * MIN}})["breakDuration"] == 5 * MIN


def test_flowtime_break_by_ratio_and_by_rule():
    assert focus.flowtime_break({}, 60 * MIN) is None  # breaks off by default
    ratio = {"flowtime": {"isBreakEnabled": True, "breakMode": "ratio", "breakPercentage": 20}}
    assert focus.flowtime_break(ratio, 50 * MIN) == 10 * MIN
    assert focus.flowtime_break(ratio, 2 * MIN) == MIN  # at least a minute
    rule = {"flowtime": {"isBreakEnabled": True, "breakMode": "rule", "breakRules": [
        {"minDuration": 0, "maxDuration": 30 * MIN, "breakDuration": 3 * MIN},
        {"minDuration": 30 * MIN, "maxDuration": None, "breakDuration": 8 * MIN}]}}
    assert focus.flowtime_break(rule, 29 * MIN) == 3 * MIN
    assert focus.flowtime_break(rule, 30 * MIN) == 8 * MIN
    session = focus.Session("Flowtime", ratio, NOW)
    assert session.remaining(NOW + MIN) is None and not session.is_due(NOW + 99 * MIN)
    worked, has_break = session.end_work(NOW + 50 * MIN)
    assert worked == 50 * MIN and has_break and session.length == 10 * MIN
    session.end_break(NOW + 60 * MIN)
    assert session.phase == "done"


def test_countdown_follows_the_estimate_left_and_has_no_break():
    assert focus.countdown_for_task(25 * MIN, {"timeEstimate": 15 * MIN, "timeSpent": 0}) == 15 * MIN
    assert focus.countdown_for_task(25 * MIN, {"timeEstimate": 10 * MIN + 1, "timeSpent": 0}) == 11 * MIN
    assert focus.countdown_for_task(25 * MIN, {"timeEstimate": 0, "timeSpent": 0}) == 25 * MIN
    session = focus.Session("Countdown", {}, NOW, countdown_ms=10 * MIN)
    worked, has_break = session.end_work(NOW + 12 * MIN)
    assert worked == 10 * MIN and not has_break and session.phase == "done"


def test_pause_tracking_in_breaks_defaults_on():
    assert focus.pause_tracking_in_breaks({})
    assert not focus.pause_tracking_in_breaks({"focusMode": {"isPauseTrackingDuringBreak": False}})


def test_sessions_are_logged_per_day(ds):
    day = ds.today(NOW)
    assert metric.for_day(ds, day) == {"id": day, "focusSessions": [], "remindTomorrow": False,
                                       "reflections": []}
    assert metric.log_focus_session(ds, day, 25 * MIN)
    assert metric.log_focus_session(ds, day, 10 * MIN)
    assert not metric.log_focus_session(ds, day, 0)
    assert ds.data["metric"]["entities"][day]["focusSessions"] == [25 * MIN, 10 * MIN]
    assert ds.data["metric"]["ids"] == [day]
    assert validate.problems(ds.data) == []
