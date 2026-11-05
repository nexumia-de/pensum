"""The bar at the bottom while a task's timer runs: its title, the time
spent today and a button that stops it. Tapping the title opens the task."""
from gi.repository import Gtk, Pango

from pensum import duration


class TrackerBar(Gtk.ActionBar):
    def __init__(self, window):
        super().__init__(revealed=False)
        self.window = window
        button = Gtk.Button(hexpand=True)
        button.add_css_class("flat")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.title = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.title.add_css_class("heading")
        self.time = Gtk.Label(xalign=0)
        self.time.add_css_class("caption")
        self.time.add_css_class("numeric")
        box.append(self.title)
        box.append(self.time)
        button.set_child(box)
        button.set_action_name("app.show-current-task")
        button.set_tooltip_text("Open Running Task")
        self.set_center_widget(None)
        self.pack_start(button)
        stop = Gtk.Button(icon_name="media-playback-stop-symbolic",
                          tooltip_text="Stop Timer", valign=Gtk.Align.CENTER)
        stop.add_css_class("circular")
        stop.add_css_class("suggested-action")
        stop.update_property([Gtk.AccessibleProperty.LABEL], ["Stop Timer"])
        stop.connect("clicked", lambda *_: window.timer.stop())
        self.pack_end(stop)

    def refresh(self):
        ds = self.window.ds
        task_id = self.window.timer.task_id
        task = ds.task(task_id) if task_id else None
        # The running task's own page has the timer button already. Hidden
        # without the reveal animation: animating it while the page slides
        # in crashed gtk4-broadwayd (GNOME 51) in the CI screenshots.
        visible = self.window.nav.get_visible_page()
        on_own_page = task is not None and getattr(visible, "task_id", None) == task_id
        self.set_visible(not on_own_page)
        self.set_revealed(task is not None)
        if task is None:
            return
        self.title.set_label(task.get("title") or "Untitled")
        today = (task.get("timeSpentOnDay") or {}).get(ds.today(), 0)
        self.time.set_label(duration.format_clock(today + self.window.timer.unbooked_ms())
                            + " today")
