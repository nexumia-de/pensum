"""A moment in words (QuestArc docs/behaviour.md, screen 0a): when it is
("After …" or a fixed time) and, optionally, a name for its place.
**Save** gives both to `on_save(anchor, name)`; without words or a time
nothing is saved."""
from gi.repository import Adw

from pensum.game.content import t
from pensum.i18n import _
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.moment_rows import MAX_WORDS, MomentRows, limit


class MomentPage(JourneySubpage):
    def __init__(self, window, on_save, anchor=None, name="", title=None):
        super().__init__(window, title or t("ui.moment.change"), "journey-moment")
        self.on_save = on_save
        anchor = anchor or {}
        when = self.group(t("ui.moment.when"), t("ui.moment.private"))
        self.rows = MomentRows(when, words=anchor.get("words", ""), time=anchor.get("time", ""))
        naming = self.group(t("ui.moment.name"), t("ui.moment.name.hint"))
        self.name_row = limit(Adw.EntryRow(title=t("ui.moment.name"), text=name), MAX_WORDS)
        naming.add(self.name_row)
        self.text(t("ui.moment.tasks"), "dimmed", "caption")
        self.set_main(_("Save"), self._save)

    def _save(self):
        anchor = self.rows.anchor()
        if anchor is None:
            self.window.toast(t("ui.moment.missing"))
            return
        self.window.nav.pop()
        self.on_save(anchor, self.name_row.get_text().strip())
