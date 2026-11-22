"""The break reminder as Super Productivity counts it (read at commit
9980fd76, `take-a-break.service.ts`, `work-context.service.ts`,
`default-global-config.const.ts`):

- Time tracked on a task adds to "working without a break"; more than
  10 minutes with no task tracked resets it, and so does taking the
  break.
- The reminder comes once that time is over
  `globalConfig.takeABreak.takeABreakMinWorkingTime` (60 min) while
  `isTakeABreakEnabled` (default on) and no snooze runs;
  snoozing waits `takeABreakSnoozeTime` (15 min).
- A break that was taken is counted on the active list's day in
  `timeTracking.<project|tag>.<id>.<day>`: `b` one more, `bt` plus its
  length (`addToBreakTimeForActiveContext`).
No GTK; the counter is not stored (Super Productivity keeps it in
memory too)."""
MINUTE = 60 * 1000
RESET_AFTER = 10 * MINUTE  # BREAK_TRIGGER_DURATION
DEFAULTS = {"isTakeABreakEnabled": True, "takeABreakMinWorkingTime": 60 * MINUTE,
            "takeABreakSnoozeTime": 15 * MINUTE}


def config(cfg):
    found = cfg.get("takeABreak") or {}
    return {k: found.get(k, v) if found.get(k) is not None else v for k, v in DEFAULTS.items()}


class Counter:
    """Working time without a break, fed once per second (or per tick)."""

    def __init__(self):
        self.worked = 0
        self.untracked = 0
        self.snoozed_until = 0

    def tick(self, ms, tracking):
        if tracking:
            self.worked += ms
            self.untracked = 0
            return
        before = self.untracked
        self.untracked += ms
        if before <= RESET_AFTER < self.untracked:
            self.reset()

    def reset(self):
        self.worked = 0

    def snooze(self, now, cfg):
        self.snoozed_until = now + config(cfg)["takeABreakSnoozeTime"]

    def due(self, now, cfg):
        c = config(cfg)
        return (bool(c["isTakeABreakEnabled"]) and self.worked > c["takeABreakMinWorkingTime"]
                and now >= self.snoozed_until)


def _key(context):
    """timeTracking's (kind, id) of a list: Today is the tag TODAY."""
    if context.kind == "project":
        return "project", context.id
    if context.kind == "today":
        return "tag", "TODAY"
    if context.kind == "tag":
        return "tag", context.id
    return None


def add_break(ds, context, day, duration_ms):
    key = _key(context)
    if key is None or duration_ms <= 0:
        return False
    days = ds.data["timeTracking"].setdefault(key[0], {}).setdefault(key[1], {})
    entry = days.setdefault(day, {})
    entry["b"] = (entry.get("b") or 0) + 1
    entry["bt"] = (entry.get("bt") or 0) + int(duration_ms)
    return True


def breaks_on(ds, day):
    """(number, ms) of breaks on a day over all lists."""
    count = total = 0
    for kind in ("project", "tag"):
        for days in (ds.data["timeTracking"].get(kind) or {}).values():
            entry = days.get(day) or {}
            count += entry.get("b") or 0
            total += entry.get("bt") or 0
    return count, total
