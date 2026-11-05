"""Days as Super Productivity stores them: local "YYYY-MM-DD" strings, and
the logical today that starts at the user's "start of next day". No GTK."""
import time
from datetime import datetime, timedelta


def now_ms():
    return int(time.time() * 1000)


def day_str(value=None):
    """Local date of a datetime or epoch milliseconds (getDbDateStr)."""
    if value is None:
        value = datetime.now()
    elif isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value / 1000)
    return value.strftime("%Y-%m-%d")


def parse_day(text):
    return datetime.strptime(text, "%Y-%m-%d").date()


def day_offset_ms(global_config):
    """How long after midnight the next day starts: misc.startOfNextDayTime
    ("HH:MM"), else the older misc.startOfNextDay (whole hours)."""
    misc = (global_config or {}).get("misc") or {}
    text = misc.get("startOfNextDayTime")
    if isinstance(text, str) and ":" in text:
        hours, _, minutes = text.partition(":")
        try:
            return (int(hours) * 60 + int(minutes)) * 60_000
        except ValueError:
            pass
    hours = misc.get("startOfNextDay")
    return int(hours) * 3_600_000 if isinstance(hours, (int, float)) else 0


def logical_day(global_config, ms=None):
    """The day a moment belongs to: before the start of the next day it is
    still the previous day (DateService.todayStr)."""
    ms = now_ms() if ms is None else ms
    return day_str(ms - day_offset_ms(global_config))


def shift_day(day, days):
    return (parse_day(day) + timedelta(days=days)).strftime("%Y-%m-%d")
