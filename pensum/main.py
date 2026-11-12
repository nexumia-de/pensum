import logging
import os
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from pensum import (APP_ID, NAME, NIGHTLY, REPO_URL, SUPPORT_URL,  # noqa: E402
                    VERSION_LABEL)

log = logging.getLogger("pensum")


def demo_files():
    """PENSUM_DEMO=1: the made-up dataset of pensum.demo in a temporary
    directory, with temporary settings (screenshots)."""
    from pensum import demo
    from pensum.store.files import Files
    directory = Path(tempfile.mkdtemp(prefix="pensum-demo-"))
    os.environ["XDG_CONFIG_HOME"] = str(directory / "config")
    files = Files(directory / "data")
    files.save(demo.create())
    return files


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.files = None
        self.settings_store = None
        for name, callback in (("about", self._on_about),
                               ("preferences", self._on_preferences),
                               ("import-backup", self._on_import),
                               ("export-backup", self._on_export),
                               ("show-current-task", self._on_show_current),
                               ("show-lists", self._on_show_lists),
                               ("show-archived", self._on_show_archived),
                               ("show-sync", self._on_show_sync),
                               ("show-journey", self._on_show_journey),
                               ("search", self._on_search),
                               ("quit", self._on_quit)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        # show-list('today:TODAY'), show-list('project:<id>') and
        # show-task('<id>'), also over D-Bus for the screenshots.
        for name, callback in (("show-list", self._on_show_list),
                               ("show-task", self._on_show_task)):
            action = Gio.SimpleAction.new(name, GLib.VariantType("s"))
            action.connect("activate", callback)
            self.add_action(action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.preferences", ["<Control>comma"])
        self.set_accels_for_action("win.add-task", ["<Control>n"])
        self.set_accels_for_action("app.search", ["<Control>f"])

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # Pensum's own symbolic icons; also when run from the source tree.
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icons = Path(__file__).resolve().parent.parent / "data" / "icons"
        if icons.is_dir():
            theme.add_search_path(str(icons))
        from pensum import settings
        from pensum.store.files import Files
        self.files = demo_files() if os.environ.get("PENSUM_DEMO") else Files()
        self.settings_store = settings.Store()
        from phosh_toolkit import style
        style.apply(self.settings_store.load().style)

    def do_activate(self):
        from pensum.window import Window
        window = self.props.active_window
        if window is None:
            window = Window(self, self.files, self.settings_store)
            if NIGHTLY:
                window.add_css_class("devel")
        window.present()

    def do_shutdown(self):
        window = self.props.active_window
        if window:
            window.flush()
        Adw.Application.do_shutdown(self)

    def _window(self):
        return self.props.active_window

    def _on_show_list(self, action, value):
        if self._window():
            self._window().show_list_key(value.unpack())

    def _on_show_task(self, action, value):
        if self._window():
            self._window().show_task(value.unpack())

    def _on_search(self, *_):
        if self._window():
            self._window().show_search()

    def _on_show_archived(self, *_):
        if self._window():
            self._window().show_archived()

    def _on_show_sync(self, *_):
        if self._window():
            self._window().show_sync()

    def _on_show_journey(self, *_):
        if self._window():
            self._window().show_journey()

    def _on_show_lists(self, *_):
        if self._window():
            self._window().show_lists()

    def _on_show_current(self, *_):
        window = self._window()
        if window and window.ds.current_task_id():
            window.show_task(window.ds.current_task_id())

    def _on_import(self, *_):
        if self._window():
            from pensum.ui import backup_actions
            backup_actions.import_backup(self._window())

    def _on_export(self, *_):
        if self._window():
            from pensum.ui import backup_actions
            backup_actions.export_backup(self._window())

    def _on_quit(self, *_):
        self.quit()

    def _on_preferences(self, *_):
        window = self._window()
        if window:
            from pensum.preferences import PreferencesDialog
            PreferencesDialog(window).present(window)

    def _on_about(self, *_):
        dialog = Adw.AboutDialog(
            application_name=NAME,
            application_icon=APP_ID,
            version=VERSION_LABEL,
            developer_name="suitably",
            website=REPO_URL,
            issue_url=f"{REPO_URL}/issues",
            license_type=Gtk.License.AGPL_3_0,
            comments="Tasks and time tracking for the phone. Reads and writes "
                     "Super Productivity's backup files. Not affiliated with "
                     "the Super Productivity project.",
        )
        dialog.add_link("Support Development", SUPPORT_URL)
        dialog.present(self._window())


def main(argv):
    # PENSUM_DEBUG=1 logs saves and consistency problems.
    logging.basicConfig(format="pensum: %(name)s: %(message)s")
    if os.environ.get("PENSUM_DEBUG"):
        logging.getLogger("pensum").setLevel(logging.DEBUG)
    return Application().run(argv)
