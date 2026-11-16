"""The Valley as the home of the journeys (QuestArc 4.2, pensum#68): the
places from the engine's `valley` view, their layout from the engine,
the growing card, and a journey from before anchors asking once. Needs a
display and QuestArc's engine."""
import pytest

from test_ui import _widgets, iterate, needs_engine, new_window, settle, visible  # noqa: F401

from pensum import demo, demo_valley  # noqa: E402
from pensum.game import content, engine, records  # noqa: E402
from pensum.store import backup, validate  # noqa: E402
from pensum.ui.journey.valley import ValleyScene  # noqa: E402


def _is_run(page):
    from pensum.ui.journey.run_page import RunPage
    return isinstance(page, RunPage)


def _scene(window):
    return next(w for w in _widgets(window.journey_page) if isinstance(w, ValleyScene))


def _open_home(app, tmp_path, monkeypatch, scenario):
    monkeypatch.setenv("PENSUM_DEMO_VALLEY", scenario)
    window = new_window(app, tmp_path, demo.create())
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    return window


@needs_engine
@pytest.mark.parametrize("scenario, places", [("1", 1), ("3", 3), ("6", 6), ("6-stacked", 6)])
def test_home_draws_a_place_for_every_moment(app, tmp_path, monkeypatch, scenario, places):
    window = _open_home(app, tmp_path, monkeypatch, scenario)
    scene = _scene(window)
    assert len(window.journeys.view["valley"]) == places == len(scene.layout["places"])
    assert len(scene.buttons) == places
    # The layout is the engine's, not drawn by hand: the same request gives the same numbers.
    again = engine.valley_layout([p["side"] for p in window.journeys.view["valley"]],
                                 [len(p["things"]) for p in window.journeys.view["valley"]],
                                 360, window.journey_page._scene_units(False))
    assert again == scene.layout
    # Each place is one button of at least 44 px, its row from edge to edge.
    for piece in scene.layout["places"]:
        assert piece["piece"]["height"] >= 44 and piece["piece"]["width"] == 360
    # Screen readers get the place in words, in the order of the day.
    last = "After sitting down at my desk" if scenario == "1" else "After my evening coffee"
    assert scene.labels[-1].startswith(last)
    window.close()


@needs_engine
def test_home_names_the_places_and_the_lantern_in_words(app, tmp_path, monkeypatch):
    window = _open_home(app, tmp_path, monkeypatch, "3")
    scene = _scene(window)
    assert [t.split(":")[0] for t in scene.labels] == [
        "After getting up", "After sitting down at my desk", "After my evening coffee"]
    # The lit lantern is the only sign: where a routine runs by itself.
    assert "The lantern is lit: the routine runs by itself." in scene.labels[0]
    assert "lantern" not in scene.labels[1] and "lantern" not in scene.labels[2]
    assert "Growing here." in scene.labels[1] and "Growing here." not in scene.labels[0]
    assert "version 5 of 5" in scene.labels[0]
    window.close()


@needs_engine
def test_the_growing_card_and_its_place_open_the_journey(app, tmp_path, monkeypatch):
    window = _open_home(app, tmp_path, monkeypatch, "3")
    page = window.journey_page
    assert page.card is not None
    page.card.emit("clicked")
    iterate()
    assert _is_run(visible(window))
    window.nav.pop()
    iterate()
    _scene(window).buttons[1].emit("clicked")  # the growing place
    iterate()
    assert _is_run(visible(window))
    window.close()


@needs_engine
def test_nothing_in_the_valley_marks_what_comes_next(app, tmp_path, monkeypatch):
    """Flowers are the only marker and only the lantern is a sign: the
    scene draws no marker, and no label says what is still to come."""
    window = _open_home(app, tmp_path, monkeypatch, "6")
    for label in _scene(window).labels:
        assert "next" not in label.lower() and "waiting" not in label.lower()
    window.close()


@needs_engine
def test_no_moment_yet_is_plain_land(app, tmp_path):
    """Records without any place: the path, a short scene, the words, and
    A New Moment as the main action. Nothing marks a free place."""
    ds = demo.create()
    records.write(ds, {"anchor:lonely": {"kind": "time", "time": "21:30"}})
    window = new_window(app, tmp_path, ds)
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    assert "After sitting down at my desk" in " ".join(_scene(window).labels)
    assert window.journey_page.main_button.get_label() == "A New Moment"
    window.close()


@needs_engine
def test_a_journey_from_before_anchors_asks_once(app, tmp_path):
    """Confirming the suggested words writes the moment and ties every run
    of the journey to it; the data stays valid."""
    from pensum.ui.journey.confirm_card import confirm_cards
    window = new_window(app, tmp_path)
    journey = content.journey("gentle-morning")
    records.write(window.ds, engine.action("startJourney", {
        "runId": "old", "journey": journey, "startDay": window.ds.today()}))
    window.changed()
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    assert [a for a in window.journeys.view["anchors"] if a.get("id") is None]
    cards = confirm_cards(window.journey_page)
    assert len(cards) == 1
    yes = next(w for w in _widgets(cards[0]) if getattr(w, "get_label", None)
               and w.get_label() == "Yes, That Is It")
    yes.emit("clicked")
    iterate()
    stored = records.load(window.ds)
    anchors = {k: v for k, v in stored.items() if k.startswith("anchor:")}
    assert list(anchors.values()) == [{"kind": "routine", "words": "getting up"}]
    assert stored["run-anchor:old"]["anchorId"] == next(iter(anchors))[len("anchor:"):]
    assert not confirm_cards(window.journey_page)  # nothing is asked again
    assert [p["name"] for p in window.journeys.view["valley"]] == ["getting up"]
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()


def test_demo_scenarios_are_known():
    assert demo_valley.scenario() == "3"
