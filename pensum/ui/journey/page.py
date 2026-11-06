"""The journey page (QuestArc docs/behaviour.md, screens 1 and 4): the
welcome with the choice between calm and game, the empty state, or the
active journey with its banners, the current station's card and the
path. The main action sits in the bottom bar; the menu holds the shelf,
how it motivates you, pausing and ending."""
from gi.repository import Adw, Gio, Gtk

from pensum.game.content import t
from pensum.ui.journey.banners import banners
from pensum.ui.journey.card import station_card
from pensum.ui.journey.path import journey_path


class JourneyPage(Adw.NavigationPage):
    def __init__(self, window):
        super().__init__(title="Journeys", tag="journey")
        self.window = window
        self.model = window.journeys
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        self.title = Adw.WindowTitle(title="Journeys")
        header.set_title_widget(self.title)
        self.menu_button = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text="Menu")
        self.menu_button.update_property([Gtk.AccessibleProperty.LABEL], ["Menu"])
        header.pack_end(self.menu_button)
        toolbar.add_top_bar(header)
        self.scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        toolbar.set_content(self.scroll)
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

    def _menu(self, run):
        menu = Gio.Menu()
        if run:
            menu.append(t("ui.action.resume") if run["paused"] else t("ui.menu.pause"),
                        "journey.resume" if run["paused"] else "journey.pause")
            menu.append(t("ui.menu.end"), "journey.end")
        rest = Gio.Menu()
        rest.append(t("ui.shelf.title"), "journey.shelf")
        rest.append(t("ui.motivates.title"), "journey.motivates")
        menu.append_section(None, rest)
        self.menu_button.set_menu_model(menu)

    def _set_main(self, label, action):
        self._main = action
        self.main_button.set_label(label or "")
        self.bottom.set_visible(bool(label))

    def refresh(self):
        model = self.model
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12,
                      margin_bottom=24, margin_start=12, margin_end=12)
        self.scroll.set_child(Adw.Clamp(child=box, maximum_size=600))
        self.title.set_subtitle("")
        if not model.available:
            self._menu(None)
            self._set_main(None, None)
            box.append(Adw.StatusPage(icon_name="dialog-information-symbolic",
                                      title="Journeys Are Not Installed",
                                      description="This build of Day Planner comes without "
                                                  "QuestArc's journeys."))
            return
        if "settings" not in model.records():
            self._menu(None)
            self._welcome(box)
            return
        if model.error and model.view is None:
            self._menu(None)
            self._set_main(None, None)
            box.append(Adw.StatusPage(icon_name="dialog-warning-symbolic",
                                      title="Journeys Can't Be Shown",
                                      description=model.error))
            return
        if model.view is None:
            model.refresh_now()
            if model.view is None:
                return
        rpg = model.mode() == "rpg"
        if rpg:
            self.title.set_subtitle(t("ui.level", level=model.view["level"]))
        current = model.current()
        if not current:
            self.title.set_title("Journeys")
            self._menu(None)
            self._set_main(t("ui.home.choose"), self.show_choose)
            box.append(Adw.StatusPage(icon_name="mark-location-symbolic",
                                      title=t("ui.home.empty.title"),
                                      description=t("ui.home.empty.text"), vexpand=True))
            return
        run, journey, index, station, stage = current
        self.title.set_title(t(journey["title"]))
        self._menu(run)
        for banner in banners(self, run, journey, index):
            box.append(banner)
        box.append(station_card(run, stage, index, station, rpg, model.view["todayStr"]))
        box.append(journey_path(run, journey, rpg, self.show_station))
        state = station["state"]
        if run["paused"]:
            self._set_main(None, None)
        elif state == "met":
            self._set_main(t("ui.action.continue"), self.show_continue)
        elif state in ("unbound", "unsupported-repeat"):
            self._set_main(t("ui.action.setup") if state == "unbound"
                           else t("ui.action.change-repeat"), self.show_setup)
        else:
            self._set_main(None, None)

    def _welcome(self, box):
        status = Adw.StatusPage(icon_name="mark-location-symbolic", title="Journeys",
                                description=f"{t('ui.welcome.what')} {t('ui.welcome.how')}")
        box.append(status)
        group = Adw.PreferencesGroup(title=t("ui.mode.title"),
                                     description=t("ui.mode.change"))
        self._mode = "calm"
        first = None
        for mode, title, text in (("calm", t("ui.mode.calm"), t("ui.mode.calm.text")),
                                  ("rpg", t("ui.mode.rpg"), t("ui.mode.rpg.text"))):
            check = Gtk.CheckButton(active=mode == "calm", group=first)
            first = first or check
            check.connect("toggled", lambda c, m=mode: c.get_active() and setattr(
                self, "_mode", m))
            row = Adw.ActionRow(title=title, subtitle=text, activatable_widget=check)
            row.add_prefix(check)
            group.add(row)
        box.append(group)
        self._set_main("Get Started", lambda: self.model.action("setMode", self._mode))

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

    def show_checkin(self):
        from pensum.ui.journey.checkin_page import CheckinPage
        self._push(CheckinPage(self.window))

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
