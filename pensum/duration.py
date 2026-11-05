"""Durations as people type and read them: "1h 30m", "45m", "1.5h", "90".
Super Productivity stores milliseconds. No GTK."""
import re

_PART = re.compile(r"(\d+(?:[.,]\d+)?)\s*([hm]?)", re.IGNORECASE)


def parse(text):
    """Milliseconds for text like "1h 30m", "1.5h", "45m" or "90" (minutes);
    None when it is not a duration. Empty text is zero."""
    text = (text or "").strip().lower()
    if not text:
        return 0
    if not re.fullmatch(r"(\s*\d+(?:[.,]\d+)?\s*[hm]?\s*)+", text):
        return None
    total = 0.0
    for number, unit in _PART.findall(text):
        value = float(number.replace(",", "."))
        total += value * (3_600_000 if unit == "h" else 60_000)
    return int(round(total))


def format_short(ms):
    """"1h 30m", "45m", "0m"."""
    minutes = int(ms or 0) // 60_000
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def format_clock(ms):
    """"1:05:09" or "5:09" for a running timer."""
    seconds = int(ms or 0) // 1000
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"
