"""The fields that say when a moment is (QuestArc docs/behaviour.md,
screen 0a): "After …" with the routine in the user's words (at most 40
characters), or a fixed time. Used where a journey starts and where a
moment is named or changed. Nothing is focused when a page opens."""
import re

from gi.repository import Adw

from pensum.game.content import t

MAX_WORDS = 40
TIME = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def limit(row, length):
    """Cut what is typed or pasted past `length` characters (an
    Adw.EntryRow has no maximum length of its own)."""
    def on_changed(entry):
        text = entry.get_text()
        if len(text) > length:
            entry.set_text(text[:length])
            entry.set_position(length)
    row.connect("changed", on_changed)
    return row


class MomentRows:
    """An "After …" row and an "At a fixed time" row in `group`; `anchor()`
    gives the engine's `{kind, words | time}`, or None for neither."""

    def __init__(self, group, words="", time=""):
        self.routine = limit(Adw.EntryRow(title=t("ui.moment.routine"), text=words), MAX_WORDS)
        self.time = limit(Adw.EntryRow(title=t("ui.moment.time") + " (24 h, like 21:30)",
                                       text=time), 5)
        group.add(self.routine)
        group.add(self.time)

    def anchor(self):
        """A fixed time wins when it reads as a time; else the words."""
        hour_minute = TIME.match(self.time.get_text().strip())
        if hour_minute:
            return {"kind": "time", "time": f"{int(hour_minute[1]):02d}:{hour_minute[2]}"}
        words = self.routine.get_text().strip()
        return {"kind": "routine", "words": words} if words else None
