"""The calm page of a read-only journey (QuestArc docs/behaviour.md,
screen 4; data model §2): the active journey was continued with a newer
QuestArc, or its journey (version) is not here. Its title and one
sentence instead of progress; no main action, no Pause or End, and
nothing is written for it (the engine's guard refuses it as well)."""
from gi.repository import Adw

from pensum.game import content
from pensum.game.content import t


def title(read_only):
    journey = content.journey(read_only.get("journeyId"))
    return t(journey["title"]) if journey else t("ui.read-only.title")


def text(read_only):
    return t("ui.read-only.newer" if read_only.get("reason") == "newer-format"
             else "ui.read-only.missing")


def status_page(read_only):
    page = Adw.StatusPage(icon_name="mark-location-symbolic", title=title(read_only),
                          description=text(read_only), hexpand=True, vexpand=True)
    page.add_css_class("pensum-journey-read-only")
    return page
