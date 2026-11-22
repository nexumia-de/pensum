"""The day's evaluation and focus sessions as Super Productivity keeps
them: the slice `metric`, one entity per day with the day string as id
(read at commit 9980fd76, `metric.model.ts`, `metric.reducer.ts`,
`evaluation-sheet`, `reflection-note`).

- A day without an entity reads as `{id, focusSessions: [],
  remindTomorrow: false, reflections: []}` (`DEFAULT_METRIC_FOR_DAY`);
  writing creates it with those fields first (upsert).
- `impactOfWork` 1-4, `energyCheckin` 1-3.
- The reflection is `reflections[0]`: `{text, created}` with the text
  trimmed; an empty text writes `reflections: []`; `created` stays from
  the first save.
- A finished focus session appends its duration in ms to
  `focusSessions` (`logFocusSession`); zero or less writes nothing.
No GTK."""
from pensum.store import dates

DEFAULT_FOR_DAY = {"focusSessions": [], "remindTomorrow": False, "reflections": []}
IMPACT = range(1, 5)
ENERGY = range(1, 4)


def _slice(ds):
    return ds.data.setdefault("metric", {"ids": [], "entities": {}})


def for_day(ds, day):
    """The day's metric as Super Productivity reads it (a copy)."""
    found = _slice(ds)["entities"].get(day)
    if found is None:
        return {"id": day, **DEFAULT_FOR_DAY, "focusSessions": [], "reflections": []}
    return {**found, "focusSessions": list(found.get("focusSessions") or []),
            "reflections": list(found.get("reflections") or [])}


def _upsert(ds, day, changes):
    state = _slice(ds)
    entity = state["entities"].get(day)
    if entity is None:
        entity = {"id": day, **DEFAULT_FOR_DAY, "focusSessions": [], "reflections": []}
        state["entities"][day] = entity
        state["ids"].append(day)
    entity.update(changes)
    return entity


def set_impact(ds, day, value):
    if value not in IMPACT:
        raise ValueError(value)
    _upsert(ds, day, {"impactOfWork": value})


def set_energy(ds, day, value):
    if value not in ENERGY:
        raise ValueError(value)
    _upsert(ds, day, {"energyCheckin": value})


def reflection(ds, day):
    found = for_day(ds, day)["reflections"]
    return (found[0].get("text") or "") if found else ""


def set_reflection(ds, day, text, now=None):
    trimmed = (text or "").strip()
    if trimmed == reflection(ds, day):
        return False
    existing = for_day(ds, day)["reflections"]
    created = existing[0].get("created") if existing else None
    value = [{"text": trimmed, "created": created or now or dates.now_ms()}] if trimmed else []
    _upsert(ds, day, {"reflections": value})
    return True


def log_focus_session(ds, day, duration_ms):
    duration_ms = int(duration_ms)
    if duration_ms <= 0:
        return False
    entity = _upsert(ds, day, {})
    entity["focusSessions"] = list(entity.get("focusSessions") or []) + [duration_ms]
    return True
