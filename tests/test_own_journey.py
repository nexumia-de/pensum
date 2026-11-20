"""The user's own habits as journeys (#80): the quick form, keeping the
journey QuestArc's engine writes, starting it, and a journey file in and
out. Needs a display and the engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from pensum.game import content, own  # noqa: E402
from journey_support import fresh, iterate, labels, needs_engine, valid, window_with  # noqa: E402

pytestmark = needs_engine

# The quick form and journey files are on QuestArc's default branch
# (quest-arc#89, #40) but in no release yet; the pinned 4.3.1 answers
# "unknown request". These tests run once a release with them is pinned.
needs_quick = pytest.mark.skipif(
    not own.available(),
    reason="the pinned QuestArc engine has no quick form yet (docs/owner-checks.md)")


def test_without_the_quick_form_the_choose_page_offers_none(app, tmp_path):
    if own.available():
        pytest.skip("this engine has the quick form")
    from pensum.ui.journey.choose_page import ChoosePage
    window = window_with(app, tmp_path, fresh())
    window.show_journey()
    window.nav.push(ChoosePage(window))
    iterate()
    shown = labels(window.visible_page())
    assert "Your Own Habit" not in shown
    assert "Import a Journey File" not in shown
    window.close()


def quick_page(window):
    from pensum.ui.journey.quick_page import QuickPage
    window.show_journey()
    window.nav.push(QuickPage(window))
    iterate()
    return window.visible_page()


def fill(page, action="read", anchor="brushing my teeth", name="Reading at night"):
    page.action.set_text(action)
    page.anchor.set_text(anchor)
    page.name.set_text(name)
    page.measure.set_selected(own.MEASURES.index("pages"))
    page.first.set_value(1)
    page.last.set_value(20)
    iterate()


def kept(window):
    return {k: v for k, v in window.journeys.records().items() if k.startswith(own.KEY)}


@needs_quick
def test_the_form_makes_a_journey_that_starts_and_keeps_the_dataset_valid(app, tmp_path):
    window = window_with(app, tmp_path, fresh())
    page = quick_page(window)
    assert window.get_focus() is None or window.get_focus().get_ancestor(type(page.action)) is None
    page._main()  # nothing filled in: a toast, no page
    iterate()
    assert window.visible_page() is page
    fill(page)
    assert page.steps.get_text() == "1, 2, 4, 10, 20"
    page.steps.set_text("1, 5, 10, 20")
    page._main()
    iterate()
    preview = window.visible_page()
    text = labels(preview)
    assert "After brushing my teeth, I will read 1 page." in text
    assert "After brushing my teeth, I will read 20 pages." in text
    assert not kept(window)
    preview._main()
    iterate()
    journey = kept(window)["journey:own-reading-at-night"]
    assert [s["id"] for s in journey["stages"]] == ["step-1", "step-2", "step-3", "step-4"]
    valid(window)
    start = window.visible_page()
    assert start.get_tag() == "journey-start-own-reading-at-night"
    assert start.rows.routine.get_text() == "brushing my teeth"
    start._main()
    iterate()
    active = window.journeys.active()
    assert active["journeyId"] == "own-reading-at-night"
    assert content.t(journey["title"]) == "Reading at night"
    assert not window.journeys.view["problems"]
    valid(window)
    window.close()


@needs_quick
def test_a_first_step_that_is_not_tiny_gets_a_kind_hint(app, tmp_path):
    window = window_with(app, tmp_path, fresh())
    page = quick_page(window)
    fill(page)
    page.steps.set_text("10, 20")
    page._main()
    iterate()
    assert content.t("ui.quick.hint.smaller") in labels(window.visible_page())
    window.close()


@needs_quick
def test_german_answers_give_german_plan_sentences(app, tmp_path, monkeypatch):
    monkeypatch.setenv("LANG", "de_DE.UTF-8")
    made = own.quick({"name": "Abends lesen", "action": "lesen", "anchor": "dem Zähneputzen",
                      "measure": "minutes", "steps": [2, 5], "schedule": {"type": "daily"}})
    assert own.plan_sentences(made["journey"]) == [
        "Nach dem Zähneputzen will ich 2 Minuten lesen.",
        "Nach dem Zähneputzen will ich 5 Minuten lesen."]
    assert not own.errors(made["problems"])


@needs_quick
def test_a_journey_file_goes_out_and_comes_back_and_stays_while_walked(app, tmp_path):
    from pensum.ui.journey import own_file
    from pensum.ui.journey.choose_page import PreviewPage
    from pensum.ui.journey.start_page import StartPage
    window = window_with(app, tmp_path, fresh())
    made = own.quick({"name": "Water first", "action": "drink a glass of water",
                      "anchor": "getting up", "measure": "same",
                      "schedule": {"type": "daily"}})["journey"]
    path = tmp_path / "water.json"
    assert own_file.write(window, str(path), made)
    (tmp_path / "broken.json").write_text("[1, 2", encoding="utf-8")
    assert not own_file.read(window, str(tmp_path / "broken.json"))
    built_in = dict(made, id=content.builtin()[0]["id"])
    (tmp_path / "taken.json").write_text(own.file_text(built_in), encoding="utf-8")
    assert not own_file.read(window, str(tmp_path / "taken.json"))
    assert not kept(window)
    assert own_file.read(window, str(path))
    assert kept(window) == {"journey:own-water-first": made}
    valid(window)

    window.show_journey()
    window.nav.push(PreviewPage(window, made["id"]))
    iterate()
    preview = window.visible_page()
    preview._remove(made)  # not walked: removed
    iterate()
    assert not kept(window)
    assert own_file.read(window, str(path))
    window.nav.push(StartPage(window, made["id"]))
    iterate()
    window.visible_page()._main()
    iterate()
    assert window.journeys.active()["journeyId"] == made["id"]
    window.nav.push(PreviewPage(window, made["id"]))
    iterate()
    window.visible_page()._remove(made)  # walked: it stays
    iterate()
    assert kept(window)
    valid(window)
    window.close()
