"""QuestArc's words about the reminder of a followed task in Day Planner
(QuestArc behaviour, flow H; pensum#13): the sentence at set-up, the
suggestion in a station's first weeks and that it goes once the task's
repeat has a reminder. Needs a display, gjs and QuestArc's engine."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from pensum.game import content, stages  # noqa: E402
from pensum.store import reminders  # noqa: E402
from journey_support import (button, fresh, iterate, labels, needs_engine,  # noqa: E402
                             started, valid, window_with)

pytestmark = needs_engine


def run_page(window):
    window.show_run()
    iterate()
    return window.visible_page()


def test_reminder_sentence_suggestion_and_that_it_goes(app, tmp_path):
    ds = fresh()
    started(ds)
    window = window_with(app, tmp_path, ds)
    page = run_page(window)
    page._main_action()  # Set up the task
    iterate()
    setup = window.visible_page()
    assert content.t("ui.setup.reminder") in labels(setup)
    setup._main()  # Create the task
    iterate(40)
    window.journeys.refresh_now()
    page = run_page(window)
    suggestion = content.t("ui.banner.reminder")
    # One thing at a time: the nugget first, then the reminder.
    assert suggestion not in labels(page)
    button(page, content.t("ui.action.got-it")).emit("clicked")
    iterate()
    assert suggestion in labels(page)
    # Open the task leads to the task, where its Repeat page sets it.
    button(page, content.t("ui.setup.open")).emit("clicked")
    iterate()
    assert type(window.visible_page()).__name__ == "TaskPage"
    cfg = stages.bound_rule(window.ds, window.journeys.view)
    reminders.set_rule_time(window.ds, cfg["id"], "07:00", "AtStart", window.ds.today())
    window.changed()
    window.journeys.refresh_now()
    assert window.journeys.active()["reminder"] == {"set": True, "time": "07:00"}
    # What Day Planner saw is recorded for graduation (game rules §9).
    assert window.journeys.records()["reminder-seen:r:water"]["on"] is True
    page = run_page(window)
    assert suggestion not in labels(page)
    valid(window)
    window.close()


def test_not_now_puts_the_suggestion_away(app, tmp_path):
    ds = fresh()
    started(ds)
    window = window_with(app, tmp_path, ds)
    page = run_page(window)
    page._main_action()
    iterate()
    window.visible_page()._main()
    iterate(40)
    window.journeys.refresh_now()
    window.settings.seen.append("nugget:r:water")
    page = run_page(window)
    suggestion = content.t("ui.banner.reminder")
    assert suggestion in labels(page)
    button(page, content.t("ui.action.not-now")).emit("clicked")
    iterate()
    assert suggestion not in labels(window.visible_page())
    assert "reminder:r:water" in window.settings.seen
    window.close()
