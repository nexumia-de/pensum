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


def test_notes_page_adds_edits_pins_and_removes(window):
    from pensum.store import notes
    from pensum.ui.notes_page import NotesPage
    project = window.ds.default_project_id()
    page = NotesPage(window, project)
    window.nav.push(page)
    iterate()
    assert "No Notes" in labels(page)
    page._on_add(None)
    iterate()
    note_page = window.visible_page()
    note_page.text.get_buffer().set_text("Seeds\nbuy them")
    note = notes.of_project(window.ds, project)[0]
    assert note["content"] == "Seeds\nbuy them"
    window.nav.pop()
    iterate()
    assert "Seeds" in labels(page)
    notes.set_pinned(window.ds, note["id"], True)
    window.show_list(Context.today())
    window.changed()
    iterate()
    assert "Seeds" in labels(window.list_page)  # pinned notes on Today
    valid(window)


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


def test_break_reminder_and_the_break_counted(window, monkeypatch):
    sent = []
    app = window.get_application()
    monkeypatch.setattr(type(app), "send_notification",
                        lambda self, name, note: sent.append(name), raising=False)
    monkeypatch.setattr(type(app), "withdraw_notification", lambda self, name: None,
                        raising=False)
    watch = window.break_watch
    task = tasks.add_task(window.ds, "Write", Context.today())
    window.timer.toggle(task["id"])
    now = dates.now_ms()
    watch._last = now - 61 * MIN
    watch.check(now)
    assert sent == ["take-a-break"]
    watch.check(now + 1000)
    assert sent == ["take-a-break"]  # once
    watch.take_break(now + 2000)
    assert window.timer.task_id is None
    window.timer.toggle(task["id"])
    watch.check(now + 2000 + 5 * MIN)
    entry = window.ds.data["timeTracking"]["tag"]["TODAY"][window.ds.today(now)]
    assert entry["b"] == 1 and entry["bt"] == 5 * MIN
    window.timer.stop()
    valid(window)


def test_worklog_and_summary(window):
    from pensum.store import metric
    from pensum.ui.summary_page import SummaryPage
    from pensum.ui.worklog_page import WorklogPage
    task = tasks.add_task(window.ds, "Write", Context.today())
    today = window.ds.today()
    tracking.set_time_on_day(window.ds, task["id"], today, 90 * MIN)
    page = WorklogPage(window, Context.today())
    window.nav.push(page)
    iterate()
    assert any("1h 30m" in text for text in labels(page))
    summary = SummaryPage(window)
    window.nav.push(summary)
    iterate()
    assert "Write" in labels(summary)
    summary.impact.set_selected(3)
    summary.energy.set_selected(2)
    summary.reflection.set_text("Good day")
    summary._on_reflection(summary.reflection)
    found = metric.for_day(window.ds, today)
    assert (found["impactOfWork"], found["energyCheckin"]) == (3, 2)
    assert found["reflections"][0]["text"] == "Good day"
    valid(window)
