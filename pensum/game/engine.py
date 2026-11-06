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

from pensum.game import content, records
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
    return {
        "day": {"todayStr": ds.today(now),
                "startOfNextDayDiffMs": dates.day_offset_ms(ds.config),
                "timeZone": time_zone()},
        "live": list(ds.tasks.values()),
        "archived": _archived(ds),
        "repeatCfgs": [cfgs.get("entities", {})[i] for i in cfgs.get("ids", [])
                       if i in cfgs.get("entities", {})],
        "records": records.load(ds),
        "journeys": content.journeys(),
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
        done = subprocess.run([gjs_command(), "-m", str(cli)], input=payload,
                              capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
                              check=False)
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
