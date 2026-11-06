"""Starting a journey (QuestArc docs/behaviour.md, screen 3): the user's
own reason, optional and never focused when the page opens, and a
self-chosen start day. Starting while another journey runs pauses it."""
import secrets

from gi.repository import Adw, Gtk

from pensum.game import content
from pensum.game.content import t
from pensum.game.sentences import first_of_next_month, next_monday, short_date
from pensum.ui.journey.base import JourneySubpage


class StartPage(JourneySubpage):
    def __init__(self, window, journey_id):
        super().__init__(window, t("ui.start.start"), f"journey-start-{journey_id}")
        self.journey = content.journey(journey_id)
        today = window.ds.today()
        why = self.group(t("ui.start.why"), t("ui.start.why.private"))
        self.why_row = Adw.EntryRow(title=t(self.journey.get("why") or "ui.start.why"))
        why.add(self.why_row)
        when = self.group(t("ui.start.when"))
        self.day = today
        first = None
        for label, day in ((t("ui.start.today"), today),
                           (t("ui.start.monday", date=short_date(next_monday(today))),
                            next_monday(today)),
                           (t("ui.start.month", date=short_date(first_of_next_month(today))),
                            first_of_next_month(today))):
            check = Gtk.CheckButton(active=day == today, group=first)
            first = first or check
            check.connect("toggled", lambda c, d=day: c.get_active() and setattr(self, "day", d))
            row = Adw.ActionRow(title=label, activatable_widget=check)
            row.add_prefix(check)
            when.add(row)
        active = self.model.current()
        label = t("ui.start.start")
        if active:
            self.text(t("ui.start.pauses", title=t(active[1]["title"])), "dimmed")
            label = t("ui.start.pause-and-start")
        self.set_main(label, self._start)

    def _start(self):
        active = self.model.active()
        changes = {"runId": secrets.token_hex(16), "journey": self.journey,
                   "startDay": self.day, "today": self.window.ds.today(),
                   "why": self.why_row.get_text()}
        if active:
            changes["activeRunId"] = active["runId"]
        self.model.action("startJourney", changes)
        self.back_to_journey()
