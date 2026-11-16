"""A user's moments (QuestArc anchors, game rules §8) in words: the name
they gave, else "After getting up" or "At 21:30". No GTK."""
from pensum.game.content import t


def title(anchor):
    """The words of an anchor view: its name, else After <words> / At <time>."""
    if anchor.get("name"):
        return anchor["name"]
    if anchor.get("kind") == "time" and anchor.get("time"):
        return t("ui.anchor.at", anchor=anchor["time"])
    if anchor.get("words"):
        return t("ui.anchor.after", anchor=anchor["words"])
    return anchor.get("name") or ""


def anchor(view, anchor_id):
    return next((a for a in view.get("anchors", []) if a.get("id") == anchor_id), None)


def place_title(view, place):
    """A place's name: from its anchor's words (the place's own `name`
    is the user's name, else the bare words)."""
    found = anchor(view, place["anchorId"])
    return title(found) if found else place["name"]
