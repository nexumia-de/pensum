"""The journey's own page (QuestArc docs/behaviour.md, screen 4), pushed
from the Valley (the home, `page.py`): the active journey with its build
on top, its banners and the current station's card; the stations are a
list under "Stations" in the menu. The main action sits in the bottom
bar; the menu holds the shelf, how it motivates you, pausing and
ending."""
from gi.repository import Adw, Gio, Gtk

from pensum.game.content import t
from pensum.ui.journey.banners import banners
from pensum.ui.journey.habits import habit_banners
from pensum.ui.journey import place_piece
from pensum.ui.journey import read_only as read_only_page
from pensum.ui.journey.build import build_header
from pensum.ui.journey.place_piece import place_of_run
from pensum.ui.journey.card import station_card
from pensum.ui.journey.tick import Growth


class RunPage(Adw.NavigationPage):
    def __init__(self, window):
        # No tag: a tagged page stays registered for a moment after it is
        # popped, and tapping the card again at once would be refused.
        super().__init__(title="Journey")
        self.window = window
        self.model = window.journeys
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title = Adw.WindowTitle(title="Journey")
        header.set_title_widget(self.title)
        self.menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="Menu")
        self.menu_button.update_property([Gtk.AccessibleProperty.LABEL], ["Menu"])
        header.pack_end(self.menu_button)
        toolbar.add_top_bar(header)
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        # At 720 px and wider the build is on the left and the card on the
        # right (QuestArc journey design, desktop).
        self.columns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12,
                               margin_bottom=24, margin_start=12, margin_end=12)
        self.clamp = Adw.Clamp(child=self.columns, maximum_size=600)
        self.scroll.set_child(self.clamp)
        wide = Adw.BreakpointBin(child=self.scroll, width_request=360, height_request=294)
        point = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("min-width: 720sp"))
        point.add_setter(self.columns, "orientation", Gtk.Orientation.HORIZONTAL)
        point.add_setter(self.columns, "spacing", 24)
        point.add_setter(self.clamp, "maximum-size", 1120)
        wide.add_breakpoint(point)
        toolbar.set_content(wide)
        # The moment of the tick: which flowers this page drew last.
        self.growth = Growth()
        self.bar = Gtk.Box(margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        self.main_button = Gtk.Button(hexpand=True)
        self.main_button.add_css_class("suggested-action")
        self.main_button.add_css_class("pensum-bar-button")
        self.main_button.connect("clicked", lambda *_: self._main_action())
        self.bar.append(self.main_button)
        self.bottom = Adw.Clamp(child=self.bar, maximum_size=480)
        toolbar.add_bottom_bar(self.bottom)
        self.set_child(toolbar)
        self._main = None
        self._actions = Gio.SimpleActionGroup()
        for name, callback in (("shelf", self.show_shelf), ("motivates", self.show_motivates),
                               ("build", self.show_build), ("stations", self.show_stations),
                               ("plan-check", self.show_plan_check),
                               ("pause", self._on_pause), ("resume", self._on_resume),
                               ("end", self._on_end)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_a, c=callback: c())
            self._actions.add_action(action)
        self.insert_action_group("journey", self._actions)
        self.model.listeners.append(self.refresh)
        self.connect("destroy", lambda *_: self._forget())
        self.refresh()

    def _forget(self):
        if self.refresh in self.model.listeners:
            self.model.listeners.remove(self.refresh)

    # --- showing -------------------------------------------------------

    def _menu(self, run, built=False):
        menu = Gio.Menu()
        if run:
            game = Gio.Menu()
            if built:
                game.append(t("ui.build.title"), "journey.build")
            game.append(t("ui.build.stations"), "journey.stations")
            game.append(t("ui.check.title"), "journey.plan-check")
            menu.append_section(None, game)
        if run:
            menu.append(t("ui.action.resume") if run["paused"] else t("ui.menu.pause"),
                        "journey.resume" if run["paused"] else "journey.pause")
            menu.append(t("ui.menu.end"), "journey.end")
        rest = Gio.Menu()
        rest.append(t("ui.shelf.title"), "journey.shelf")
        rest.append(t("ui.motivates.title"), "journey.motivates")
        menu.append_section(None, rest)
        self.menu_button.set_menu_model(menu)

    def _set_main(self, label, action, quiet=False):
        self._main = action
        (self.main_button.remove_css_class if quiet else self.main_button.add_css_class)(
            "suggested-action")
        self.main_button.set_label(label or "")
        self.bottom.set_visible(bool(label))

    def refresh(self):
        model = self.model
        while (child := self.columns.get_first_child()) is not None:
            self.columns.remove(child)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True,
                      valign=Gtk.Align.START)
        self.title.set_subtitle("")
        self.columns.append(box)
        self.build = None
        if model.view is None:
            model.refresh_now()
            if model.view is None:
                return
        current = model.current()
        read_only = model.read_only()
        if read_only:
            self._menu(None)
            self._set_main(None, None)
            self.title.set_title(read_only_page.title(read_only))
            box.append(read_only_page.status_page(read_only))
            return
        if not current:
            self._menu(None)
            self._set_main(None, None)
            box.append(Adw.StatusPage(icon_name="mark-location-symbolic",
                                      title=t("ui.home.empty.title"),
                                      description=t("ui.home.empty.text"), vexpand=True))
            return
        run, journey, index, station, stage = current
        self.title.set_title(t(journey["title"]))
        # The journey is set in its place (a run without a moment has none yet).
        place = place_of_run(model.view, run["runId"])
        self.build = place_piece.section(self.window, model.view, place, run["runId"],
                                         self.growth) \
            if place else build_header(run.get("build"))
        self._menu(run, built=self.build is not None)
        if self.build:
            self.build.set_hexpand(True)
            self.build.set_valign(Gtk.Align.START)
            self.columns.prepend(Adw.Clamp(child=self.build, maximum_size=560, hexpand=True,
                                           valign=Gtk.Align.START))
        for banner in banners(self, run, journey, index):
            box.append(banner)
        for banner in habit_banners(self):
            box.append(banner)
        box.append(station_card(run, stage, index, station, model.view["todayStr"]))
        state = station["state"]
        if run["paused"]:
            self._set_main(None, None)
        elif state == "met":
            # While the user stays a while, Continue is a quiet action.
            staying = bool((run.get("offer") or {}).get("quietUntil"))
            self._set_main(t("ui.action.continue"), self.show_continue, quiet=staying)
        elif state in ("unbound", "unsupported-repeat"):
            self._set_main(t("ui.action.setup") if state == "unbound"
                           else t("ui.action.change-repeat"), self.show_setup)
        else:
            self._set_main(None, None)

    def _main_action(self):
        if self._main:
            self._main()

    # --- pushed pages and actions ----------------------------------------

    def _push(self, page):
        self.window.nav.push(page)

    def show_choose(self):
        from pensum.ui.journey.choose_page import ChoosePage
        self._push(ChoosePage(self.window))

    def show_setup(self):
        from pensum.ui.journey.setup_page import SetupPage
        self._push(SetupPage(self.window))

    def show_continue(self):
        from pensum.ui.journey.continue_page import ContinuePage
        self._push(ContinuePage(self.window))

    def show_station(self, index):
        from pensum.ui.journey.station_page import StationPage
        self._push(StationPage(self.window, index))

    def show_build(self):
        from pensum.ui.journey.build_page import BuildPage
        self._push(BuildPage(self.window))

    def show_plan_check(self):
        from pensum.ui.journey.plan_check import PlanCheckPage
        self._push(PlanCheckPage(self.window))

    def show_stations(self):
        from pensum.ui.journey.stations_page import StationsPage
        self._push(StationsPage(self.window))

    def show_smaller(self):
        from pensum.ui.journey.smaller_page import SmallerPage
        self._push(SmallerPage(self.window))

    def show_checkin(self, run_id=None):
        from pensum.ui.journey.checkin_page import CheckinPage
        self._push(CheckinPage(self.window, run_id))

    def show_graduate(self, run_id):
        from pensum.ui.journey.graduate_page import GraduatePage
        self._push(GraduatePage(self.window, run_id))

    def show_still(self, run_id):
        from pensum.ui.journey.still_page import StillPage
        self._push(StillPage(self.window, run_id))

    def show_shelf(self):
        from pensum.ui.journey.shelf_page import ShelfPage
        self._push(ShelfPage(self.window))

    def show_motivates(self):
        from pensum.ui.journey.motivates_page import MotivatesPage
        self._push(MotivatesPage())

    def _today(self):
        return self.model.view["todayStr"]

    def _on_pause(self):
        run = self.model.active()
        if run:
            self.model.action("pauseJourney", run["runId"], self._today())

    def _on_resume(self):
        run = self.model.active()
        if run:
            self.model.action("resumeJourney", run["runId"], self._today())

    def _on_end(self):
        current = self.model.current()
        if not current:
            return
        run, journey = current[0], current[1]
        self.model.action("endJourney", run["runId"], self._today())
        toast = Adw.Toast(title=t("ui.banner.ended", title=t(journey["title"])),
                          button_label=t("ui.action.undo"))
        toast.connect("button-clicked",
                      lambda *_: self.model.action("withdraw", f"run-end:{run['runId']}"))
        self.window.toasts.add_toast(toast)
