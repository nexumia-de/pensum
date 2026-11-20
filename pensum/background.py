"""Asking the desktop to let Day Planner run without a window and start
with the session (the Background portal), so reminders come while it is
closed (docs/reminders.md). Only inside the Flatpak, where the portal
knows how to start the app; elsewhere nothing is asked. The answer is not
awaited: without the permission reminders still come while the app runs."""
import logging
import os

from gi.repository import Gio, GLib

log = logging.getLogger(__name__)
REASON = "Show reminders for your tasks"


def in_flatpak():
    return os.path.exists("/.flatpak-info")


def request(autostart):
    """Ask for background running; `autostart` adds or removes the start
    with the session (as a service, without a window)."""
    if not in_flatpak():
        return False
    options = {"reason": GLib.Variant("s", REASON),
               "autostart": GLib.Variant("b", bool(autostart)),
               "commandline": GLib.Variant("as", ["pensum", "--gapplication-service"]),
               "dbus-activatable": GLib.Variant("b", False)}
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
                 "org.freedesktop.portal.Background", "RequestBackground",
                 GLib.Variant("(sa{sv})", ("", options)), None,
                 Gio.DBusCallFlags.NONE, -1, None, None)
    except GLib.Error as error:
        log.warning("background portal: %s", error.message)
        return False
    return True
