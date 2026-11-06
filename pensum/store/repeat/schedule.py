"""When a repeat rule has an occurrence: the newest one on or before a
day, and the first one from its start date. Days are "YYYY-MM-DD"
strings; the rules follow Super Productivity 19.3.1
(get-newest-possible-due-date, get-first-repeat-occurrence), written
anew for dates without times. No GTK."""
import calendar
from datetime import date, timedelta

from pensum.store import dates

# Super Productivity's weekday flags, Monday first like date.weekday().
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday")
EPOCH = "1970-01-01"


def _day(text):
    return dates.parse_day(text)


def _text(day):
    return day.strftime("%Y-%m-%d")


def _every(cfg):
    every = cfg.get("repeatEvery")
    return every if isinstance(every, int) and not isinstance(every, bool) and every >= 1 else None


def last_creation_day(cfg):
    """lastTaskCreationDay, else the day of the older lastTaskCreation."""
    if cfg.get("lastTaskCreationDay"):
        return cfg["lastTaskCreationDay"]
    if cfg.get("lastTaskCreation"):
        return dates.day_str(cfg["lastTaskCreation"])
    return None


def start_day(cfg):
    """With repeatFromCompletionDate the series restarts at the last
    creation; otherwise it starts at startDate."""
    if cfg.get("repeatFromCompletionDate") and cfg.get("lastTaskCreationDay"):
        return cfg["lastTaskCreationDay"]
    return cfg.get("startDate") or EPOCH


def is_weekday(cfg, day):
    return cfg.get(WEEKDAYS[day.weekday()]) is True


def _clamped(year, month, wanted):
    return date(year, month, min(wanted, calendar.monthrange(year, month)[1]))


def _add_months(year, month, delta):
    index = year * 12 + month - 1 + delta
    return index // 12, index % 12 + 1


def _months_between(start, day):
    return (day.year - start.year) * 12 + day.month - start.month


def has_nth_weekday(cfg):
    week, weekday = cfg.get("monthlyWeekOfMonth"), cfg.get("monthlyWeekday")
    return (isinstance(week, int) and (week == -1 or 1 <= week <= 4)
            and isinstance(weekday, int) and 0 <= weekday <= 6)


def nth_weekday(year, month, cfg):
    """The n-th (or last, -1) weekday of a month; monthlyWeekday counts
    from Sunday = 0."""
    wanted = (cfg["monthlyWeekday"] - 1) % 7  # to date.weekday(): Monday = 0
    if cfg["monthlyWeekOfMonth"] == -1:
        last = date(year, month, calendar.monthrange(year, month)[1])
        return last - timedelta(days=(last.weekday() - wanted) % 7)
    first = date(year, month, 1)
    offset = (wanted - first.weekday()) % 7
    return first + timedelta(days=offset + (cfg["monthlyWeekOfMonth"] - 1) * 7)


def newest_due_day(cfg, today):
    """The newest occurrence on or before `today` (or before repeatUntilDay
    when that is earlier) that comes after the last creation, or None."""
    every = _every(cfg)
    if every is None:
        return None
    check = _day(today)
    if cfg.get("repeatUntilDay") and today > cfg["repeatUntilDay"]:
        check = _day(cfg["repeatUntilDay"])
    start = _day(start_day(cfg))
    last = _day(last_creation_day(cfg) or EPOCH)
    if start > check:
        return None
    cycle = cfg.get("repeatCycle")
    if cycle == "DAILY":
        for back in range(every + 1):
            day = check - timedelta(days=back)
            if day <= last or day < start:
                break
            if (day - start).days % every == 0:
                return _text(day)
    elif cycle == "WEEKLY":
        for back in range(every * 7 + 1):
            day = check - timedelta(days=back)
            weeks = (day - start).days // 7
            if day <= last or weeks < 0:
                break
            if weeks % every == 0 and is_weekday(cfg, day):
                return _text(day)
    elif cycle == "MONTHLY":
        return _newest_monthly(cfg, check, start, last, every)
    elif cycle == "YEARLY":
        day = _clamped(check.year, start.month, start.day)
        if day > check:
            day = _clamped(check.year - 1, start.month, start.day)
        for _ in range(every):
            years = day.year - start.year
            if day <= last or years < 0:
                break
            if years % every == 0:
                return _text(day)
            day = _clamped(day.year - 1, start.month, start.day)
    return None


def _newest_monthly(cfg, check, start, last, every):
    if has_nth_weekday(cfg):
        year, month = check.year, check.month
        for _ in range(every + 1):
            day = nth_weekday(year, month, cfg)
            months = _months_between(start, date(year, month, 1))
            if day <= check and day > last and months >= 0 and months % every == 0:
                return _text(day)
            year, month = _add_months(year, month, -1)
        return None
    wanted = 31 if cfg.get("monthlyLastDay") else start.day
    year, month = check.year, check.month
    if check.day < _clamped(year, month, wanted).day:
        year, month = _add_months(year, month, -1)
    for _ in range(every):
        day = _clamped(year, month, wanted)
        months = _months_between(start, day)
        if day <= last or months < 0:
            break
        if months % every == 0:
            return _text(day)
        year, month = _add_months(year, month, -1)
    return None


def first_day(cfg):
    """The first occurrence from startDate, or None without a start date,
    with an invalid rule or when it falls after repeatUntilDay."""
    if _every(cfg) is None or not cfg.get("startDate"):
        return None
    day = _day(cfg["startDate"])
    cycle = cfg.get("repeatCycle")
    if cycle == "MONTHLY":
        if has_nth_weekday(cfg):
            candidate = nth_weekday(day.year, day.month, cfg)
            if candidate < day:
                year, month = _add_months(day.year, day.month, 1)
                candidate = nth_weekday(year, month, cfg)
            day = candidate
        elif cfg.get("monthlyLastDay"):
            day = _clamped(day.year, day.month, 31)
    elif cycle == "WEEKLY":
        for _ in range(7):
            if is_weekday(cfg, day):
                break
            day += timedelta(days=1)
        else:
            return None
    elif cycle not in ("DAILY", "YEARLY"):
        return None
    if cfg.get("repeatUntilDay") and _text(day) > cfg["repeatUntilDay"]:
        return None
    return _text(day)
