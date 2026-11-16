"""Starting a journey and setting up its task on Day Planner's journey
pages (QuestArc docs/behaviour.md, screen 3 and flow B,
docs/questarc-coverage.md): Pick a date, what the journey builds, and
why a station has no task (gone, ended, the earlier task). Needs a
display and the engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from pensum.game import content, records  # noqa: E402
from pensum.store import dates, tasks  # noqa: E402
from pensum.store.repeat import instances, rules  # noqa: E402
from journey_support import (button, fresh, iterate, labels, needs_engine, valid,  # noqa: E402
                             window_with)

pytestmark = needs_engine


def start_page(window, journey_id="gentle-morning", anchor_id=None):
    from pensum.ui.journey.start_page import StartPage
    window.show_journey()
    window.nav.push(StartPage(window, journey_id, anchor_id))
    iterate()
    return window.visible_page()


def run_records(window):
    return {k: v for k, v in window.journeys.records().items()
            if k.startswith(("run:", "build:"))}


def test_pick_a_date_starts_on_that_day_and_never_before_today(app, tmp_path):
    window = window_with(app, tmp_path, fresh())
    start = start_page(window)
    today = window.ds.today()
    later = dates.shift_day(today, 10)
    start._pick(later)
    assert start.date_check.get_active() and start.day == later
    start._pick(dates.shift_day(today, -3))
    assert start.day == today
    start._pick(later)
    start._main()
    iterate()
    run = next(v for k, v in run_records(window).items() if k.startswith("run:"))
    assert run["startDay"] == later
    valid(window)
    window.close()


def test_the_suggested_build_writes_nothing_and_a_change_is_written(app, tmp_path):
    window = window_with(app, tmp_path, fresh())
    start = start_page(window)
    journey = content.journey("gentle-morning")
    assert start.build.chosen == (journey.get("build") or {}).get("ladder", "home")
    assert any(s.startswith("You build: ") for s in labels(start.build.group))
    other = next(name for name in content.ladders() if name != start.build.chosen)
    start.build._choose(other)
    assert start.build.changes("x") == {"build:x": {"ladder": other}}
    start.build._choose(start.build.suggested)
    assert start.build.changes("x") == {}
    start.build._choose(other)
    start._main()
    iterate()
    built = [v for k, v in run_records(window).items() if k.startswith("build:")]
    assert built == [{"ladder": other}]
    assert window.journeys.active()["build"]["ladder"] == other
    valid(window)
    window.close()


def test_a_further_journey_at_a_moment_builds_more_of_the_same(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    records.write(ds, {"anchor:up": {"kind": "routine", "words": "getting up"}})
    demo_journey.finished(ds, ds.today(), anchor_id="up")
    window = window_with(app, tmp_path, ds)
    start = start_page(window, "walk-after-lunch", "up")
    assert start.build.further()
    assert start.build.group.get_description() == content.t("ui.start.grows-on")
    assert start.build.changes("x") == {}
    window.close()


def setup_page(window):
    from pensum.ui.journey.setup_page import SetupPage
    window.show_run()
    window.nav.push(SetupPage(window))
    iterate()
    return window.visible_page()


def test_a_station_whose_task_is_gone_says_so(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.met(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    bound = window.journeys.records()["binding:walk:water"]["taskId"]
    for task_id in [i for i, t in window.ds.tasks.items()
                    if t.get("repeatCfgId") == "walk-water" or i == bound]:
        tasks.delete(window.ds, task_id)
    rules.delete(window.ds, "walk-water")
    window.changed()
    window.journeys.refresh_now()
    assert window.journeys.active()["stations"][0]["state"] == "unbound"
    page = setup_page(window)
    assert content.t("ui.setup.gone") in labels(page)
    valid(window)
    window.close()


def test_starting_smaller_on_an_ended_task_says_it_ended(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.come_back(ds, ds.today())
    first = content.journey(demo_journey.JOURNEY)["stages"][0]["id"]
    cfg = ds.data["taskRepeatCfg"]["entities"][f"walk-{first}"]
    cfg["repeatUntilDay"] = dates.shift_day(ds.today(), -1)
    window = window_with(app, tmp_path, ds)
    run = window.journeys.active()
    assert window.journeys.action("stepBack", run, window.ds.today(), {"pause": False})
    assert window.journeys.active()["stations"][0]["state"] == "unbound"
    page = setup_page(window)
    assert content.t("ui.setup.ended") in labels(page)
    valid(window)
    window.close()


def test_the_next_station_names_the_earlier_task_and_opens_it(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.met(ds, ds.today())
    # Today's task of the first station, not yet done.
    cfg = ds.data["taskRepeatCfg"]["entities"]["walk-water"]
    cfg["lastTaskCreationDay"] = dates.shift_day(ds.today(), -1)
    assert instances.create_for(ds, cfg, ds.today(), dates.now_ms())
    window = window_with(app, tmp_path, ds)
    run = window.journeys.active()
    journey = window.journeys.journey(run["journeyId"])
    assert window.journeys.action("continueJourney", run, journey, window.ds.today())
    assert window.journeys.active()["stations"][1]["state"] == "unbound"
    page = setup_page(window)
    assert content.t("ui.setup.open-earlier") in labels(page)
    row = next(r for r in _rows(page) if r.get_title() == content.t("ui.setup.open-earlier"))
    row.emit("activated")
    iterate()
    assert window.visible_page().get_tag().startswith("task-")
    valid(window)
    window.close()


def _rows(widget):
    from gi.repository import Adw
    found = [widget] if isinstance(widget, Adw.ActionRow) else []
    child = widget.get_first_child()
    while child:
        found += _rows(child)
        child = child.get_next_sibling()
    return found


def test_a_habit_whose_task_is_gone_gets_a_task_again_from_the_shelf(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    stage_id = demo_journey.finished(ds, ds.today())
    rules.delete(ds, f"walk-{stage_id}")
    window = window_with(app, tmp_path, ds)
    habit = window.journeys.view["finished"][0]["habit"]
    assert habit["state"] == "unbound"
    window.show_journey()
    window.journey_page.show_shelf()
    iterate()
    shelf = window.visible_page()
    assert content.t("ui.shelf.no-task") in labels(shelf)
    button(shelf, content.t("ui.action.setup")).emit("clicked")
    iterate()
    setup = window.visible_page()
    assert setup.run_id == "walk"
    assert not any(s == content.t("ui.action.skip-stage") for s in labels(setup))
    setup._main()
    iterate()
    assert window.journeys.view["finished"][0]["habit"]["state"] == "maintained"
    assert window.visible_page() is shelf
    valid(window)
    window.close()
