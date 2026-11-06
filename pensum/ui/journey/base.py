"""What every page pushed from the journey page shares: a header, a
scrolling preferences page and an optional main action in the bottom
bar, and a redraw when the game view changes."""
from gi.repository import Adw, Gtk


class JourneySubpage(Adw.NavigationPage):
    def __init__(self, window, title, tag):
        super().__init__(title=title, tag=tag)
        self.window = window
        self.model = window.journeys
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.page = Adw.PreferencesPage()
        toolbar.set_content(self.page)
        bar = Gtk.Box(margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        self.main_button = Gtk.Button(hexpand=True)
        self.main_button.add_css_class("suggested-action")
        self.main_button.add_css_class("pensum-bar-button")
        self.main_button.connect("clicked", lambda *_: self._main and self._main())
        bar.append(self.main_button)
        self.bottom = Adw.Clamp(child=bar, maximum_size=480, visible=False)
        toolbar.add_bottom_bar(self.bottom)
        self.set_child(toolbar)
        self._main = None
        self._groups = []

    def set_main(self, label, action):
        self._main = action
        self.main_button.set_label(label or "")
        self.bottom.set_visible(bool(label))

    def clear(self):
        for group in self._groups:
            self.page.remove(group)
        self._groups = []

    def group(self, title=None, description=None):
        group = Adw.PreferencesGroup(title=title or "", description=description or "")
        self.page.add(group)
        self._groups.append(group)
        return group

    def text(self, text, *classes):
        group = self.group()
        label = Gtk.Label(label=text, xalign=0, wrap=True)
        for name in classes:
            label.add_css_class(name)
        group.add(label)
        return label

    def back_to_journey(self):
        self.window.show_journey()
