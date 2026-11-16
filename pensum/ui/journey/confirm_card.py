"""A journey from before anchors asks once whether its moment is the
user's (QuestArc docs/behaviour.md, screen 0): "Yes, That Is It" writes
the suggested words as the moment, "Change the Words" lets the user say
their own. Nothing depends on the answer; until then the moment has no
place in the Valley."""
import secrets

from gi.repository import Gtk

from pensum.game import content
from pensum.game.content import t


def suggested(group):
    """The engine's `{kind, words | time}` for a group of runs that have
    no anchor yet: a time if the journey's hint names one, else its words."""
    if group.get("kind") == "time" and group.get("time"):
        return {"kind": "time", "time": group["time"]}
    words = group.get("words")
    if not words:
        journey = content.journey(group.get("suggest")) or {}
        words = t((journey.get("anchor") or {}).get("example", "")) or ""
    return {"kind": "routine", "words": words}


def confirm_cards(page):
    """One card for each group of runs without an anchor."""
    view = page.model.view
    cards = []
    for group in view.get("anchors", []):
        if group.get("id") is not None or not group.get("suggest"):
            continue
        cards.append(_card(page, group))
    return cards


def _confirm(page, group, anchor):
    page.model.action("confirmAnchor", page.model.view, {
        "journeyId": group["suggest"], "anchorId": secrets.token_hex(8), "anchor": anchor})


def _card(page, group):
    from pensum.ui.journey.moment_page import MomentPage
    words = suggested(group)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, css_classes=["card"])
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12,
                    margin_bottom=12, margin_start=12, margin_end=12)
    box.append(inner)
    inner.append(Gtk.Label(label=t("ui.anchor.confirm"), xalign=0, wrap=True))
    shown = words.get("time") or words.get("words")
    inner.append(Gtk.Label(label=f"“{shown}”", xalign=0, css_classes=["title-4"], wrap=True))
    row = Gtk.Box(spacing=8, homogeneous=True)
    yes = Gtk.Button(label=t("ui.anchor.confirm.yes"), css_classes=["suggested-action",
                                                                  "pensum-bar-button"])
    yes.connect("clicked", lambda *_: _confirm(page, group, words))
    change = Gtk.Button(label=t("ui.anchor.confirm.change"), css_classes=["pensum-bar-button"])
    change.connect("clicked", lambda *_: page.window.nav.push(MomentPage(
        page.window, lambda anchor, name: _confirm(page, group, anchor), anchor=words,
        title=t("ui.anchor.confirm.change"))))
    row.append(yes)
    row.append(change)
    inner.append(row)
    return box
