"""The pages of M3 on real widgets: notes (#24), focus (#19), the break
reminder (#20), the worklog (#22), the daily summary (#23), attachments
(#25), the planner (#26) and menu folders (#27). Every change keeps
`validate.problems()` empty."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from journey_support import fresh, iterate, labels, valid, window_with  # noqa: E402
from pensum.store import dates, tasks, tracking  # noqa: E402
from pensum.store.dataset import Context  # noqa: E402

MIN = 60 * 1000


@pytest.fixture
def window(app, tmp_path):
    w = window_with(app, tmp_path, fresh())
    yield w
    w.close()
    iterate()


def test_focus_countdown_tracks_logs_and_stops(window):
    from pensum.store import focus, metric
    from pensum.ui.focus_page import FocusPage
    task = tasks.add_task(window.ds, "Write", Context.today())
    page = FocusPage(window, task["id"])
    window.nav.push(page)
    page._mode_buttons["Countdown"].set_active(True)
    page.minutes.set_value(1)
    page._on_button(None)
    assert window.timer.task_id == task["id"]
    page.session.started -= 2 * MIN  # the minute is over
    page.tick()
    assert page.session is None
    assert window.timer.task_id is None
    assert metric.for_day(window.ds, window.ds.today())["focusSessions"] == [MIN]
    valid(window)


def test_pomodoro_break_pauses_tracking(window):
    from pensum.store import focus, metric
    from pensum.ui.focus_page import FocusPage
    task = tasks.add_task(window.ds, "Write", Context.today())
    page = FocusPage(window, task["id"])
    window.nav.push(page)
    page._on_button(None)
    page.session.started -= focus.DEFAULTS["duration"]
    page.tick()
    assert page.session.phase == "break" and window.timer.task_id is None
    page._on_button(None)  # skip the break
    assert page.session.phase == "work" and window.timer.task_id == task["id"]
    page._on_button(None)  # end the session early
    window.timer.stop()
    valid(window)
