"""Focus sessions as Super Productivity runs them (read at commit
9980fd76, `focus-mode.model.ts`, `focus-mode-strategies.ts`,
`focus-mode.effects.ts`):

- **Pomodoro**: a session of `globalConfig.pomodoro.duration`, then a
  break; after every `cyclesBeforeLongerBreak`-th session the longer
  break. The next session starts after the break.
- **Flowtime**: counts up; when ended, a break only if
  `globalConfig.flowtime.isBreakEnabled`: `breakPercentage` of the work
  (at least one minute) in mode `ratio`, or the duration of the first
  rule with `minDuration <= work < maxDuration` in mode `rule`.
- **Countdown**: a chosen length (25 min by default), shortened to the
  task's remaining estimate rounded up to whole minutes; no break.

Every finished session logs its length in `metric.focusSessions`
(pensum.store.metric). `globalConfig.focusMode.isPauseTrackingDuringBreak`
(default true) stops tracking during breaks. The session itself is not
part of the dataset (Super Productivity keeps it in local storage). No
GTK."""
import math

MINUTE = 60 * 1000
MODES = ("Pomodoro", "Flowtime", "Countdown")
DEFAULTS = {"duration": 25 * MINUTE, "breakDuration": 5 * MINUTE,
            "longerBreakDuration": 15 * MINUTE, "cyclesBeforeLongerBreak": 4}
MIN_BREAK = MINUTE


def pomodoro_config(config):
    found = config.get("pomodoro") or {}
    return {k: found.get(k) or v for k, v in DEFAULTS.items()}


def flowtime_config(config):
    return config.get("flowtime") or {}


def pause_tracking_in_breaks(config):
    return (config.get("focusMode") or {}).get("isPauseTrackingDuringBreak", True) is not False


def countdown_for_task(default_ms, task):
    """`getCountdownDurationForTask`: the default, or the task's remaining
    estimate in whole minutes when that is shorter."""
    remaining = (task.get("timeEstimate") or 0) - (task.get("timeSpent") or 0)
    if remaining <= 0:
        return default_ms
    return min(default_ms, math.ceil(remaining / MINUTE) * MINUTE)


def flowtime_break(config, work_ms):
    cfg = flowtime_config(config)
    if not cfg.get("isBreakEnabled"):
        return None
    mode = cfg.get("breakMode")
    if mode == "ratio" and isinstance(cfg.get("breakPercentage"), (int, float)):
        if cfg["breakPercentage"] <= 0:
            return None
        return max(MIN_BREAK, round(work_ms * cfg["breakPercentage"] / 100))
    if mode == "rule":
        for rule in cfg.get("breakRules") or ():
            low, high = rule.get("minDuration", 0), rule.get("maxDuration")
            if work_ms >= low and (high is None or work_ms < high):
                return rule.get("breakDuration")
    return None


class Session:
    """One focus session and its breaks. Times are epoch ms passed in, so
    the logic can be tested without a clock."""

    def __init__(self, mode, config, now, countdown_ms=None):
        if mode not in MODES:
            raise ValueError(mode)
        self.mode = mode
        self.config = config
        self.cycle = 1
        self.phase = "work"
        self.long_break = False
        self.countdown_ms = countdown_ms or DEFAULTS["duration"]
        self.started = now
        self.length = self._work_length()

    def _work_length(self):
        if self.mode == "Pomodoro":
            return pomodoro_config(self.config)["duration"]
        if self.mode == "Countdown":
            return self.countdown_ms
        return None  # Flowtime counts up

    def elapsed(self, now):
        return max(0, now - self.started)

    def remaining(self, now):
        """ms left in this phase; None while Flowtime counts up."""
        if self.length is None:
            return None
        return max(0, self.length - self.elapsed(now))

    def is_due(self, now):
        return self.length is not None and self.elapsed(now) >= self.length

    def end_work(self, now):
        """End the work phase. Returns the ms to log as a focus session and
        whether a break follows (then the phase is "break")."""
        worked = self.elapsed(now) if self.length is None else min(self.elapsed(now), self.length)
        pause = None
        if self.mode == "Pomodoro":
            cfg = pomodoro_config(self.config)
            self.long_break = self.cycle % cfg["cyclesBeforeLongerBreak"] == 0
            pause = cfg["longerBreakDuration"] if self.long_break else cfg["breakDuration"]
        elif self.mode == "Flowtime":
            pause = flowtime_break(self.config, worked)
            self.long_break = False
        if pause:
            self.phase, self.started, self.length = "break", now, pause
        else:
            self.phase = "done"
        return worked, bool(pause)

    def end_break(self, now):
        """End a break: Pomodoro goes on with the next session, the other
        modes are done."""
        if self.mode == "Pomodoro":
            self.cycle += 1
            self.phase, self.started, self.length = "work", now, self._work_length()
        else:
            self.phase = "done"
        self.long_break = False
