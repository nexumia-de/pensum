"""A habit of the user's own as a journey (#80; QuestArc
docs/behaviour.md, screen 2a): the quick form. What do you want to do,
after what, how should it grow, how often, its name and what it builds;
one scrolling page with a group per question, nothing focused when it
opens. The journey itself is written by QuestArc's engine
(pensum.game.own); the next page shows its steps before it is kept."""
from gi.repository import Adw, Gtk

from pensum.game import content, engine, own
from pensum.game.sentences import DAY_IDS, DAY_NAMES
from pensum.i18n import _
from pensum.ui.journey.base import JourneySubpage
from pensum.ui.journey.moment_rows import limit


def _combo(title, names):
    return Adw.ComboRow(title=title, model=Gtk.StringList.new(list(names)))


class QuickPage(JourneySubpage):
    def __init__(self, window, anchor_id=None):
        super().__init__(window, _("Your Own Habit"), "journey-quick")
        self.anchor_id = anchor_id
        what = self.group(_("What do you want to do?"),
                          _("In your own words. It completes “I will …”: read, stretch, "
                            "write in my journal."))
        self.action = limit(Adw.EntryRow(title=_("I will …")), own.LIMITS["action"])
        what.add(self.action)
        after = self.group(_("After what?"),
                           _("A moment that already happens in your day. It completes "
                             "“After …”: brushing my teeth."))
        self.anchor = limit(Adw.EntryRow(title=_("After …")), own.LIMITS["anchor"])
        after.add(self.anchor)
        self._grow_group()
        self._often_group()
        last = self.group(_("Name and what it builds"))
        self.name = limit(Adw.EntryRow(title=_("Name of the journey")), own.LIMITS["name"])
        last.add(self.name)
        self.ladders = list(content.ladders())
        self.ladder = _combo(_("It builds"), [content.ladder(n)["title"] for n in self.ladders])
        last.add(self.ladder)
        self.set_main(_("Look at the Steps"), self._preview)

    # --- how it grows -------------------------------------------------------

    def _grow_group(self):
        grow = self.group(_("How should it grow?"),
                          _("Start with a step that is too small to skip."))
        self.measure = _combo(_("Counted in"), (_("Minutes"), _("Pages"), _("Times"),
                                                _("It stays the same")))
        self.first = Adw.SpinRow.new_with_range(1, 1000, 1)
        self.first.set_title(_("First step"))
        self.last = Adw.SpinRow.new_with_range(1, 1000, 1)
        self.last.set_title(_("Last step"))
        self.first.set_value(2)
        self.last.set_value(20)
        self.steps = Adw.EntryRow(title=_("Steps (you can change them)"))
        self.steps.set_input_purpose(Gtk.InputPurpose.NUMBER)
        for row in (self.measure, self.first, self.last, self.steps):
            grow.add(row)
        self.measure.connect("notify::selected", lambda *_a: self._show_grow())
        self.first.connect("notify::value", lambda *_a: self._propose())
        self.last.connect("notify::value", lambda *_a: self._propose())
        self._propose()

    def _same(self):
        return own.MEASURES[self.measure.get_selected()] == "same"

    def _show_grow(self):
        for row in (self.first, self.last, self.steps):
            row.set_visible(not self._same())

    def _propose(self):
        try:
            steps = own.propose(int(self.first.get_value()), int(self.last.get_value()))
        except engine.EngineError:
            steps = [int(self.first.get_value()), int(self.last.get_value())]
        self.steps.set_text(", ".join(str(n) for n in steps))

    def _amounts(self):
        """The numbers of the steps row, as typed; the engine keeps the
        growing ones."""
        found = []
        for part in self.steps.get_text().replace(";", ",").replace(" ", ",").split(","):
            if part.strip().isdigit():
                found.append(int(part))
        return found[:own.MAX_STEPS]

    # --- how often ----------------------------------------------------------

    def _often_group(self):
        often = self.group(_("How often?"))
        self.often = _combo(_("Planned"), (_("Every day"), _("Every 2 days"), _("Every 3 days"),
                                           _("On chosen weekdays")))
        often.add(self.often)
        box = Gtk.Box(spacing=4, homogeneous=True, margin_top=8, margin_bottom=8,
                      margin_start=8, margin_end=8)
        self.days = []
        for name in DAY_NAMES:
            day = _(name)
            button = Gtk.ToggleButton(label=day[:2], tooltip_text=day, height_request=44)
            button.update_property([Gtk.AccessibleProperty.LABEL], [day])
            box.append(button)
            self.days.append(button)
        self.days_row = Adw.PreferencesRow(child=box, activatable=False, visible=False)
        often.add(self.days_row)
        self.often.connect("notify::selected", lambda *_a: self.days_row.set_visible(
            self.often.get_selected() == 3))

    def _schedule(self):
        chosen = self.often.get_selected()
        if chosen in (1, 2):
            return {"type": "everyNDays", "n": chosen + 1}
        if chosen == 3:
            days = [day for day, button in zip(DAY_IDS, self.days) if button.get_active()]
            return {"type": "weekdays", "days": days} if days else None
        return {"type": "daily"}

    # --- the journey --------------------------------------------------------

    def answers(self):
        """The engine's answers, or None with a toast naming what is
        still open."""
        texts = {"action": self.action.get_text().strip(),
                 "anchor": self.anchor.get_text().strip(),
                 "name": self.name.get_text().strip()}
        schedule = self._schedule()
        if not all(texts.values()):
            self.window.toast(_("Say what you want to do, after what, and give it a name."))
            return None
        if schedule is None:
            self.window.toast(_("Choose at least one weekday."))
            return None
        measure = own.MEASURES[self.measure.get_selected()]
        return {**texts, "measure": measure, "schedule": schedule,
                "steps": [] if measure == "same" else self._amounts(),
                "ladder": self.ladders[self.ladder.get_selected()] if self.ladders else None}

    def _preview(self):
        answers = self.answers()
        if answers is None:
            return
        try:
            made = own.quick(answers)
        except engine.EngineError:
            self.window.toast(content.t("ui.error.write"))
            return
        from pensum.ui.journey.quick_preview import QuickPreviewPage
        self.window.nav.push(QuickPreviewPage(self.window, made, self.anchor_id))
