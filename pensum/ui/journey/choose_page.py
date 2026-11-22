"""Choosing a journey (QuestArc docs/behaviour.md, screen 2): the
journeys with their first step, then a preview with every station as a
plan sentence, its author, and Start This Journey. Below the built-in
journeys: the user's own, the quick form for a new one and importing a
journey file (#80); an own journey's preview exports it, and removes it
while no run uses it."""
from gi.repository import Adw, Gtk

from pensum.game import content, engine, own, records
from pensum.i18n import _
from pensum.game.content import t
from pensum.game.sentences import plan_sentence
from pensum.ui.journey.base import JourneySubpage


class ChoosePage(JourneySubpage):
    """`anchor_id`: "Extend This Moment", the moment is already chosen."""

    def __init__(self, window, anchor_id=None):
        super().__init__(window, t("ui.choose.title"), "journey-choose")
        self.anchor_id = anchor_id
        self._fill()
        self.listen(self._fill)

    def _fill(self):
        self.clear()
        group = self.group()
        for journey in content.builtin():
            group.add(self._row(journey))
        if not (content.own() or own.available()):
            return
        mine = self.group(_("Your Own"))
        for journey in content.own():
            mine.add(self._row(journey))
        if not own.available():
            return
        for title, subtitle, icon, action in (
                (_("Your Own Habit"), _("A few questions make a journey of your habit."),
                 "list-add-symbolic", self._quick),
                (_("Import a Journey File"), "", "document-open-symbolic", self._import)):
            row = Adw.ActionRow(title=title, subtitle=subtitle, activatable=True)
            row.add_prefix(Gtk.Image(icon_name=icon))
            row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
            row.connect("activated", lambda _r, a=action: a())
            mine.add(row)

    def _row(self, journey):
        first = journey["stages"][0]
        lines = [t("ui.choose.stations", n=len(journey["stages"]))]
        if journey.get("author"):
            lines.append(t("ui.journey.author", name=journey["author"]))
        lines.append(plan_sentence(first))
        row = Adw.ActionRow(title=t(journey["title"]), use_markup=False,
                            subtitle=t(journey["description"]) + "\n" + " · ".join(lines[:-1])
                            + "\n" + lines[-1], activatable=True, subtitle_lines=0)
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda _r: self.window.nav.push(
            PreviewPage(self.window, journey["id"], self.anchor_id)))
        return row

    def _quick(self):
        from pensum.ui.journey.quick_page import QuickPage
        self.window.nav.push(QuickPage(self.window, self.anchor_id))

    def _import(self):
        from pensum.ui.journey import own_file
        own_file.import_journey(self.window, lambda journey: self.window.nav.push(
            PreviewPage(self.window, journey["id"], self.anchor_id)))


class PreviewPage(JourneySubpage):
    def __init__(self, window, journey_id, anchor_id=None):
        journey = content.journey(journey_id)
        super().__init__(window, t(journey["title"]), f"journey-preview-{journey_id}")
        self.text(t(journey["description"]))
        if journey.get("author"):
            self.text(t("ui.journey.author", name=journey["author"]), "dimmed", "caption")
        group = self.group(t("ui.preview.stations"))
        for index, stage in enumerate(journey["stages"], 1):
            row = Adw.ActionRow(title=plan_sentence(stage), title_lines=0)
            number = Gtk.Label(label=str(index))
            number.add_css_class("numeric")
            number.add_css_class("dimmed")
            row.add_prefix(number)
            group.add(row)
        self.set_main(t("ui.preview.start"), lambda: self._start(journey_id, anchor_id))
        if own.is_own(journey_id):
            self._own_group(journey)

    def _own_group(self, journey):
        from pensum.ui.journey import own_file
        group = self.group(_("Your Own"))
        for title, action in ((_("Export as a File"),
                               lambda: own_file.export_journey(self.window, journey)),
                              (_("Remove This Journey"), lambda: self._remove(journey))):
            row = Adw.ActionRow(title=title, activatable=True)
            row.connect("activated", lambda _r, a=action: a())
            group.add(row)

    def _remove(self, journey):
        """Only while no run uses it (the engine decides); Undo brings
        the record back."""
        key = own.KEY + journey["id"]
        before = {k: v for k, v in records.load(self.window.ds).items() if k == key}
        try:
            changes = engine.action("forgetJourney", self.model.view or
                                    {"paused": [], "finished": [], "readOnly": []},
                                    journey["id"])
        except engine.EngineError:
            changes = {}
        if not changes:
            self.window.toast(_("A journey you have walked stays."))
            return
        if not self.model.apply(lambda: changes, "forgetJourney"):
            return
        self.window.nav.pop()
        toast = Adw.Toast(title=_("Journey removed"), button_label=t("ui.action.undo"))
        toast.connect("button-clicked", lambda *_a: self.model.apply(lambda: before, "undo"))
        self.window.toasts.add_toast(toast)

    def _start(self, journey_id, anchor_id):
        from pensum.ui.journey.start_page import StartPage
        self.window.nav.push(StartPage(self.window, journey_id, anchor_id))
