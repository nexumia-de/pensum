"""The pages through the real widgets: lists, adding and finishing tasks,
the task page with subtasks and timer, list menus and preferences. Needs
a display (CI runs pytest under xvfb-run)."""
import os

import pytest

if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
    pytest.skip("needs a display", allow_module_level=True)

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib  # noqa: E402

from pensum import demo, settings  # noqa: E402
from pensum.store import backup, validate  # noqa: E402
from pensum.store.dataset import Context  # noqa: E402
from pensum.store.files import Files  # noqa: E402


@pytest.fixture(scope="module")
def app():
    """One application for all tests: a second one with the same id can't
    register on the session bus."""
    from pensum.main import Application
    application = Application()
    application.register(None)
    Adw.init()
    yield application


def iterate(times=20):
    ctx = GLib.MainContext.default()
    for _ in range(times):
        while ctx.pending():
            ctx.iteration(False)


def new_window(app, tmp_path, ds=None):
    from pensum.window import Window
    files = Files(tmp_path / "data")
    if ds is not None:
        files.save(ds)
    window = Window(app, files, settings.Store(tmp_path / "settings.json"))
    window.present()
    iterate()
    return window


def test_add_finish_and_open_task(app, tmp_path):
    window = new_window(app, tmp_path)
    page = window.list_page
    assert page.context == Context.today()
    page.entry.set_text("Water the plants")
    page._on_add(page.entry)
    iterate()
    assert [r.task.get("title") for r in page.rows] == ["Water the plants"]
    row = page.rows[0]
    row.check.set_active(True)
    iterate()
    assert window.ds.task(row.task_id)["isDone"]
    assert page.done_title.get_visible()

    window.show_task(row.task_id)
    iterate()
    task_page = window.nav.get_visible_page()
    task_page.sub_entry.set_text("Fetch the can")
    task_page._on_add_sub(task_page.sub_entry)
    iterate()
    assert len(window.ds.task(row.task_id)["subTaskIds"]) == 1
    task_page.estimate_row.set_text("1h 30m")
    task_page._on_estimate(task_page.estimate_row)
    window.flush()
    saved = backup.read(window.files.path)
    assert validate.problems(saved) == []
    assert row.task_id in saved["task"]["entities"]
    window.close()


def test_timer_books_time(app, tmp_path):
    window = new_window(app, tmp_path)
    from pensum.store import tasks
    task = tasks.add_task(window.ds, "Focus", Context.today())
    window.changed()
    iterate()
    window.timer.toggle(task["id"])
    assert window.tracker_bar.get_revealed()
    window.timer._since -= 120_000  # two minutes ago
    window.timer.stop()
    iterate()
    assert window.ds.task(task["id"])["timeSpent"] >= 120_000
    assert not window.tracker_bar.get_revealed()
    window.close()


def test_demo_lists_menus_and_preferences(app, tmp_path):
    window = new_window(app, tmp_path, demo.create())
    for context in [Context.today()] + [Context("project", p["id"])
                                        for p in window.ds.projects()] \
            + [Context("tag", t["id"]) for t in window.ds.tags()]:
        window.show_list(context)
        iterate()
        assert window.list_page.get_title() == window.ds.context_title(context)
    window.show_list(Context("project", "demo-garden"))
    assert len(window.list_page.rows) == 3
    window.show_list(Context("project", "missing"))
    assert window.list_page.context == Context.today()
    current = window.ds.current_task_id()
    window.show_task(current)
    iterate()
    assert window.nav.get_visible_page().task_id == current
    from pensum.preferences import PreferencesDialog
    dialog = PreferencesDialog(window)
    dialog.hour_row.set_value(4)
    assert window.ds.config["misc"]["startOfNextDayTime"] == "04:00"
    from pensum.ui.tags_dialog import TagsDialog
    TagsDialog(window, current).present(window)
    iterate()
    window.close()


def test_reorder_menu_and_archived_projects(app, tmp_path):
    window = new_window(app, tmp_path, demo.create())
    window.show_list(Context("project", "demo-garden"))
    iterate()
    first, second = (r.task_id for r in window.list_page.rows[:2])
    window.list_page.rows[1].activate_action("row.top", None)
    iterate()
    assert [r.task_id for r in window.list_page.rows[:2]] == [second, first]
    window.list_page.activate_action("list.archive", None)
    iterate()
    assert window.ds.project_entities["demo-garden"]["isArchived"]
    assert "demo-garden" not in [p["id"] for p in window.ds.projects()]
    window.show_archived()
    iterate()
    archived = window.nav.get_visible_page()
    assert archived.stack.get_visible_child_name() == "list"
    archived._on_unarchive(None, "demo-garden")
    iterate()
    assert not window.ds.project_entities["demo-garden"]["isArchived"]
    window.close()


def test_overdue_section(app, tmp_path):
    from pensum.store import dates, tasks
    window = new_window(app, tmp_path)
    task = tasks.add_task(window.ds, "Late", Context.today())
    tasks.schedule_day(window.ds, task["id"], dates.shift_day(window.ds.today(), -3))
    window.changed()
    iterate()
    page = window.list_page
    assert page.overdue_header.get_visible()
    page._on_move_overdue()
    iterate()
    assert not page.overdue_header.get_visible()
    assert [r.task_id for r in page.rows] == [task["id"]]
    window.close()


def test_time_dialog(app, tmp_path):
    from pensum.store import tasks
    from pensum.ui.time_dialog import TimeDialog
    window = new_window(app, tmp_path)
    task = tasks.add_task(window.ds, "T", Context.today())
    dialog = TimeDialog(window, task["id"])
    dialog.present(window)
    iterate()
    row = Adw.EntryRow(text="1h 5m")
    dialog._on_apply(row, window.ds.today())
    assert window.ds.task(task["id"])["timeSpent"] == 3_900_000
    window.close()


def test_finish_day(app, tmp_path):
    window = new_window(app, tmp_path, demo.create())
    page = window.list_page
    assert page.done_header.get_visible()
    page._on_finish()
    iterate()
    assert not page.done_header.get_visible()
    assert validate.problems(window.ds.data) == []
    window.close()
