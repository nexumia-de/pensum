"""The steps of a journey from the quick form before it is kept (#80):
every step as its plan sentence, the engine's kind hints, and **Keep
This Journey**, which writes the `journey:<id>` record after the
engine's journey checker and goes on to starting it."""
from gi.repository import Adw, Gtk

from pensum.game import content, engine, own
from pensum.game.content import t
from pensum.i18n import _
from pensum.ui.journey.base import JourneySubpage


def keep(window, journey):
    """Keep a journey file as the user's own; True when it was written.
    An error of the journey checker is told and nothing is written."""
    try:
        changes, problems = own.keep(journey)
    except engine.EngineError:
        window.toast(content.t("ui.error.write"))
        return False
    if own.errors(problems) or not changes:
        window.toast(_("This journey cannot be kept: {reason}").format(
            reason=(own.errors(problems) or [{"message": "?"}])[0].get("message", "?")))
        return False
    return window.journeys.apply(lambda: changes, "keepJourney")


class QuickPreviewPage(JourneySubpage):
    def __init__(self, window, made, anchor_id=None):
        journey = made["journey"]
        texts = (journey.get("texts") or {}).get("en") or {}
        super().__init__(window, texts.get(journey["title"]) or _("Your Own Habit"),
                         "journey-quick-preview")
        self.journey, self.anchor_id = journey, anchor_id
        for hint in made.get("hints") or ():
            self.text(t(hint), "dimmed")
        group = self.group(t("ui.preview.stations"))
        for index, sentence in enumerate(own.plan_sentences(journey), 1):
            row = Adw.ActionRow(title=sentence, title_lines=0, use_markup=False)
            number = Gtk.Label(label=str(index))
            number.add_css_class("numeric")
            number.add_css_class("dimmed")
            row.add_prefix(number)
            group.add(row)
        problems = own.errors(made.get("problems") or ())
        if problems:
            self.text(_("This journey cannot be kept: {reason}").format(
                reason=problems[0].get("message", "?")), "dimmed")
        else:
            self.set_main(_("Keep This Journey"), self._keep)

    def _keep(self):
        if not keep(self.window, self.journey):
            return
        from pensum.ui.journey.quick_page import QuickPage
        from pensum.ui.journey.start_page import StartPage
        nav = self.window.nav
        start = StartPage(self.window, self.journey["id"], self.anchor_id)
        stack = nav.get_navigation_stack()
        pages = [stack.get_item(i) for i in range(stack.get_n_items())]
        nav.replace([p for p in pages if not isinstance(p, (QuickPage, QuickPreviewPage))]
                    + [start])
