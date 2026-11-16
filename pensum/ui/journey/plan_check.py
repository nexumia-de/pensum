"""The optional plan check (QuestArc docs/behaviour.md, screens 3 and 3b;
design rule 6): wish, best outcome, main obstacle and the plan for it,
in the user's own words, none required, none focused when the page
opens, at most 160 characters each. On the start page the rows sit in a
collapsed expander; from the journey's menu they are their own page,
filled with what is stored, and **Save** rewrites the record through the
engine's `checkPlan` (every field empty withdraws it). Only the plan for
the obstacle comes back, in the hard-week hint and a station's details."""
from gi.repository import Adw

from pensum.game.content import t
from pensum.ui.journey.base import JourneySubpage

FIELDS = ("wish", "outcome", "obstacle", "plan")
LIMIT = 160  # QuestArc words.ts PLAN_CHECK_LIMIT; the engine trims as well


def entry_rows(add, stored=None):
    """One entry row per question, added with `add`; returns name → row."""
    rows = {}
    for name in FIELDS:
        row = Adw.EntryRow(title=t(f"ui.check.{name}"))
        row.set_text(((stored or {}).get(name) or "")[:LIMIT])
        row.connect("changed", lambda r: len(r.get_text()) > LIMIT
                    and r.set_text(r.get_text()[:LIMIT]))
        add(row)
        rows[name] = row
    return rows


def answers(rows):
    return {name: row.get_text().strip() for name, row in rows.items()
            if row.get_text().strip()}


def start_expander(group):
    """The collapsed "Plan check (optional)" on the start page."""
    expander = Adw.ExpanderRow(title=t("ui.check.summary"), subtitle=t("ui.check.intro"),
                               subtitle_lines=0)
    group.add(expander)
    return entry_rows(expander.add_row)


class PlanCheckPage(JourneySubpage):
    def __init__(self, window):
        super().__init__(window, t("ui.check.title"), "journey-plan-check")
        run = self.model.active()
        if not run:
            self.text(t("ui.error.gone"))
            return
        self.run_id = run["runId"]
        group = self.group(None, t("ui.check.intro"))
        self.rows = entry_rows(group.add, run.get("planCheck"))
        self.set_main(t("ui.check.save"), self._save)

    def _save(self):
        if self.model.action("checkPlan", self.run_id, answers(self.rows)):
            self.window.nav.pop()
