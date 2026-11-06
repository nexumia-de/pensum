"""The window: the lists and the shown list in a split view, pages such as
a task pushed on top, the timer bar, and saving the dataset shortly after
each change.

The layout is Ephyra's (phosh-toolkit docs/adaptive-libadwaita.md, rule
9): one AdwNavigationView whose first page holds an AdwNavigationSplitView
with the lists as sidebar and the shown list (or the journey) as content.
Below 600 sp the split view collapses, so a swipe from a list goes back to
the lists; every other page is pushed on the navigation view and swipes
back to where it came from."""
import logging

from gi.repository import Adw, Gio, GLib, Gtk

from pensum import NAME
from pensum.store.dataset import Context

log = logging.getLogger("pensum.window")
SAVE_DELAY_MS = 800


def context_key(context):
    return f"{context.kind}:{context.id}"


def parse_context_key(key):
    kind, _, context_id = (key or "").partition(":")
    if kind == "today" or kind not in ("project", "tag"):
        return Context.today()
    return Context(kind, context_id)


class Window(Adw.ApplicationWindow):
    def __init__(self, app, files, settings_store):
        super().__init__(application=app, default_width=1000,
                         default_height=700, title=NAME)
        # Breakpoints need a minimum size (phosh-toolkit adaptive rules).
        self.set_size_request(360, 294)
        self.files = files
        self.ds = files.load()
        self.settings_store = settings_store
        self.settings = settings_store.load()
        self._save_source = None

        from pensum.timer import Timer
        self.timer = Timer(lambda: self.ds, self.changed, self._on_tick)
        from pensum.day_watch import DayWatch
        self.day_watch = DayWatch(lambda: self.ds, self.changed)
        from pensum.ui.journey.model import JourneyModel
        self.journeys = JourneyModel(self)

        from pensum.ui.sidebar import Sidebar
        from pensum.ui.task_list import TaskListPage
        from pensum.ui.tracker_bar import TrackerBar
        self.sidebar = Sidebar(self)
        self.lists_page = Adw.NavigationPage(title=NAME, tag="lists",
                                             child=self.sidebar)
        self.list_page = TaskListPage(self, parse_context_key(self.settings.last_list))
        self.split = Adw.NavigationSplitView(sidebar=self.lists_page,
                                             content=self.list_page, show_content=True)
        self.split.connect("notify::show-content", lambda *_: self.tracker_bar.refresh())
        self.main_page = Adw.NavigationPage(title=NAME, tag="main", child=self.split)
        self.nav = Adw.NavigationView()
        self.nav.add(self.main_page)
        self.tracker_bar = TrackerBar(self)
        self.nav.connect("notify::visible-page", lambda *_: self.tracker_bar.refresh())
        content = Adw.ToolbarView(content=self.nav)
        content.add_bottom_bar(self.tracker_bar)
        self.toasts = Adw.ToastOverlay(child=content)
        self.set_content(self.toasts)

        breakpoint = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("max-width: 600sp"))
        breakpoint.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(breakpoint)

        action = Gio.SimpleAction.new("add-task", None)
        action.connect("activate", lambda *_: self.list_page.focus_entry())
        self.add_action(action)
        self.connect("close-request", self._on_close)
        self.timer.resume()
        self.refresh()
        if self.day_watch.start_day():
            self.changed()
        # No field focused at the start: on the phone that would open the
        # on-screen keyboard over the list.
        self.connect("map", lambda *_: GLib.idle_add(self._unfocus))

    # --- data ------------------------------------------------------------

    def changed(self):
        """Something in the dataset changed: redraw, update the journey
        and save soon."""
        self.refresh()
        self.journeys.schedule()
        if self._save_source is None:
            self._save_source = GLib.timeout_add(SAVE_DELAY_MS, self._save_now)

    def _save_now(self):
        self._save_source = None
        try:
            self.files.save(self.ds)
        except OSError as error:
            log.warning("saving failed: %s", error)
            self.toast("Can't save the tasks")
        return GLib.SOURCE_REMOVE

    def flush(self):
        """Book the running time and save now (closing, importing)."""
        self.timer.book()
        if self._save_source is not None:
            GLib.source_remove(self._save_source)
        self._save_now()

    def replace_dataset(self, ds):
        """After an import: show the new data from the start."""
        self.timer.stop()
        self.ds = ds
        self.day_watch.start_day()
        self.timer.resume()
        self.show_list(Context.today())
        self.refresh()

    def refresh(self):
        if not self.ds.context_exists(self.list_page.context):
            self.list_page.set_context(Context.today())
        self.sidebar.refresh()
        for page in self._pages():
            if hasattr(page, "refresh"):
                page.refresh()
        self.tracker_bar.refresh()

    def _navigation_root(self):
        stack = self.nav.get_navigation_stack()
        return stack.get_item(0) if stack.get_n_items() else None

    def visible_page(self):
        """The page the user sees: a pushed page, else the split view's
        content or, collapsed and showing the lists, the lists."""
        page = self.nav.get_visible_page()
        if page is not self.main_page:
            return page
        if self.split.get_collapsed() and not self.split.get_show_content():
            return self.lists_page
        return self.split.get_content()

    def focus_task_row(self, task_id):
        """Keep the keyboard focus on a row after a move rebuilt the list."""
        page = self.visible_page()
        if hasattr(page, "focus_row"):
            page.focus_row(task_id)

    def _on_tick(self):
        self.tracker_bar.refresh()
        for page in self._pages():
            if hasattr(page, "tick"):
                page.tick()

    def _pages(self):
        """The split view's content and every pushed page."""
        stack = self.nav.get_navigation_stack()
        pushed = [stack.get_item(i) for i in range(1, stack.get_n_items())]
        return [self.split.get_content()] + pushed

    def _unfocus(self):
        self.set_focus(None)
        return GLib.SOURCE_REMOVE

    def _show_content(self, page):
        """Show `page` as the split view's content, above the lists."""
        if self.split.get_content() is not page:
            self.split.set_content(page)
        self.nav.pop_to_page(self.main_page)
        self.split.set_show_content(True)

    def show_lists(self):
        """The lists: on the phone the split view's sidebar page, on wide
        windows always beside the list."""
        self.nav.pop_to_page(self.main_page)
        self.split.set_show_content(False)

    def _on_close(self, *_):
        self.flush()
        return False

    def undoable(self, message, change):
        """Make a change now and show a toast whose Undo puts the whole
        dataset back as it was before."""
        import copy
        self.timer.book()
        before = copy.deepcopy(self.ds.data)
        change()
        self.changed()
        toast = Adw.Toast(title=GLib.markup_escape_text(message), button_label="Undo",
                          priority=Adw.ToastPriority.HIGH)

        def undo(*_):
            self.ds.data.clear()
            self.ds.data.update(before)
            self.timer.resume()
            self.changed()

        toast.connect("button-clicked", undo)
        self.toasts.add_toast(toast)
        return toast

    def toast(self, message):
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(message)))

    def save_settings(self):
        self.settings_store.save(self.settings)

    # --- navigation ------------------------------------------------------

    def show_list(self, context):
        if not self.ds.context_exists(context):
            context = Context.today()
        self.list_page.set_context(context)
        self._show_content(self.list_page)
        self.sidebar.select(context)
        self.settings.last_list = context_key(context)
        self.save_settings()

    def show_list_key(self, key):
        self.show_list(parse_context_key(key))

    def show_search(self):
        from pensum.ui.search_page import SearchPage
        if isinstance(self.nav.get_visible_page(), SearchPage):
            return
        self.nav.push(SearchPage(self))

    def show_archived(self):
        from pensum.ui.archived_page import ArchivedPage
        self.nav.pop_to_page(self.main_page)
        self.nav.push(ArchivedPage(self))

    def show_journey(self):
        """The journey is shown like a list: the split view's content."""
        from pensum.ui.journey.page import JourneyPage
        if getattr(self, "journey_page", None) is None:
            self.journey_page = JourneyPage(self)
        self._show_content(self.journey_page)
        self.sidebar.select(Context("journey", "questarc"))

    def show_task(self, task_id):
        if task_id not in self.ds.tasks:
            return
        from pensum.ui.task_page import TaskPage
        self.nav.push(TaskPage(self, task_id))
