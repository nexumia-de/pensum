"""The places of the Valley for the demo dataset (PENSUM_DEMO=1, never real
tasks): moments with journeys that stand, wait (they started before the
growing one, so it stays the active journey) or run by themselves, as
QuestArc's records tell them (docs/data-model.md §2). `PENSUM_DEMO_VALLEY`
picks 1, 3 (the default), 6 or 6-stacked places; the growing journey of
`pensum.demo` stands at "sitting down at my desk". No GTK."""
import os

from pensum.game import content, records
from pensum.store import dates

SCENARIOS = ("1", "3", "6", "6-stacked")
# In the order of the day; the desk is where the growing journey stands.
MOMENTS = {
    "getting-up": ("getting up", "gentle-morning"),
    "desk": ("sitting down at my desk", "first-things-first"),
    "lunch": ("lunch", "walk-after-lunch"),
    "dinner": ("dinner", "tidy-a-little"),
    "bedtime": ("brushing my teeth", "pages-before-sleep"),
    "evening": ("my evening coffee", "evening-wind-down"),
}
PLACES = {"1": ("desk",), "3": ("getting-up", "desk", "evening"),
          "6": tuple(MOMENTS), "6-stacked": tuple(MOMENTS)}
# Where a second and third thing stand in the stacked scenario: the
# journeys that started at the moment after its first one.
EXTRA = {"desk": ("gentle-morning",), "dinner": ("evening-wind-down", "first-things-first"),
         "bedtime": ("tidy-a-little",)}
# What the first journey of a moment is doing: it ran by itself, it is
# done, or it waits at its first station.
STATE = {"getting-up": "graduated", "lunch": "finished", "dinner": "finished",
         "bedtime": "waiting", "evening": "waiting"}


def scenario():
    name = os.environ.get("PENSUM_DEMO_VALLEY", "3")
    return name if name in SCENARIOS else "3"


def _finished(found, run, journey_id, ends_ago, today, graduated):
    stages = [s["id"] for s in content.journey(journey_id)["stages"]]
    start = ends_ago + 15 * len(stages)
    day = lambda back: dates.shift_day(today, -back)  # noqa: E731
    found[f"run:{run}"] = {"journeyId": journey_id, "journeyVersion": 1, "startDay": day(start)}
    for i, stage in enumerate(stages):
        found[f"stage:{run}:{stage}"] = {"acceptedDay": day(start - 15 * i)}
        found[f"stage-done:{run}:{stage}"] = {"day": day(start - 15 * (i + 1)), "dataFormat": 2}
    found[f"run-end:{run}"] = {"day": day(ends_ago), "reason": "finished"}
    if graduated:
        found[f"graduation:{run}:{stages[-1]}:{day(ends_ago - 3 if ends_ago > 3 else 0)}"] = \
            {"choice": "end"}


def _waiting(found, run, journey_id, today):
    first = content.journey(journey_id)["stages"][0]["id"]
    found[f"run:{run}"] = {"journeyId": journey_id, "journeyVersion": 1,
                           "startDay": dates.shift_day(today, -45)}
    found[f"stage:{run}:{first}"] = {"acceptedDay": dates.shift_day(today, -45)}
    found[f"pause:{run}:{dates.shift_day(today, -40)}"] = {"action": "pause", "source": "user"}


def add(ds, today, name=None):
    """Write the moments, the other journeys and the places' records of
    the scenario; the growing run `demo` is tied to the desk."""
    name = name or scenario()
    found = {}
    for moment in PLACES[name]:
        found[f"anchor:{moment}"] = {"kind": "routine", "words": MOMENTS[moment][0]}
    found["run-anchor:demo"] = {"anchorId": "desk"}
    # The places in the order of the day, as the user placed them.
    for position, moment in enumerate(PLACES[name]):
        found[f"place:{moment}"] = {"position": position}
    for moment in PLACES[name]:
        state = STATE.get(moment)
        journey_id = MOMENTS[moment][1]
        if state is None:
            continue
        run = f"{moment}-1"
        if state == "waiting":
            _waiting(found, run, journey_id, today)
        else:
            _finished(found, run, journey_id, 60, today, state == "graduated")
        found[f"run-anchor:{run}"] = {"anchorId": moment}
    if name == "6-stacked":
        for moment, more in EXTRA.items():
            for k, journey_id in enumerate(more, start=2):
                run = f"{moment}-{k}"
                _finished(found, run, journey_id, 48 - 14 * k, today, False)
                found[f"run-anchor:{run}"] = {"anchorId": moment}
    records.write(ds, found)
