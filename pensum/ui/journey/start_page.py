"""Starting a journey (QuestArc docs/behaviour.md, screen 3): the moment
it starts from (one of the user's, or a new one in their words), the
user's own reason, optional and never focused when the page opens, and a
self-chosen start day. Starting while another journey runs pauses it."""
import secrets

from gi.repository import Adw, Gtk

from pensum.game import content, engine, moments
from pensum.game.content import t
from pensum.game.sentences import first_of_next_month, next_monday, short_date
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.moment_rows import MomentRows


class StartPage(JourneySubpage):
    def __init__(self, window, journey_id, anchor_id=None):
        super().__init__(window, t("ui.start.start"), f"journey-start-{journey_id}")
        self.journey = content.journey(journey_id)
        self.anchor_id = anchor_id  # None: a new moment; "Extend This Moment" names one
        today = window.ds.today()
        self._moment_group()
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

    def _moment_group(self):
        """Your moment: the user's own as options, then a new one with
        the two fields of "Change this moment", filled with the journey's
        example words."""
        hint = self.journey.get("anchor") or {}
        group = self.group(t("ui.moment.title"), t("ui.moment.hint", moment=t(
            hint.get("moment") or "ui.moment.any")))
        mine = [a for a in (self.model.view or {}).get("anchors", []) if a.get("id")]
        if self.anchor_id not in {a["id"] for a in mine}:
            self.anchor_id = None
        first = None
        for found in mine:
            check = Gtk.CheckButton(group=first, active=found["id"] == self.anchor_id)
            first = first or check
            check.connect("toggled", lambda c, i=found["id"]: c.get_active()
                          and setattr(self, "anchor_id", i))
            row = Adw.ActionRow(title=moments.title(found), activatable_widget=check)
            row.add_prefix(check)
            group.add(row)
        new = Gtk.CheckButton(active=self.anchor_id not in {a["id"] for a in mine}, group=first)
        new.connect("toggled", lambda c: c.get_active() and setattr(self, "anchor_id", None))
        row = Adw.ActionRow(title=t("ui.moment.new"), activatable_widget=new)
        row.add_prefix(new)
        group.add(row)
        self.rows = MomentRows(group, words=t(hint["example"]) if hint.get("example") else "")

    def _start(self):
        anchor_id, changes = self.anchor_id, {}
        if anchor_id is None:
            anchor = self.rows.anchor()
            if anchor is None:
                self.window.toast(t("ui.moment.missing"))
                return
            anchor_id = secrets.token_hex(8)
            changes = engine.action("nameAnchor", {"anchorId": anchor_id, "anchor": anchor})
        active = self.model.active()
        start = {"runId": secrets.token_hex(16), "journey": self.journey,
                 "startDay": self.day, "today": self.window.ds.today(),
                 "why": self.why_row.get_text(), "anchor": {"anchorId": anchor_id}}
        if active:
            start["activeRunId"] = active["runId"]
        try:
            changes = dict(changes, **engine.action("startJourney", start))
        except engine.EngineError:
            self.window.toast("Can't save this. Please try again.")
            return
        self.model.write(changes)
        self.back_to_journey()
