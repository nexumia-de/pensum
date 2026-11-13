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
from gi.repository import Adw, GLib, Gtk  # noqa: E402

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


def _widgets(widget):
    """A widget and everything below it."""
    found = [widget]
    child = widget.get_first_child()
    while child:
        found += _widgets(child)
        child = child.get_next_sibling()
    return found


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


def test_ephyra_layout_and_swipe_back_stack(app, tmp_path):
    """Ephyra's layout (phosh-toolkit adaptive rule 9): one navigation view
    whose first page holds a split view with the lists as sidebar and the
    list as content. Collapsed, the list sits above the lists, so a swipe
    goes back to them; pushed pages can pop."""
    window = new_window(app, tmp_path, demo.create())
    window.split.set_collapsed(True)
    iterate()
    assert window._navigation_root() is window.main_page
    assert window.split.get_sidebar() is window.lists_page
    window.show_list(Context("project", "demo-garden"))
    iterate()
    assert window.split.get_show_content()
    assert window.visible_page() is window.list_page
    assert window.list_page.get_can_pop()
    window.show_task(window.ds.current_task_id())
    iterate()
    assert all(p.get_can_pop() for p in window._pages()[1:])
    window.nav.pop()
    iterate()
    assert window.visible_page() is window.list_page
    window.show_lists()
    iterate()
    assert window.visible_page() is window.lists_page
    window.show_journey()
    iterate()
    assert window.visible_page().get_tag() == "journey"
    assert window.split.get_content() is window.journey_page
    window.show_list(Context.today())
    iterate()
    assert window.split.get_content() is window.list_page
    window.split.set_collapsed(False)
    iterate()
    assert window.visible_page() is window.list_page
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


def test_change_project_on_the_task_page(app, tmp_path):
    """Choosing another project used to crash: the redraw replaced the
    combo row's list while the row still handled the selection."""
    window = new_window(app, tmp_path, demo.create())
    task_id = window.ds.top_level_ids(Context("project", "demo-website"))[0]
    window.show_task(task_id)
    iterate()
    page = window.nav.get_visible_page()
    model = page.project_row.get_model()
    page.project_row.activate()
    iterate()
    page.project_row.set_selected(page._project_ids.index("demo-garden"))
    iterate()
    assert window.ds.task(task_id)["projectId"] == "demo-garden"
    assert task_id in window.ds.project_entities["demo-garden"]["taskIds"]
    assert task_id not in window.ds.project_entities["demo-website"]["taskIds"]
    assert page.project_row.get_model() is model
    assert page._project_ids[page.project_row.get_selected()] == "demo-garden"
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


needs_engine = pytest.mark.skipif(
    not os.environ.get("PENSUM_QUESTARC_DIR") and not os.environ.get("PENSUM_REQUIRE_ENGINE"),
    reason="needs gjs and QuestArc's engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)")


def visible(window):
    return window.visible_page()


@needs_engine
def test_walk_into_a_journey(app, tmp_path):
    window = new_window(app, tmp_path)
    window.show_journey()
    iterate()
    page = visible(window)
    assert page.get_tag() == "journey"
    # The welcome: no mode to choose and nothing written (pensum#61).
    assert window.journeys.records() == {}
    assert page.main_button.get_label() == "Choose a journey"
    page._main_action()
    iterate()
    choose = visible(window)
    assert choose.get_tag() == "journey-choose"
    from pensum.ui.journey.choose_page import PreviewPage
    window.nav.push(PreviewPage(window, "gentle-morning"))
    iterate()
    visible(window)._main()  # Start this journey
    iterate()
    start = visible(window)
    start.why_row.set_text("Calmer mornings")
    start._main()
    iterate()
    assert visible(window) is page
    assert page.main_button.get_label() == "Set up the task"
    page._main_action()
    iterate()
    setup = visible(window)
    setup._main()  # Create the task
    iterate(40)
    assert visible(window) is page
    run = window.journeys.active()
    assert run["why"] == "Calmer mornings"
    assert run["stations"][0]["state"] == "current"
    task_id = next(t["id"] for t in window.ds.tasks.values() if t.get("repeatCfgId"))
    from pensum.store import tasks
    tasks.set_done(window.ds, task_id, True)
    window.journeys.refresh_now()
    iterate()
    assert window.journeys.active()["stations"][0]["completions"] == 1
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()


def settle(window, seconds=10):
    """Run the main loop until the background evaluation has finished."""
    import time
    model = window.journeys
    deadline = time.monotonic() + seconds
    iterate()
    while (model._source is not None or model._running) and time.monotonic() < deadline:
        iterate()
        time.sleep(0.02)
    iterate()


@needs_engine
def test_journey_comes_forward_only_for_its_own_task(app, tmp_path):
    from pensum.game import content, engine, records
    from pensum.store import tasks
    window = new_window(app, tmp_path)
    journey = content.journey("gentle-morning")
    records.write(window.ds, engine.action("startJourney", {
        "runId": "r", "journey": journey, "startDay": window.ds.today()}))
    window.changed()
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    page = visible(window)
    page._main_action()  # Set up the task
    iterate()
    setup = visible(window)
    assert setup.get_tag() == "journey-setup"
    setup._main()  # Create the task
    iterate(40)
    assert visible(window) is page
    stage_task = next(t["id"] for t in window.ds.tasks.values() if t.get("repeatCfgId"))

    # Unrelated actions keep the user where they are, though the set-up
    # page they came through is still alive.
    window.show_list(Context.today())
    iterate()
    other = tasks.add_task(window.ds, "Water the plants", Context.today())["id"]
    window.changed()
    settle(window)
    assert visible(window) is window.list_page
    tasks.set_done(window.ds, other, True)
    window.changed()
    settle(window)
    assert visible(window) is window.list_page
    window.show_task(other)
    iterate()
    tasks.update(window.ds, other, title="Water the roses")
    window.changed()
    settle(window)
    assert visible(window).get_tag() != "journey"

    # Ticking off the station's own task brings the journey forward.
    window.show_list(Context.today())
    iterate()
    tasks.set_done(window.ds, stage_task, True)
    window.changed()
    settle(window)
    assert visible(window) is window.journey_page
    assert window.journeys.active()["stations"][0]["completions"] == 1
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()


def _labels(widget):
    """The text of every label below a widget."""
    found = [widget.get_label()] if isinstance(widget, Gtk.Label) else []
    child = widget.get_first_child()
    while child:
        found += _labels(child)
        child = child.get_next_sibling()
    return found


@needs_engine
def test_journey_shows_its_build_and_the_stations_as_a_list(app, tmp_path):
    """The journey page shows the build (QuestArc#42, pensum#57, #61): the
    demo's second station of First Things First is a log across the river
    with the next version under way; the stations are a list under
    Stations, with no level, no mode and no drawn path."""
    from pensum.game import content
    if not content.ladders():
        pytest.skip("no ladders in PENSUM_QUESTARC_DIR")
    window = new_window(app, tmp_path, demo.create())
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    page = visible(window)
    build = window.journeys.active()["build"]
    assert (build["ladder"], build["version"], build["versions"]) == ("crossing", 2, 6)
    assert page.build is not None
    words = _labels(page.build)
    assert "1" in words and "2" in words and "3" in words and "4" not in words
    assert any(w.startswith("A log stands") for w in words)
    assert page.title.get_subtitle() == ""
    assert "mode" not in window.journeys.view and "level" not in window.journeys.view
    page.show_stations()
    iterate()
    stations = visible(window)
    assert stations.get_tag() == "journey-stations"
    rows = [w for w in _widgets(stations) if "pensum-journey-station" in w.get_css_classes()]
    assert [r.get_subtitle() for r in rows][:2] == ["Station 1 of 5 · Done",
                                                    "Station 2 of 5 · You are here"]
    window.nav.pop()
    iterate()
    window.close()


@needs_engine
def test_what_you_build_writes_only_the_choice(app, tmp_path):
    """Changing the colour or what grows writes one build record with what
    the user picked; flowers cannot hang over water; the journey's
    suggestion withdraws it. The data stays valid."""
    from pensum.game import content, records
    if not content.ladders():
        pytest.skip("no ladders in PENSUM_QUESTARC_DIR")
    window = new_window(app, tmp_path, demo.create())
    window.journeys.refresh_now()
    window.show_journey()
    iterate()
    window.journey_page.show_build()
    iterate()
    page = visible(window)
    assert page.get_tag() == "journey-build"
    run = window.journeys.active()
    page._choose(run, "hue", "slate")
    iterate()
    assert records.load(window.ds)["build:demo"] == {"hue": "slate"}
    assert window.journeys.active()["build"]["hue"] == "slate"
    run = window.journeys.active()
    page._choose(run, "ladder", "home")
    page._choose(window.journeys.active(), "marker", "flowers")
    iterate()
    assert records.load(window.ds)["build:demo"] == {"hue": "slate", "ladder": "home",
                                                     "marker": "flowers"}
    # Back over water the flowers no longer fit: the ladder's own marker applies.
    page._choose(window.journeys.active(), "ladder", "crossing")
    iterate()
    assert records.load(window.ds)["build:demo"] == {"hue": "slate", "ladder": "crossing"}
    build = window.journeys.active()["build"]
    assert (build["ladder"], build["marker"], build["version"]) == ("crossing", "lanterns", 2)
    window.journeys.action("chooseBuild", "demo", {})
    iterate()
    assert "build:demo" not in records.load(window.ds)
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
    window.close()


def test_sync_page_reads_folder_and_imports(app, tmp_path):
    """Read a sync folder written by Super Productivity, show its counts,
    import it; the folder stays as it was and the data stays valid."""
    import shutil
    from pathlib import Path
    folder = tmp_path / "sync"
    shutil.copytree(Path(__file__).parent / "fixtures" / "sync", folder)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    window = new_window(app, tmp_path, demo.create())
    window.show_sync()
    iterate()
    page = window.nav.get_visible_page()
    assert window.get_focus() is None or not isinstance(window.get_focus(), Gtk.Text)
    page.read(wait=True)  # WebDAV without an address
    assert page.banner.get_revealed() and page.snapshot is None
    page.kind_row.set_selected(1)
    window.settings.sync_local_path = str(folder)
    page.read(wait=True)
    iterate()
    assert not page.banner.get_revealed()
    assert page.snapshot.format == "v2"
    assert int(page.rows["open"].get_label()) + int(page.rows["done"].get_label()) == \
        len(page.snapshot.data["task"]["ids"])
    assert page.rows["changes"].get_label() == "0"
    assert page.import_button.get_sensitive()
    page.import_now()
    iterate()
    titles = {t["title"] for t in window.ds.data["task"]["entities"].values()}
    assert "Sync test: water the plants" in titles
    assert validate.problems(window.ds.data) == []
    assert {p.name: p.read_bytes() for p in folder.iterdir()} == before
    assert window.settings.sync_kind == "local"
    window.close()


def test_sync_page_asks_for_encryption_password(app, tmp_path):
    """An encrypted folder (#29): without the password the page says so,
    with it the data is read."""
    from pathlib import Path
    window = new_window(app, tmp_path, demo.create())
    window.settings.sync_kind = "local"
    window.settings.sync_local_path = str(Path(__file__).parent / "fixtures" / "sync-encrypted")
    window.show_sync()
    iterate()
    page = window.nav.get_visible_page()
    page.read(wait=True)
    assert page.banner.get_revealed() and "encryption password" in page.banner.get_title()
    page.encryption_row.set_text("test password")
    page.read(wait=True)
    iterate()
    assert not page.banner.get_revealed() and page.snapshot is not None
    assert validate.problems(page.snapshot.data) == []
    window.close()
