"""**Pair it with** (QuestArc behaviour, flow B step 6 and screen 5;
design rule 7): one optional field, never focused when the page opens,
for something the user enjoys and saves for this step. While they type,
`on_preview` gets the words for the plan sentence; leaving the field or
pressing Enter writes them through the engine's `pairStage` (an empty
field withdraws the pairing). Nothing is counted or shown for it."""
from gi.repository import Adw, Gtk

from pensum.game.content import t

LIMIT = 60  # QuestArc words.ts PAIR_LIMIT; the engine trims as well


def pair_group(page, run, stage_id, current, on_preview=None):
    group = page.group(t("ui.pair.label"), t("ui.pair.hint"))
    row = Adw.EntryRow(title=t("ui.pair.label"), show_apply_button=True)
    row.set_text(current or "")
    row.add_css_class("pensum-journey-pair")
    saved = [current or ""]

    def save(*_):
        text = row.get_text()[:LIMIT]
        if text.strip() == saved[0].strip():
            return
        saved[0] = text
        page.model.action("pairStage", run["runId"], stage_id, text)

    def changed(*_):
        if len(row.get_text()) > LIMIT:
            row.set_text(row.get_text()[:LIMIT])
            return
        if on_preview:
            on_preview(row.get_text().strip() or None)
    row.connect("apply", save)
    row.connect("entry-activated", save)
    row.connect("changed", changed)
    focus = Gtk.EventControllerFocus()
    focus.connect("leave", save)
    row.add_controller(focus)
    group.add(row)
    return row
