"""Reminders as notifications (#13): what comes due is shown once, Done
and Snooze change the dataset the way the store does, with a window open
and on the file while none is, and the task and repeat pages set them.
Needs a display."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

from pensum import settings  # noqa: E402
from pensum.store import dates, reminders, tasks, validate  # noqa: E402
from pensum.store.dataset import Context  # noqa: E402
from pensum.store.files import Files  # noqa: E402
from pensum.store.repeat import rules  # noqa: E402

from test_ui import iterate, new_window, visible  # noqa: E402


@pytest.fixture
def watch(app, tmp_path, monkeypatch):
    """The application's watcher on its own files and settings, with the
    notifications caught instead of sent."""
    sent, withdrawn = [], []
    monkeypatch.setattr(app, "files", Files(tmp_path / "app-data"))
    monkeypatch.setattr(app, "settings_store", settings.Store(tmp_path / "app-settings.json"))
    monkeypatch.setattr(type(app), "send_notification",
                        lambda self, name, note: sent.append(name), raising=False)
    monkeypatch.setattr(type(app), "withdraw_notification",
                        lambda self, name: withdrawn.append(name), raising=False)
    held = []
    monkeypatch.setattr(type(app), "hold", lambda self: held.append(1), raising=False)
    monkeypatch.setattr(type(app), "release", lambda self: held.pop(), raising=False)
    app.reminders._shown.clear()
    app.reminders._held = False
    app.reminders._day = None
    app.reminders.sent, app.reminders.withdrawn, app.reminders.held = sent, withdrawn, held
    yield app.reminders
    app.reminders._hold(False)
    app.reminders.check()


def due_task(ds, minutes_ago=1):
    """A task planned a minute ago with a reminder at that time."""
    now = dates.now_ms()
    task = tasks.add_task(ds, "Call the plumber", Context.today())
    task["dueWithTime"] = now - minutes_ago * 60_000
    task.pop("dueDay", None)
    task["remindAt"] = task["dueWithTime"]
    return task["id"]


def test_a_due_reminder_is_shown_once_and_done_or_snoozed(app, tmp_path, watch):
    window = new_window(app, tmp_path)
    first, second = due_task(window.ds), due_task(window.ds)
    window.changed()
    assert sorted(watch.sent) == sorted([f"reminder-{first}", f"reminder-{second}"])
    window.changed()
    assert len(watch.sent) == 2  # not again while it waits
    app.activate_action("reminder-done", __import__("gi").repository.GLib.Variant("s", first))
    iterate()
    assert window.ds.tasks[first]["isDone"] and f"reminder-{first}" in watch.withdrawn
    watch.snooze(second)
    task = window.ds.tasks[second]
    assert task["remindAt"] > dates.now_ms() and reminders.due(window.ds) == []
    assert watch.held == [1]  # a reminder waits: stay alive without a window
    assert validate.problems(window.ds.data) == []
    # Opening the notification puts the reminder away and shows the task.
    third = due_task(window.ds)
    window.changed()
    watch.open(third)
    iterate()
    assert "remindAt" not in window.ds.tasks[third]
    assert type(visible(window)).__name__ == "TaskPage"
    window.close()


def test_reminders_come_without_a_window(app, tmp_path, watch):
    """Closed: the watcher reads and writes the file, creates the repeat
    instance of the day and holds the application while a rule reminds."""
    ds = app.files.load()
    task = tasks.add_task(ds, "Water the plants", Context.today())
    cfg = rules.make_recurring(ds, task["id"], rules.schedule_fields("DAILY", ds.today()))
    reminders.set_rule_time(ds, cfg["id"], "00:00", "AtStart", ds.today())
    tasks.set_done(ds, task["id"], True)
    # Tomorrow's instance does not exist yet: the watcher's day start makes
    # today's when the rule last created one yesterday.
    cfg["lastTaskCreationDay"] = dates.shift_day(ds.today(), -1)
    del ds.tasks[task["id"]]
    ds.data["task"]["ids"].remove(task["id"])
    for ids in (ds.data["tag"]["entities"]["TODAY"]["taskIds"],
                ds.project_entities[ds.default_project_id()]["taskIds"]):
        if task["id"] in ids:
            ids.remove(task["id"])
    app.files.save(ds)
    assert validate.problems(ds.data) == []
    watch.check()
    saved = app.files.load()
    made = [t for t in saved.tasks.values() if t.get("repeatCfgId") == cfg["id"]]
    assert len(made) == 1 and reminders.option_of(made[0]) == "AtStart"
    assert watch.sent == [f"reminder-{made[0]['id']}"]
    assert watch.held == [1]
    watch.done(made[0]["id"])
    saved = app.files.load()
    assert saved.tasks[made[0]["id"]]["isDone"]
    assert watch.held == [1]  # the rule will remind again tomorrow
    assert validate.problems(saved.data) == []
    # Switched off in the preferences: nothing keeps the application.
    store = app.settings_store
    values = store.load()
    values.remind_when_closed = False
    store.save(values)
    watch.check()
    assert watch.held == []


def test_task_and_repeat_pages_set_reminders(app, tmp_path, watch):
    window = new_window(app, tmp_path)
    task = tasks.add_task(window.ds, "Call the plumber", Context.today())
    window.changed()
    window.show_task(task["id"])
    iterate()
    page = visible(window)
    assert not page.remind_row.get_sensitive()
    page.set_time(23, 59)
    iterate()
    assert page.remind_row.get_sensitive()
    page.remind_row.set_selected(2)  # 5 minutes before
    iterate()
    live = window.ds.tasks[task["id"]]
    assert live["remindAt"] == live["dueWithTime"] - 5 * 60_000
    page.remind_row.set_selected(0)
    iterate()
    assert "remindAt" not in live
    # The repeat page: a time and a reminder for every new task of the rule.
    page._on_repeat()
    iterate()
    repeat = visible(window)
    repeat.schedule_row.set_selected(1)
    iterate(40)
    cfg = rules.rule_of(window.ds, window.ds.tasks[task["id"]])
    assert cfg and not repeat.remind_row.get_sensitive()
    repeat.time_row.set_text("21.30")
    repeat._on_time(repeat.time_row)
    iterate(40)
    repeat.remind_row.set_selected(1)  # at the time
    iterate(40)
    assert reminders.rule_time(cfg) == ("21:30", "AtStart")
    assert reminders.option_of(window.ds.tasks[task["id"]]) == "AtStart"
    assert validate.problems(window.ds.data) == []
    window.close()
