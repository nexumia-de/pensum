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


# --- the place and "Change this moment" (QuestArc screens 0b and 0a) ---------

def _push_place(window, index):
    _scene(window).buttons[index].emit("clicked")
    iterate()
    return visible(window)


def _texts(widget):
    found = []
    for w in _widgets(widget):
        for getter in ("get_label", "get_title", "get_subtitle"):
            text = getattr(w, getter, lambda: None)()
            if isinstance(text, str) and text:
                found.append(text)
    return found


@needs_engine
def test_a_place_at_rest_shows_its_things_versions_and_routine(app, tmp_path, monkeypatch):
    window = _open_home(app, tmp_path, monkeypatch, "6-stacked")
    # "dinner" (index 3) holds three things; "getting up" (index 0) runs by itself.
    page = _push_place(window, 3)
    assert type(page).__name__ == "PlacePage" and page.get_title() == "After dinner"
    texts = _texts(page)
    assert texts.count("Your routine here") == 1
    # Where the place holds several things each row is headed by its journey's title.
    assert sum(1 for t in texts if t in ("Evening wind-down", "Tidy a little",
                                         "First Things First")) >= 2
    assert "Extend This Moment" in texts
    from pensum.ui.journey.place_page import PlacePage
    window.nav.push(PlacePage(window, "getting-up"))
    iterate()
    texts = _texts(visible(window))
    assert "Runs by itself" in texts
    assert "Nothing is ticked or counted for it any more." in texts
    assert not any("Still followed" in t for t in texts)
    window.close()


@needs_engine
def test_a_place_where_nothing_stands_yet(app, tmp_path):
    ds = demo.create()
    records.write(ds, {"anchor:free": {"kind": "time", "time": "21:30"}})
    window = new_window(app, tmp_path, ds)
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    labels = _scene(window).labels
    free = next(i for i, text in enumerate(labels) if text.startswith("At 21:30"))
    assert labels[free] == "At 21:30: nothing stands here yet."
    page = _push_place(window, free)
    assert "Nothing stands here yet." in _texts(page)
    window.close()


@needs_engine
def test_change_this_moment_writes_place_records_and_stays_valid(app, tmp_path, monkeypatch):
    """Earlier, side, colour and the suggestion write `place:` records
    through the engine's actions; the words and the name write the anchor;
    the data stays valid."""
    from pensum.ui.journey.change_moment_page import ChangeMomentPage
    window = _open_home(app, tmp_path, monkeypatch, "3")
    page = _push_place(window, 2)  # the evening moment: a journey waits there
    pencil = next(w for w in _widgets(page) if "pensum-place-edit" in w.get_css_classes())
    assert min(pencil.get_size_request()) >= 44
    pencil.emit("clicked")
    iterate()
    change = visible(window)
    assert isinstance(change, ChangeMomentPage)
    names = [p["anchorId"] for p in window.journeys.view["valley"]]
    assert names == ["getting-up", "desk", "evening"]
    before_side = window.journeys.view["valley"][2]["side"]

    # earlier: swaps with its neighbour and writes every place's position
    rows = {w.get_title(): w for w in _widgets(change) if hasattr(w, "get_title")}
    assert not rows["Move Later"].get_sensitive()  # at the end of the path
    rows["Move Earlier"].emit("activated")
    iterate()
    assert [p["anchorId"] for p in window.journeys.view["valley"]] == [
        "getting-up", "evening", "desk"]
    stored = records.load(window.ds)
    assert [stored[f"place:{i}"]["position"] for i in ("getting-up", "evening", "desk")] \
        == [0, 1, 2]

    # side and colour: written at once, only what was picked
    other = "left" if window.journeys.view["valley"][1]["side"] == "right" else "right"
    rows = {w.get_title(): w for w in _widgets(change) if hasattr(w, "get_title")}
    rows[other.capitalize()].activate()
    iterate()
    rows = {w.get_title(): w for w in _widgets(change) if hasattr(w, "get_title")}
    rows["Rose"].activate()
    iterate()
    place = window.journeys.view["valley"][1]
    assert (place["side"], place["hue"]) == (other, "rose")
    assert records.load(window.ds)["place:evening"] == {"position": 1, "side": other,
                                                         "hue": "rose"}
    assert before_side in ("left", "right")

    # the suggestion withdraws all three
    rows = {w.get_title(): w for w in _widgets(change) if hasattr(w, "get_title")}
    rows["Use the suggestion"].emit("activated")
    iterate()
    assert "place:evening" not in records.load(window.ds)
    evening = next(p for p in window.journeys.view["valley"] if p["anchorId"] == "evening")
    assert evening["chosen"] == {}

    # the words and the name
    # no Save button: the words are written when editing ends (Enter, focus out, back)
    assert not change.bottom.get_visible()
    change.rows.routine.set_text("my second coffee")
    change.name_row.set_text("Evening")
    assert records.load(window.ds)["anchor:evening"] == {"kind": "routine",
                                                         "words": "my evening coffee"}
    change.name_row.emit("entry-activated")
    iterate()
    assert records.load(window.ds)["anchor:evening"] == {
        "kind": "routine", "words": "my second coffee", "name": "Evening"}
    assert any(p["name"] == "Evening" for p in window.journeys.view["valley"])
    # emptying the words writes nothing and puts back what stands
    change.rows.routine.set_text("")
    change._commit()
    iterate()
    assert records.load(window.ds)["anchor:evening"]["words"] == "my second coffee"
    assert change.rows.routine.get_text() == "my second coffee"
    # leaving the page writes what was typed last
    change.rows.routine.set_text("tea")
    change.emit("hiding")
    iterate()
    assert records.load(window.ds)["anchor:evening"]["words"] == "tea"
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()


@needs_engine
def test_remove_a_moment_only_where_nothing_stands(app, tmp_path):
    from pensum.ui.journey.change_moment_page import ChangeMomentPage
    ds = demo.create()
    records.write(ds, {"anchor:free": {"kind": "routine", "words": "tea"},
                       "place:free": {"side": "left"}})
    window = new_window(app, tmp_path, ds)
    window.journeys.refresh_now()
    window.nav.push(ChangeMomentPage(window, "free"))
    iterate()
    page = visible(window)
    titles = _texts(page)
    assert "Remove This Moment" in titles and "Nothing stands here yet, so nothing is lost." in titles
    row = next(w for w in _widgets(page) if getattr(w, "get_title", lambda: "")() ==
               "Remove This Moment")
    row.emit("activated")
    iterate()
    stored = records.load(window.ds)
    assert "anchor:free" not in stored and "place:free" not in stored
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    # where a journey stands there is no such row
    window.nav.push(ChangeMomentPage(window, "desk"))
    iterate()
    assert "Remove This Moment" not in _texts(visible(window))
    window.close()


@needs_engine
def test_extend_this_moment_starts_from_the_moment(app, tmp_path, monkeypatch):
    from pensum.ui.journey.choose_page import PreviewPage
    window = _open_home(app, tmp_path, monkeypatch, "3")
    window.nav.push(PreviewPage(window, "tidy-a-little", "evening"))
    iterate()
    visible(window)._main()
    iterate()
    start = visible(window)
    assert start.anchor_id == "evening"
    start._main()
    iterate()
    run = next(r for r in [window.journeys.active()] + window.journeys.view["paused"]
               if r and r["journeyId"] == "tidy-a-little")
    assert records.load(window.ds)[f"run-anchor:{run['runId']}"] == {"anchorId": "evening"}
    # the place now holds a second thing of the same kind
    evening = next(p for p in window.journeys.view["valley"] if p["anchorId"] == "evening")
    assert len(evening["things"]) == 2
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()
