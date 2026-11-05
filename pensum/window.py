"""The window: the lists in a sidebar, the open list and its task pages in
a navigation view next to it (swipe back everywhere), the timer bar, and
saving the dataset shortly after each change."""
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

        from pensum.ui.sidebar import Sidebar
        from pensum.ui.task_list import TaskListPage
        from pensum.ui.tracker_bar import TrackerBar
        self.sidebar = Sidebar(self)
        sidebar_page = Adw.NavigationPage(title=NAME, tag="lists",
                                          child=self.sidebar)
        self.nav = Adw.NavigationView()
        self.tracker_bar = TrackerBar(self)
        content = Adw.ToolbarView(content=self.nav)
        content.add_bottom_bar(self.tracker_bar)
        self.list_page = TaskListPage(self, parse_context_key(self.settings.last_list))
        self.nav.add(self.list_page)
        self.split = Adw.NavigationSplitView(
            sidebar=sidebar_page,
            content=Adw.NavigationPage(title="Tasks", tag="content", child=content),
            show_content=True)
        self.toasts = Adw.ToastOverlay(child=self.split)
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
        # No field focused at the start: on the phone that would open the
        # on-screen keyboard over the list.
        self.connect("map", lambda *_: GLib.idle_add(self._unfocus))

    # --- data ------------------------------------------------------------

    def changed(self):
        """Something in the dataset changed: redraw and save soon."""
        self.refresh()
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

    def _on_tick(self):
        self.tracker_bar.refresh()
        for page in self._pages():
            if hasattr(page, "tick"):
                page.tick()

    def _pages(self):
        stack = self.nav.get_navigation_stack()
        return [stack.get_item(i) for i in range(stack.get_n_items())]

    def _unfocus(self):
        self.set_focus(None)
        return GLib.SOURCE_REMOVE

    def show_lists(self):
        """The sidebar; on the phone it replaces the open list."""
        self.split.set_show_content(False)

    def _on_close(self, *_):
        self.flush()
        return False

    def toast(self, message):
        self.toasts.add_toast(Adw.Toast(title=GLib.markup_escape_text(message)))

    def save_settings(self):
        self.settings_store.save(self.settings)

    # --- navigation ------------------------------------------------------

    def show_list(self, context):
        if not self.ds.context_exists(context):
            context = Context.today()
        self.nav.pop_to_page(self.list_page)
        self.list_page.set_context(context)
        self.split.set_show_content(True)
        self.sidebar.select(context)
        self.settings.last_list = context_key(context)
        self.save_settings()

    def show_list_key(self, key):
        self.show_list(parse_context_key(key))

    def show_task(self, task_id):
        if task_id not in self.ds.tasks:
            return
        from pensum.ui.task_page import TaskPage
        self.split.set_show_content(True)
        self.nav.push(TaskPage(self, task_id))
