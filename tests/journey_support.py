"""Helpers of the journey flow tests: a window on a dataset, the text and
buttons below a widget, and the check that the dataset stays valid.
Imported only after the tests checked for a display."""
import json
import os

import gi
import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk  # noqa: E402

from pensum import settings  # noqa: E402
from pensum.game import content, engine, records  # noqa: E402
from pensum.store import backup, defaults, validate  # noqa: E402
from pensum.store.dataset import Dataset  # noqa: E402
from pensum.store.files import Files  # noqa: E402

needs_engine = pytest.mark.skipif(
    not content.available() and not os.environ.get("PENSUM_REQUIRE_ENGINE"),
    reason="needs gjs and QuestArc's engine (PENSUM_QUESTARC_DIR, PENSUM_GJS)")


def iterate(times=20):
    ctx = GLib.MainContext.default()
    for _ in range(times):
        while ctx.pending():
            ctx.iteration(False)


def labels(widget):
    """The text of every label, row title and status page below a widget."""
    found = []
    for name in ("get_label", "get_title", "get_subtitle", "get_description"):
        value = getattr(widget, name, None)
        if callable(value) and not isinstance(widget, Gtk.Window):
            try:
                text = value()
            except TypeError:
                text = None
            if isinstance(text, str) and text:
                found.append(text)
    child = widget.get_first_child()
    while child:
        found += labels(child)
        child = child.get_next_sibling()
    return found


def buttons(widget):
    found = [widget] if isinstance(widget, Gtk.Button) else []
    child = widget.get_first_child()
    while child:
        found += buttons(child)
        child = child.get_next_sibling()
    return found


def button(widget, label):
    return next(b for b in buttons(widget) if b.get_label() == label)


def window_with(app, tmp_path, ds):
    from pensum.window import Window
    files = Files(tmp_path / "data")
    files.save(ds)
    window = Window(app, files, settings.Store(tmp_path / "settings.json"))
    window.present()
    iterate()
    window.journeys.refresh_now()
    return window


def fresh():
    from pensum.store import dates
    return Dataset(defaults.fresh_dataset(dates.now_ms()))


def started(ds, journey_id="gentle-morning", run_id="r", start=None):
    journey = content.journey(journey_id)
    records.write(ds, engine.action("startJourney", {
        "runId": run_id, "journey": journey, "startDay": start or ds.today()}))
    return journey


def stored(window):
    """The dataset as it would be written, without the save's timestamp."""
    window.flush()
    data = backup.read(window.files.path)
    return json.dumps(data, sort_keys=True)


def valid(window):
    window.flush()
    assert validate.problems(backup.read(window.files.path)) == []
