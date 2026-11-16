"""The home of the journeys (QuestArc docs/behaviour.md, screen 0): the
Valley, one path through the day with a place for every moment, and the
growing step as a card below it. The welcome and the error states are
here too. Tapping the growing place or its card opens the journey's own
page (`run_page.py`); the main action at the bottom is **A New Moment**.
At 720 px and wider the scene stands on the left and the card on the
right."""
from gi.repository import Adw, Gtk

from pensum.game import engine, moments
from pensum.game.content import t
from pensum.ui.journey.banners import banners
from pensum.ui.journey.confirm_card import confirm_cards
from pensum.ui.journey.growing_card import growing_card
from pensum.ui.journey.valley import MAX_WIDTH, ValleyScene


class JourneyPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="Journeys", tag="journey")
        self.window = window
        self.model = window.journeys
        self._layouts = {}
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="Menu")
        self.menu_button.update_property([Gtk.AccessibleProperty.LABEL], ["Menu"])
        header.pack_end(self.menu_button)
        toolbar.add_top_bar(header)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12,
                           margin_bottom=24, margin_start=12, margin_end=12)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
                                    child=self.box)
        # At 720 px and wider the scene stands on the left, the card on the right.
        wide = Adw.BreakpointBin(child=scroll, width_request=360, height_request=294)
        breakpoint_ = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 720sp"))
        breakpoint_.add_setter(self.box, "orientation", Gtk.Orientation.HORIZONTAL)
        breakpoint_.add_setter(self.box, "spacing", 24)
        wide.add_breakpoint(breakpoint_)
        toolbar.set_content(wide)
        self.main_button = Gtk.Button(hexpand=True, css_classes=["pensum-bar-button"])
        self.main_button.connect("clicked", lambda *_: self.show_choose())
        bar = Gtk.Box(margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        bar.append(self.main_button)
        self.bottom = Adw.Clamp(child=bar, maximum_size=480)
        toolbar.add_bottom_bar(self.bottom)
        self.set_child(toolbar)
        self.scene = None
        self.card = None
        self._build_menu()
        self.model.listeners.append(self.refresh)
        self.connect("destroy", lambda *_: self._forget())
        self.refresh()

    def _forget(self):
        if self.refresh in self.model.listeners:
            self.model.listeners.remove(self.refresh)

    def _build_menu(self):
        from gi.repository import Gio
        menu = Gio.Menu()
        menu.append(t("ui.shelf.title"), "journey.shelf")
        menu.append(t("ui.motivates.title"), "journey.motivates")
        self.menu_button.set_menu_model(menu)
        actions = Gio.SimpleActionGroup()
        for name, callback in (("shelf", self.show_shelf), ("motivates", self.show_motivates)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_a, c=callback: c())
            actions.add_action(action)
        self.insert_action_group("journey", actions)

    # --- showing -------------------------------------------------------

    def _set_main(self, label, suggested=False):
        self.main_button.set_label(label or "")
        self.bottom.set_visible(bool(label))
        (self.main_button.add_css_class if suggested
         else self.main_button.remove_css_class)("suggested-action")

    def _show(self, *widgets):
        while (child := self.box.get_first_child()) is not None:
            self.box.remove(child)
        for widget in widgets:
            self.box.append(widget)

    def _status(self, icon, title, description):
        self._show(Adw.StatusPage(icon_name=icon, title=title, description=description,
                                  hexpand=True, vexpand=True))

    def refresh(self):
        model = self.model
        self.scene = self.card = None
        if not model.available:
            self._set_main(None)
            return self._status("dialog-information-symbolic", "Journeys Are Not Installed",
                                "This build of Day Planner comes without QuestArc's journeys.")
        if not model.records():
            self._set_main(t("ui.home.choose"), suggested=True)
            return self._status("mark-location-symbolic", "Journeys",
                                f"{t('ui.welcome.what')} {t('ui.welcome.how')}")
        if model.error and model.view is None:
            self._set_main(None)
            return self._status("dialog-warning-symbolic", "Journeys Can't Be Shown", model.error)
        if model.view is None:
            model.refresh_now()
            if model.view is None:
                return None
        self._home()
        return None

    def _layout(self, sides, things, units):
        key = (tuple(sides), tuple(things), units)
        if key not in self._layouts:
            self._layouts[key] = engine.valley_layout(sides, things, 360, units)
        return self._layouts[key]

    def _scene_units(self, empty):
        """The scene's height in layout units: about two thirds of the
        window, so the card starts on the first screen; never less than
        480, where the layout's checks hold for any number of places."""
        if empty:
            return 240
        return max(480, round(self.window.get_height() * 2 / 3) if self.window.get_height() > 0
                   else 480)

    def _home(self):
        view = self.model.view
        places = view.get("valley", [])
        titles = [moments.place_title(view, p) for p in places]
        units = self._scene_units(not places)
        layout = self._layout([p["side"] for p in places],
                              [max(1, len(p["things"])) for p in places], units)
        self.scene = ValleyScene(places, titles, layout, on_open=self._open_place)
        left = Adw.Clamp(child=self.scene, maximum_size=MAX_WIDTH, valign=Gtk.Align.START)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True,
                        valign=Gtk.Align.START)
        for card in confirm_cards(self):
            right.append(card)
        current = self.model.current()
        if current:
            run, journey, index, station, stage = current
            self.card = growing_card(run, stage, index, station, view["todayStr"],
                                     self.show_run)
            right.append(self.card)
            for banner in banners(self, run, journey, index):
                right.append(banner)
        elif not places:
            right.append(Adw.StatusPage(title=t("ui.home.empty.title"),
                                        description=t("ui.home.empty.text")))
        self._show(left, right)
        self._set_main(t("ui.anchor.new"), suggested=not current)

    def _open_place(self, index):
        place = self.model.view["valley"][index]
        if place["growing"]:
            self.show_run()
        else:
            from pensum.ui.journey.place_page import PlacePage
            self._push(PlacePage(self.window, place["anchorId"]))

    # --- pushed pages ---------------------------------------------------

    def _push(self, page):
        self.window.nav.push(page)

    def show_run(self):
        from pensum.ui.journey.run_page import RunPage
        self._push(RunPage(self.window))

    def show_choose(self):
        from pensum.ui.journey.choose_page import ChoosePage
        self._push(ChoosePage(self.window))

    def show_checkin(self):
        from pensum.ui.journey.checkin_page import CheckinPage
        self._push(CheckinPage(self.window))

    def show_shelf(self):
        from pensum.ui.journey.shelf_page import ShelfPage
        self._push(ShelfPage(self.window))

    def show_motivates(self):
        from pensum.ui.journey.motivates_page import MotivatesPage
        self._push(MotivatesPage())
