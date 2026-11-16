"""The card after a long break (QuestArc docs/behaviour.md, flow D;
design rule 14): nothing counted for 14 days. One calm greeting, the
user's own reason and three equal outlined choices, each with a line
that says what it does; none is suggested. **Carry On** and **Call It a
Pause** write at once (`carryOn`, `callItAPause`); **Start Smaller**
opens its own page (`smaller_page.py`)."""
from gi.repository import Gtk

from pensum.game.content import t
from pensum.game.sentences import short_date


def _label(text, *classes):
    return Gtk.Label(label=text, xalign=0, wrap=True, css_classes=list(classes))


def come_back_card(page, run, journey):
    model = page.model
    today = model.view["todayStr"]
    come_back = run["comeBack"]
    smaller = next((s for s in journey["stages"] if s["id"] == come_back.get("smaller")), None)
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card",
                   "pensum-journey-card", "pensum-journey-comeback"])
    card.update_property([Gtk.AccessibleProperty.LABEL], [t("ui.comeback.title")])
    card.append(_label(t("ui.comeback.title"), "title-4"))
    card.append(_label(t("ui.comeback.text")))
    if run.get("why"):
        card.append(_label(t("ui.card.why", why=run["why"]), "pensum-journey-why"))

    def choice(label, words, on_click):
        button = Gtk.Button(label=label, css_classes=["pensum-bar-button"], margin_top=4)
        button.connect("clicked", lambda *_: on_click())
        card.append(button)
        card.append(_label(words, "caption", "dimmed"))
    choice(t("ui.comeback.carry-on"), t("ui.comeback.carry-on.text"),
           lambda: model.action("carryOn", run, today))
    choice(t("ui.comeback.pause"),
           t("ui.comeback.pause.text", date=short_date(come_back.get("from") or today)),
           lambda: model.action("callItAPause", run, today))
    if smaller:
        choice(t("ui.comeback.smaller"),
               t("ui.comeback.smaller.text", action=t(smaller["plan"]["action"])),
               page.show_smaller)
    return card
