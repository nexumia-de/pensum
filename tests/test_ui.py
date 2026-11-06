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


def test_backlog_section(app, tmp_path):
    from pensum.store import tasks
    window = new_window(app, tmp_path, demo.create())
    garden = Context("project", "demo-garden")
    first = window.ds.top_level_ids(garden)[0]
    tasks.set_backlog(window.ds, first, True)
    window.show_list(garden)
    iterate()
    page = window.list_page
    assert page.backlog.get_visible()
    backlog_row = [r for r in page.rows if r.task_id == first][0]
    backlog_row.activate_action("row.backlog", None)
    iterate()
    assert not page.backlog.get_visible()
    window.close()


def test_search_page(app, tmp_path):
    window = new_window(app, tmp_path, demo.create())
    window.show_search()
    iterate()
    page = window.nav.get_visible_page()
    page.entry.set_text("plumber")
    page.refresh()
    row = page.results.get_row_at_index(0)
    assert row is not None and row.task_id
    page._on_activated(page.results, row)
    iterate()
    assert window.nav.get_visible_page().task_id == row.task_id
    window.close()


def _navigation_views(widget):
    found = [widget] if isinstance(widget, Adw.NavigationView) else []
    child = widget.get_first_child()
    while child is not None:
        found += _navigation_views(child)
        child = child.get_next_sibling()
    return found


def test_one_navigation_view_and_swipe_back_stack(app, tmp_path):
    """A nested AdwNavigationView broke the back swipe on the phone; the
    window has one, the lists are its first page on narrow windows and
    every page above can pop (phosh-toolkit adaptive rule 9)."""
    window = new_window(app, tmp_path, demo.create())
    window._set_wide(False)
    iterate()
    assert _navigation_views(window) == [window.nav]
    stack = window._pages()
    assert stack[:2] == [window.lists_page, window.list_page]
    window.show_task(window.ds.current_task_id())
    iterate()
    assert all(p.get_can_pop() for p in window._pages()[1:])
    window.nav.pop()
    window.nav.pop()
    iterate()
    assert window.nav.get_visible_page() is window.lists_page
    window._set_wide(True)
    iterate()
    assert window.lists_page not in window._pages()
    assert window.split.get_sidebar() is window.sidebar
    assert _navigation_views(window) == [window.nav]
    window._set_wide(False)
    iterate()
    assert window._pages()[0] is window.lists_page
    window.close()


def test_delete_with_undo(app, tmp_path):
    window = new_window(app, tmp_path, demo.create())
    task_id = window.ds.top_level_ids(Context("project", "demo-garden"))[0]
    window.show_task(task_id)
    iterate()
    window.nav.get_visible_page()._on_delete()
    iterate()
    assert task_id not in window.ds.tasks
    window.show_list(Context("project", "demo-garden"))
    window.list_page._on_delete()
    assert "demo-garden" not in window.ds.project_entities
    from pensum.store import contexts
    toast = window.undoable("deleted", lambda: contexts.delete_project(
        window.ds, "demo-website"))
    assert "demo-website" not in window.ds.project_entities
    toast.emit("button-clicked")
    iterate()
    assert "demo-website" in window.ds.project_entities
    assert validate.problems(window.ds.data) == []
    window.close()


def test_make_a_task_repeat_and_stop_with_undo(app, tmp_path):
    window = new_window(app, tmp_path)
    page = window.list_page
    page.entry.set_text("Walk")
    page._on_add(page.entry)
    iterate()
    task_id = page.rows[0].task_id
    window.show_task(task_id)
    iterate()
    task_page = window.nav.get_visible_page()
    assert task_page.repeat_row.get_subtitle() == "Never"
    task_page._on_repeat()
    iterate()
    repeat = window.nav.get_visible_page()
    assert repeat.get_tag() == f"repeat-{task_id}"
    repeat.schedule_row.set_selected(2)  # Monday to Friday
    iterate()
    cfg_id = window.ds.task(task_id)["repeatCfgId"]
    cfg = window.ds.data["taskRepeatCfg"]["entities"][cfg_id]
    assert cfg["quickSetting"] == "MONDAY_TO_FRIDAY"
    assert repeat.pause_row.get_visible()
    repeat._on_stop()
    iterate()
    assert "repeatCfgId" not in window.ds.task(task_id)
    assert task_page.repeat_row.get_subtitle() == "Never"
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()
