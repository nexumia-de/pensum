"""QuestArc's flows on Day Planner's journey pages, through the real
widgets (pensum#58, #64, docs/questarc-coverage.md): the engine's guard
and the read-only page, stay and skip, the long break, graduation, pair
it with, the plan check and reminders. Every write goes through the
engine's actions; the dataset stays valid. Needs a display and the
engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)."""
import copy
import json
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from pensum.game import content, engine, records  # noqa: E402
from journey_support import (button, fresh, iterate, labels, needs_engine,  # noqa: E402
                             started, stored, valid, window_with)

pytestmark = needs_engine


# --- #58: the guard and the read-only page ------------------------------

def test_a_journey_of_a_newer_questarc_is_read_only_and_never_written(app, tmp_path):
    """A run with a record of a newer data format shows the read-only page
    (title and one sentence, no Pause or End, no main action); trying to
    pause or end it leaves the stored dataset byte for byte as it was."""
    ds = fresh()
    journey = started(ds)
    stage = journey["stages"][0]["id"]
    records.write(ds, {f"stage-done:r:{stage}": {"day": ds.today(), "dataFormat": 99}})
    window = window_with(app, tmp_path, ds)
    model = window.journeys
    assert model.active() is None
    assert model.read_only()["reason"] == "newer-format"
    window.show_journey()
    iterate()
    home = window.visible_page()
    assert content.t("ui.read-only.newer") in labels(home)
    assert not home.bottom.get_visible()
    window.show_run()
    iterate()
    page = window.visible_page()
    assert type(page).__name__ == "RunPage"
    assert page.title.get_title() == "A gentle morning"
    assert content.t("ui.read-only.newer") in labels(page)
    assert not page.bottom.get_visible()
    menu = page.menu_button.get_menu_model()
    actions = [menu.get_item_attribute_value(i, "action", None)
               for i in range(menu.get_n_items())]
    assert "journey.pause" not in [a and a.get_string() for a in actions]
    before = stored(window)
    for name, args in (("pauseJourney", ("r", ds.today())), ("endJourney", ("r", ds.today()))):
        assert model.action(name, *args) is False
    assert stored(window) == before
    valid(window)
    window.close()


def test_the_guard_keeps_records_it_does_not_understand(app, tmp_path):
    """Writing keeps every QuestArc record Day Planner does not know, also
    GZ1-packed ones, untouched; a write of an unknown kind is refused as a
    whole."""
    ds = fresh()
    started(ds)
    packed = records.encode(json.dumps({"text": "x" * 2000}))
    ds.data["pluginUserData"] += [{"id": "questarc:note:r:x", "data": '{"a":1}'},
                                  {"id": "questarc:note:r:y", "data": packed}]
    window = window_with(app, tmp_path, ds)
    model = window.journeys
    entries = copy.deepcopy([e for e in window.ds.data["pluginUserData"]
                             if e["id"].startswith("questarc:note:")])
    assert model.action("pauseJourney", "r", window.ds.today())
    assert model.active()["paused"]
    assert [e for e in window.ds.data["pluginUserData"]
            if e["id"].startswith("questarc:note:")] == entries
    with pytest.raises(engine.Refused):
        model.write({"note:r:z": {"a": 2}, "pause:r:2000-01-01": {"action": "pause"}})
    assert "pause:r:2000-01-01" not in model.records()
    valid(window)
    window.close()


# --- #64: stay and skip ---------------------------------------------------

def run_page(window):
    window.show_run()
    iterate()
    page = window.visible_page()
    assert type(page).__name__ == "RunPage"
    return page


def test_a_met_station_offers_continue_and_stay_as_equals(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.met(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    page = run_page(window)
    assert page.main_button.get_label() == "Continue"
    page.show_continue()
    iterate()
    cont = window.visible_page()
    assert cont.get_tag() == "journey-continue"
    # No weekly answer yet: the engine suggests staying, which is the filled button.
    assert window.journeys.active()["offer"]["suggest"] == "stay"
    assert content.t("ui.continue.suggest-new") in labels(cont)
    assert cont.main_button.get_label() == "Continue"
    assert cont.other_button.get_label() == "Stay Here a While"
    assert "suggested-action" in cont.other_button.get_css_classes()
    assert "suggested-action" not in cont.main_button.get_css_classes()
    cont.other_button.emit("clicked")
    iterate()
    assert any(k.startswith("stay:walk:water") for k in window.journeys.records())
    page = window.visible_page()
    assert type(page).__name__ == "RunPage"
    # While staying, Continue is a quiet action and the card says so.
    assert "suggested-action" not in page.main_button.get_css_classes()
    assert content.t("ui.card.staying") in labels(page)
    page.show_continue()
    iterate()
    window.visible_page().main_button.emit("clicked")  # Continue
    iterate()
    assert window.journeys.active()["position"]["stage"] == 1
    assert window.visible_page().get_tag() == "journey-setup"
    valid(window)
    window.close()


def test_i_already_do_this_passes_a_station_and_can_be_taken_back(app, tmp_path):
    ds = fresh()
    started(ds)
    window = window_with(app, tmp_path, ds)
    page = run_page(window)
    page.show_setup()
    iterate()
    setup = window.visible_page()
    assert content.t("ui.setup.skip") in labels(setup)
    skip = next(w for w in _all(setup) if "pensum-journey-skip" in w.get_css_classes())
    skip.emit("activated")
    iterate()
    run = window.journeys.active()
    assert run["stations"][0]["state"] == "skipped"
    assert run["position"]["stage"] == 1
    assert any(k.startswith("skip:r:water") for k in window.journeys.records())
    # The same page offers the next station.
    assert window.visible_page() is setup
    assert "Stretch" in " ".join(labels(setup)) or "stretch" in " ".join(labels(setup))
    window.show_run()
    iterate()
    run_page_ = window.visible_page()
    run_page_.show_stations()
    iterate()
    stations = window.visible_page()
    assert any(s.endswith("Already yours") for s in labels(stations))
    run_page_.show_station(0)
    iterate()
    station = window.visible_page()
    assert any(s.startswith("Already yours: passed on") for s in labels(station))
    assert station.main_button.get_label() == "Do This Station After All"
    station._main()
    iterate()
    run = window.journeys.active()
    assert run["position"]["stage"] == 0 and run["stations"][0]["state"] == "unbound"
    valid(window)
    window.close()


def _all(widget):
    found = [widget]
    child = widget.get_first_child()
    while child:
        found += _all(child)
        child = child.get_next_sibling()
    return found


def test_pair_it_with_becomes_part_of_the_plan_sentence(app, tmp_path):
    ds = fresh()
    started(ds)
    window = window_with(app, tmp_path, ds)
    run_page(window).show_setup()
    iterate()
    setup = window.visible_page()
    row = next(w for w in _all(setup) if "pensum-journey-pair" in w.get_css_classes())
    assert row.get_text() == ""
    row.set_text("my podcast.")
    row.emit("apply")
    iterate()
    assert window.journeys.records()["pair:r:water"] == {"text": "my podcast"}
    assert window.journeys.active()["stations"][0]["pair"] == "my podcast"
    assert any(s.endswith(", with my podcast.") for s in labels(window.visible_page()))
    row = next(w for w in _all(window.visible_page())
               if "pensum-journey-pair" in w.get_css_classes())
    row.set_text("")
    row.emit("apply")
    iterate()
    assert "pair:r:water" not in window.journeys.records()
    valid(window)
    window.close()


# --- #64: the long break --------------------------------------------------

def _come_back_window(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.come_back(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    assert window.journeys.active()["comeBack"]["smaller"] == "water"
    return window


def test_after_a_long_break_one_card_offers_three_ways(app, tmp_path):
    window = _come_back_window(app, tmp_path)
    page = run_page(window)
    words = labels(page)
    assert "Good to see you." in words
    assert "Carry On" in words and "Call It a Pause" in words and "Start Smaller" in words
    assert content.t("ui.banner.checkin") not in words
    button(page, "Call It a Pause").emit("clicked")
    iterate()
    pauses = sorted(k for k in window.journeys.records() if k.startswith("pause:walk:"))
    assert len(pauses) == 2
    assert window.journeys.active().get("comeBack") is None
    valid(window)
    window.close()


def test_carry_on_closes_the_card(app, tmp_path):
    window = _come_back_window(app, tmp_path)
    button(run_page(window), "Carry On").emit("clicked")
    iterate()
    assert any(k.startswith("carry-on:walk:") for k in window.journeys.records())
    assert window.journeys.active().get("comeBack") is None
    valid(window)
    window.close()


def test_start_smaller_walks_the_earlier_station_again(app, tmp_path):
    window = _come_back_window(app, tmp_path)
    page = run_page(window)
    button(page, "Start Smaller").emit("clicked")
    iterate()
    smaller = window.visible_page()
    assert smaller.get_tag() == "journey-smaller"
    # The earlier task still repeats: it counts again from today.
    assert content.t("ui.smaller.task-earlier") in labels(smaller)
    smaller.pause.set_active(True)
    smaller._main()
    iterate()
    found = window.journeys.records()
    assert any(k.startswith("step-back:walk:stretch-1:") for k in found)
    assert len([k for k in found if k.startswith("pause:walk:")]) == 2
    run = window.journeys.active()
    assert run["position"]["stage"] == 0 and run["stations"][0].get("stepBackDay")
    assert type(window.visible_page()).__name__ == "RunPage"
    assert any(s.startswith("You started smaller on") for s in labels(window.visible_page()))
    valid(window)
    window.close()


# --- #64: graduation --------------------------------------------------------

def home(window):
    window.show_journey()
    iterate()
    return window.visible_page()


def test_a_habit_that_runs_by_itself_is_offered_to_graduate(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    stage = demo_journey.graduate(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    page = home(window)
    assert any("seems to run by itself. You could let it graduate." in s
               for s in labels(page))
    # Not Now is a choice, written for every device.
    button(page, "Not Now").emit("clicked")
    iterate()
    assert f"graduation-later:walk:{stage}" in window.journeys.records()
    page = home(window)
    assert not any("seems to run by itself" in s for s in labels(page))
    # The shelf keeps the quiet way to it.
    page.show_shelf()
    iterate()
    shelf = window.visible_page()
    assert "Habits that stay" in labels(shelf)
    assert content.t("ui.shelf.maintained") in labels(shelf)
    button(shelf, "Let It Graduate").emit("clicked")
    iterate()
    grad = window.visible_page()
    assert content.t("ui.graduate.text") in labels(grad)
    assert not grad.bottom.get_visible()  # the choice is the yes
    button(grad, "Keep It Repeating Quietly").emit("clicked")
    iterate()
    assert [v for k, v in window.journeys.records().items()
            if k.startswith(f"graduation:walk:{stage}:")] == [{"choice": "keep"}]
    assert content.t("ui.graduated.text") in labels(grad)
    assert grad.main_button.get_label() == "Done"
    valid(window)
    window.close()


def test_a_graduated_habit_is_asked_once_and_can_be_brought_back(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    stage = demo_journey.graduated(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    due = window.journeys.view["finished"][0]["habit"]["graduated"]["checkDue"]
    page = home(window)
    assert any("graduated a while ago" in s for s in labels(page))
    button(page, "Answer").emit("clicked")
    iterate()
    still = window.visible_page()
    assert any(s.startswith("Does ") for s in labels(still))
    still.other_button.emit("clicked")  # Not Really
    iterate()
    assert window.journeys.records()[f"graduation-check:walk:{stage}:{due}"]["still"] is False
    # Not really changes nothing by itself: the page offers to bring it back.
    assert content.t("ui.still.back.said") in labels(still)
    assert still.main_button.get_label() == "Bring It Back"
    still.main_button.emit("clicked")
    iterate()
    record = next(v for k, v in window.journeys.records().items()
                  if k.startswith(f"graduation:walk:{stage}:"))
    assert record["until"] == window.journeys.view["todayStr"]
    habit = window.journeys.view["finished"][0]["habit"]
    assert habit["state"] == "maintained" and habit.get("backDay")
    shelf = window.visible_page()
    assert shelf.get_tag() == "journey-shelf"
    assert any(s.startswith("Back with you since") for s in labels(shelf))
    valid(window)
    window.close()


def test_running_by_themselves_on_the_shelf(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.graduated(ds, ds.today())
    window = window_with(app, tmp_path, ds)
    home(window).show_shelf()
    iterate()
    shelf = window.visible_page()
    assert "Running by themselves" in labels(shelf)
    assert any(s.startswith("Runs by itself since") for s in labels(shelf))
    button(shelf, "Answer One Question").emit("clicked")
    iterate()
    still = window.visible_page()
    button(still, "Not Now").emit("clicked")
    iterate()
    # Put aside on this device only: nothing written.
    assert not any(k.startswith("graduation-check:") for k in window.journeys.records())
    assert any(k.startswith("still:walk:") for k in window.settings.seen)
    window.close()


# --- #64: plan check, chains, reminders --------------------------------------

def test_the_plan_check_is_written_with_start_and_changed_from_the_menu(app, tmp_path):
    ds = fresh()
    window = window_with(app, tmp_path, ds)
    from pensum.ui.journey.start_page import StartPage
    window.show_journey()
    window.nav.push(StartPage(window, "gentle-morning"))
    iterate()
    start = window.visible_page()
    # Collapsed and empty: nothing written for it.
    start.plan_rows["obstacle"].set_text("the phone")
    start.plan_rows["plan"].set_text("If I reach for the phone, then I will put it down")
    start._main()
    iterate()
    run = window.journeys.active()
    assert run["planCheck"] == {"obstacle": "the phone",
                                "plan": "If I reach for the phone, then I will put it down"}
    page = window.visible_page()
    page.show_plan_check()
    iterate()
    check = window.visible_page()
    assert check.rows["plan"].get_text().startswith("If I reach")
    for row in check.rows.values():
        row.set_text("")
    check._main()
    iterate()
    assert "planCheck" not in window.journeys.active()
    valid(window)
    window.close()


def test_a_new_step_can_be_tied_to_a_habit_at_the_moment(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    records.write(ds, {"anchor:up": {"kind": "routine", "words": "getting up"}})
    demo_journey.finished(ds, ds.today(), anchor_id="up")
    window = window_with(app, tmp_path, ds)
    from pensum.ui.journey.start_page import StartPage
    window.show_journey()
    window.nav.push(StartPage(window, "walk-after-lunch", "up"))
    iterate()
    start = window.visible_page()
    assert start.chain.get_visible()
    assert any(s.startswith("After I plan") or s.startswith("After I ")
               for s in labels(start.chain))
    start.after = "walk"
    start._main()
    iterate()
    tied = [v for k, v in window.journeys.records().items() if k.startswith("run-anchor:")
            and v.get("after")]
    assert tied == [{"anchorId": "up", "after": "walk"}]
    assert window.journeys.active()["anchor"]["after"]["runId"] == "walk"
    valid(window)
    window.close()


def test_a_reminder_on_the_followed_task_is_recorded(app, tmp_path):
    from pensum import demo_journey
    ds = fresh()
    demo_journey.met(ds, ds.today())
    cfg = ds.data["taskRepeatCfg"]["entities"]["walk-water"]
    cfg.update(startTime="07:00", remindAt="AtStart")
    window = window_with(app, tmp_path, ds)
    assert window.journeys.active()["reminder"]["set"] is True
    assert window.journeys.records()["reminder-seen:walk:water"] == {
        "on": True, "day": window.journeys.view["todayStr"]}
    cfg = window.ds.data["taskRepeatCfg"]["entities"]["walk-water"]
    cfg.pop("remindAt")
    window.changed()
    window.journeys.refresh_now()
    assert window.journeys.records()["reminder-seen:walk:water"]["on"] is False
    valid(window)
    window.close()
