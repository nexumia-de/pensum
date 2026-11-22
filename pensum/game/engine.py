"""QuestArc's engine, run through gjs from the GNOME runtime (QuestArc
docs/decisions/engine-in-gjs.md): one request as JSON on stdin, the
answer on stdout. Builds the request from the dataset as it is; the
engine picks the fields it needs. No GTK."""
import json
import logging
import os
import subprocess
import time
from pathlib import Path

from pensum.game import content, own, records
from pensum.store import dates

log = logging.getLogger(__name__)
TIMEOUT_SECONDS = 20


class EngineError(Exception):
    """gjs is missing or the engine failed; the message says which."""


def gjs_command():
    return os.environ.get("PENSUM_GJS") or "gjs"


def time_zone():
    """The IANA name of the local zone (TZ, then /etc/localtime)."""
    name = os.environ.get("TZ", "").lstrip(":")
    if name and "/" in name and not name.startswith("/"):
        return name
    try:
        target = os.readlink("/etc/localtime")
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    try:
        text = Path("/etc/timezone").read_text().strip()
        if text:
            return text
    except OSError:
        pass
    return "UTC"


def _archived(ds):
    found = []
    for name in ("archiveYoung", "archiveOld"):
        entities = ((ds.data.get(name) or {}).get("task") or {}).get("entities") or {}
        found += list(entities.values())
    return found


def host_input(ds, now=None):
    """The engine's host input (QuestArc data model §1) from the dataset."""
    now = now or dates.now_ms()
    cfgs = ds.data.get("taskRepeatCfg") or {}
    found = records.load(ds)
    content.set_own(own.journeys(found))
    return {
        "day": {"todayStr": ds.today(now),
                "startOfNextDayDiffMs": dates.day_offset_ms(ds.config),
                "timeZone": time_zone()},
        "live": list(ds.tasks.values()),
        "archived": _archived(ds),
        "repeatCfgs": [cfgs.get("entities", {})[i] for i in cfgs.get("ids", [])
                       if i in cfgs.get("entities", {})],
        "records": found,
        "journeys": content.builtin(),
    }


def run(request):
    """Run one request (a dict, or JSON text already made) and return the
    parsed answer."""
    payload = request if isinstance(request, str) else json.dumps(request)
    cli = content.cli_path()
    if cli is None:
        raise EngineError("QuestArc's engine is not installed")
    started = time.monotonic()
    try:
        # gjs prints in the locale's character set: with a locale that is
        # not installed (a Flatpak without its language pack) umlauts came
        # back as "?". The engine takes its language from the request, so
        # its own locale is fixed to UTF-8.
        done = subprocess.run([gjs_command(), "-m", str(cli)], input=payload,
                              capture_output=True, text=True, encoding="utf-8",
                              timeout=TIMEOUT_SECONDS, check=False,
                              env={**os.environ, "LC_ALL": "C.UTF-8"})
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EngineError(f"gjs could not run the engine: {error}") from error
    if done.returncode != 0:
        raise EngineError(f"the engine failed: {done.stderr.strip()[:300]}")
    log.debug("engine answered in %d ms", (time.monotonic() - started) * 1000)
    return json.loads(done.stdout)


def evaluate(ds, now=None):
    """The game view for the dataset."""
    return run({"evaluateHost": host_input(ds, now)})


def evaluate_request(ds, now=None):
    """The evaluation request as JSON text, made from the dataset now (so
    a thread can run it while the dataset changes)."""
    return json.dumps({"evaluateHost": host_input(ds, now)})


def evaluate_and_diff(ds, before, now=None, request=None):
    """(view, events since `before`) in two engine runs; no events
    without an earlier view. `request` is a prepared evaluate_request."""
    view = run(request or evaluate_request(ds, now))
    if before is None:
        return view, []
    return view, run({"diff": {"before": before, "after": view}})


def action(name, *args):
    """The record changes of a user action (QuestArc actions.ts)."""
    answer = run({"action": {"name": name, "args": list(args)}})
    if isinstance(answer, dict) and set(answer) == {"error"}:
        raise EngineError(answer["error"])
    return answer


class Refused(EngineError):
    """The engine's last check refused a write (QuestArc data model §2,
    data format): it touches a read-only run or a kind this engine does
    not write. Nothing was written; `keys` names the refused records."""

    def __init__(self, keys):
        super().__init__(f"{len(keys)} record change(s) refused")
        self.keys = list(keys)


def guard_write(view, changes):
    """The changes the engine allows (`guardWrite`): all of them, or
    Refused when one touches a run of a newer engine or a kind this
    engine does not write, so a write is never half done."""
    if not changes:
        return {}
    answer = run({"guardWrite": {"view": view or {"readOnly": []}, "changes": changes}})
    if not isinstance(answer, dict) or "changes" not in answer:
        raise EngineError("the engine gave no answer to guardWrite")
    if answer.get("refused"):
        raise Refused(answer["refused"])
    return answer["changes"]


def valley_layout(sides, things, width=360, height=720):
    """The Valley's geometry from the engine (QuestArc journey design,
    "The place piece"): the path and, per place, its slot, boxes for every
    thing, bay, doorstep, name box and joints, in units of a scene
    `width` wide. Nothing is laid out here. `things` is how many things
    stand at each place (1 to 3)."""
    return run({"valley": {"sides": list(sides), "things": list(things),
                           "width": width, "height": height}})
