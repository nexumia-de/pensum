"""The window: one navigation view for every page (swipe back everywhere),
the lists as its first page on the phone or as a sidebar on wide windows,
the timer bar, and saving the dataset shortly after each change.

There is exactly one AdwNavigationView: a second one nested in a split
view's content kept the back swipe from working on the phone (phosh-toolkit
docs/adaptive-libadwaita.md, rule 9)."""
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
        # Phone: the lists are the first page and a list is pushed on it.
        self.lists_page = Adw.NavigationPage(title=NAME, tag="lists",
                                             child=self.sidebar)
        self.nav = Adw.NavigationView()
        self.tracker_bar = TrackerBar(self)
        self.nav.connect("notify::visible-page", lambda *_: self.tracker_bar.refresh())
        content = Adw.ToolbarView(content=self.nav)
        content.add_bottom_bar(self.tracker_bar)
        self.list_page = TaskListPage(self, parse_context_key(self.settings.last_list))
        self.nav.add(self.lists_page)
        self.nav.push(self.list_page)
        self.wide = False
        # Wide windows: the same sidebar widget moves into this split view
        # and the list becomes the navigation view's first page.
        self.split = Adw.OverlaySplitView(content=content, show_sidebar=False,
                                          collapsed=True, enable_show_gesture=False,
                                          enable_hide_gesture=False)
        self.toasts = Adw.ToastOverlay(child=self.split)
        self.set_content(self.toasts)

        breakpoint = Adw.Breakpoint.new(
            Adw.BreakpointCondition.parse("min-width: 600sp"))
        breakpoint.connect("apply", lambda *_: self._set_wide(True))
        breakpoint.connect("unapply", lambda *_: self._set_wide(False))
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

    def focus_task_row(self, task_id):
        """Keep the keyboard focus on a row after a move rebuilt the list."""
        page = self.nav.get_visible_page()
        if hasattr(page, "focus_row"):
            page.focus_row(task_id)

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

    def _set_wide(self, wide):
        """Move the lists between the first page (phone) and the sidebar."""
        if wide == self.wide:
            return
        self.wide = wide
        pages = [p for p in self._pages() if p is not self.lists_page]
        if wide:
            self.lists_page.set_child(None)
            self.nav.replace(pages or [self.list_page])
            self.split.set_sidebar(self.sidebar)
            self.split.set_collapsed(False)
            self.split.set_show_sidebar(True)
        else:
            self.split.set_show_sidebar(False)
            self.split.set_collapsed(True)
            self.split.set_sidebar(None)
            self.lists_page.set_child(self.sidebar)
            self.nav.replace([self.lists_page] + pages)

    def show_lists(self):
        """The lists: on the phone the first page, on wide windows the
        sidebar, which is always shown."""
        if not self.wide:
            self.nav.pop_to_page(self.lists_page)

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
        if self.list_page in self._pages():
            self.nav.pop_to_page(self.list_page)
        else:
            self.nav.push(self.list_page)
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
        if self.list_page in self._pages():
            self.nav.pop_to_page(self.list_page)
        self.nav.push(ArchivedPage(self))

    def show_task(self, task_id):
        if task_id not in self.ds.tasks:
            return
        from pensum.ui.task_page import TaskPage
        self.nav.push(TaskPage(self, task_id))
