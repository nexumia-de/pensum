"""Starting a journey (QuestArc docs/behaviour.md, screen 3): the moment
it starts from (one of the user's, or a new one in their words), the
user's own reason, optional and never focused when the page opens, and a
self-chosen start day. Starting while another journey runs pauses it."""
import secrets

from gi.repository import Adw, Gtk

from pensum.game import content, engine, moments
from pensum.game.content import t
from pensum.game.sentences import (capitalise, find_stage, first_of_next_month, next_monday,
                                   short_date)
from pensum.ui.journey import plan_check
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.moment_rows import MomentRows


class StartPage(JourneySubpage):
    def __init__(self, window, journey_id, anchor_id=None):
        super().__init__(window, t("ui.start.start"), f"journey-start-{journey_id}")
        self.journey = content.journey(journey_id)
        self.anchor_id = anchor_id  # None: a new moment; "Extend This Moment" names one
        today = window.ds.today()
        self.after = None
        self._moment_group()
        self.chain = self.group(t("ui.moment.tie"), t("ui.moment.tie.hint"))
        self._chain_rows = []
        self._show_chain()
        why = self.group(t("ui.start.why"), t("ui.start.why.private"))
        self.why_row = Adw.EntryRow(title=t(self.journey.get("why") or "ui.start.why"))
        why.add(self.why_row)
        self.plan_rows = plan_check.start_expander(self.group())
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
                          and self._choose_anchor(i))
            row = Adw.ActionRow(title=moments.title(found), activatable_widget=check)
            row.add_prefix(check)
            group.add(row)
        new = Gtk.CheckButton(active=self.anchor_id not in {a["id"] for a in mine}, group=first)
        new.connect("toggled", lambda c: c.get_active() and self._choose_anchor(None))
        row = Adw.ActionRow(title=t("ui.moment.new"), activatable_widget=new)
        row.add_prefix(new)
        group.add(row)
        self.rows = MomentRows(group, words=t(hint["example"]) if hint.get("example") else "")

    def _choose_anchor(self, anchor_id):
        self.anchor_id = anchor_id
        self.after = None
        if hasattr(self, "chain"):
            self._show_chain()

    def _show_chain(self):
        """At a moment where a habit stands, the new step may be tied to that
        step instead of the moment (a chain, `anchorRun`'s `after`; the
        user's choice, never the default, QuestArc design rule 3)."""
        for row in self._chain_rows:
            self.chain.remove(row)
        self._chain_rows = []
        anchor = next((a for a in (self.model.view or {}).get("anchors", [])
                       if self.anchor_id and a.get("id") == self.anchor_id), None)
        steps = []
        for step in (anchor or {}).get("steps", ()):
            stage = find_stage(content.journey(step["journeyId"]), step["stageId"])
            if stage and step.get("state") in ("graduated", "maintained"):
                steps.append((step["runId"], t("ui.anchor.then", anchor=t(stage["plan"]["action"]))))
        self.chain.set_visible(bool(steps))
        first = None
        for run_id, label in [(None, capitalise(t("ui.moment.tie.anchor")))] + steps:
            check = Gtk.CheckButton(group=first, active=run_id is None)
            first = first or check
            check.connect("toggled", lambda c, r=run_id: c.get_active()
                          and setattr(self, "after", r))
            row = Adw.ActionRow(title=label, activatable_widget=check, title_lines=0)
            row.add_prefix(check)
            self.chain.add(row)
            self._chain_rows.append(row)

    def _start(self):
        anchor_id, anchor = self.anchor_id, None
        if anchor_id is None:
            anchor = self.rows.anchor()
            if anchor is None:
                self.window.toast(t("ui.moment.missing"))
                return
            anchor_id = secrets.token_hex(8)
        active = self.model.active()
        start = {"runId": secrets.token_hex(16), "journey": self.journey,
                 "startDay": self.day, "today": self.window.ds.today(),
                 "why": self.why_row.get_text(),
                 "anchor": {"anchorId": anchor_id, **({"after": self.after} if self.after else {})}}
        if active:
            start["activeRunId"] = active["runId"]

        def changes():
            found = engine.action("nameAnchor", {"anchorId": anchor_id, "anchor": anchor}) \
                if anchor else {}
            found.update(engine.action("startJourney", start))
            found.update(self._plan_check(start["runId"]))
            return found
        if self.model.apply(changes, "startJourney"):
            self.back_to_journey()

    def _plan_check(self, run_id):
        """The plan check's answers as one record; none written without an answer."""
        given = plan_check.answers(self.plan_rows)
        return engine.action("checkPlan", run_id, given) if given else {}
