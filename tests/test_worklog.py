"""The worklog and its CSV time sheet by Super Productivity's export
rules (#22, pensum/store/worklog.py)."""
from datetime import datetime

import pytest

from pensum.store import contexts, defaults, tasks, tracking, worklog
from pensum.store.dataset import Context, Dataset

NOW = 1_780_000_000_000
MIN = 60 * 1000
H = 60 * MIN


@pytest.fixture
def ds():
    return Dataset(defaults.fresh_dataset(NOW))


def at(day, hour, minute=0):
    return int(datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}").timestamp() * 1000)


def garden(ds):
    project = contexts.add_project(ds, "Garden")
    ctx = Context("project", project["id"])
    seeds = tasks.add_task(ds, "Seeds", ctx, NOW)
    water = tasks.add_task(ds, "=Water; now", ctx, NOW)
    tracking.set_time_on_day(ds, seeds["id"], "2026-05-26", 90 * MIN)
    tracking.set_time_on_day(ds, water["id"], "2026-05-26", 30 * MIN)
    tracking.set_time_on_day(ds, water["id"], "2026-05-27", 20 * MIN)
    tracking.set_time_on_day(ds, water["id"], "2026-05-01", 5 * MIN)  # outside the range
    days = ds.data["timeTracking"].setdefault("project", {}).setdefault(project["id"], {})
    days["2026-05-26"] = {"s": at("2026-05-26", 8, 7), "e": at("2026-05-26", 11, 52)}
    return project, ctx, seeds, water


def test_time_per_day_in_a_range(ds):
    project, ctx, seeds, water = garden(ds)
    found = worklog.tasks_in_range(ds, ctx, "2026-05-25", "2026-05-31")
    assert {t["id"] for t in found} == {seeds["id"], water["id"]}
    assert worklog.per_day(found) == {"2026-05-26": 120 * MIN, "2026-05-27": 20 * MIN}
    other = contexts.add_project(ds, "Other")
    assert worklog.tasks_in_range(ds, Context("project", other["id"]), "2026-05-01", "2026-05-31") == []


def test_csv_with_the_default_settings_groups_by_date(ds):
    project, ctx, seeds, water = garden(ds)
    text = worklog.csv_text(ds, ctx, "2026-05-25", "2026-05-31")
    assert text.split("\n") == [
        "Date;Start;End;Worked;Titles",
        # Only a field that starts like a formula gets the quote mark.
        '2026-05-26;08:07;11:52;2:00;"Seeds | =Water; now"',
        "2026-05-27; - ; - ;0:20;\"'=Water; now\"",
    ]
    assert worklog.file_name("2026-05-25", "2026-05-31") == "tasks2026-05-25-2026-05-31.csv"


def test_csv_follows_the_lists_settings(ds):
    project, ctx, seeds, water = garden(ds)
    project.setdefault("advancedCfg", {})["worklogExportSettings"] = {
        "cols": ["TITLES", "TIME_STR", "TIME_MS", "ESTIMATE_CLOCK", "PROJECTS", "", "TAGS"],
        "roundWorkTimeTo": "QUARTER", "groupBy": "TASK", "separateTasksBy": ", "}
    tasks.set_estimate(ds, seeds["id"], 2 * H, NOW)
    lines = worklog.csv_text(ds, ctx, "2026-05-25", "2026-05-31").split("\n")
    assert lines[0] == "Parent Titles;Worked;Worked;Estimate;Projects;Tags"
    rows = sorted(lines[1:])
    assert "Seeds;1h 30m;5400000;2:00;Garden; - " in rows
    # 50 minutes rounded up to the next quarter.
    assert "\"'=Water; now\";1h;3600000;-;Garden; - " in rows


def test_rounding_and_clock_strings():
    assert worklog.round_duration(52 * MIN, "QUARTER", True) == 60 * MIN
    assert worklog.round_duration(52 * MIN, "5M") == 50 * MIN
    assert worklog.round_duration(52 * MIN, None) == 52 * MIN
    assert worklog.ms_to_clock(0) == "-" and worklog.ms_to_clock(65 * MIN) == "1:05"
    assert worklog.ms_to_string(0) == "-" and worklog.ms_to_string(65 * MIN) == "1h 5m"
