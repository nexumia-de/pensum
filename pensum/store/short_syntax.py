"""Short syntax in the add field, a subset of Super Productivity's
(src/app/features/tasks/short-syntax.ts) with the same characters:
`+project`, `#tag`, `1h 30m` (estimate), `10m/1h` (spent/estimate),
`p1`–`p3` (p1 is high), `@today`, `@tomorrow`, `@fri`, `@14:30`, each
switched by globalConfig.shortSyntax. No GTK."""
import re
from dataclasses import dataclass, field
from datetime import timedelta

from pensum.store import dates

_DURATION = r"\d+(?:\.\d+)?[mh]"
_TIME = re.compile(r"(?:\s|^)t?((?:" + _DURATION + r"\s*)+)(?:\s*/((?:\s*" + _DURATION
                   + r")+)?)?(?=\s|$)")
_TAG = re.compile(r"(?:(?<=\s)|^)#([^\s+#@!]+)")
_PROJECT = re.compile(r"(?:(?<=\s)|^)\+(?!\s)((?:(?!\s+(?:#|@|t?\d+[mh]\b)).)+)")
_PRIORITY = re.compile(r"(?:^|\s)p([1-3])(?=\s|$)")
_DUE = re.compile(r"(?:(?<=\s)|^)@([^\s+#@!]+(?:\s+\d{1,2}[:.]\d{2})?)")
_PRIORITY_FOR_TOKEN = {"1": 3, "2": 2, "3": 1}
_WEEKDAYS = {}
for _index, _name in enumerate(("monday", "tuesday", "wednesday", "thursday",
                                "friday", "saturday", "sunday")):
    _WEEKDAYS[_name] = _WEEKDAYS[_name[:3]] = _index


@dataclass
class Parsed:
    title: str
    project_id: str = None
    tag_titles: list = field(default_factory=list)
    estimate: int = None
    spent: int = None
    priority: int = None
    due_day: str = None
    due_time: tuple = None


def _ms(group):
    total = 0.0
    for number, unit in re.findall(r"(\d+(?:\.\d+)?)([mh])", group or ""):
        total += float(number) * (3_600_000 if unit == "h" else 60_000)
    return int(round(total))


def _cut(text, match):
    return re.sub(r"\s{2,}", " ", (text[:match.start()] + " " + text[match.end():])).strip()


def _project(ds, typed):
    """The project whose title (spaces ignored) the typed words start; the
    longest typed prefix that matches wins, as in Super Productivity."""
    words = typed.split()
    projects = [(p["id"], (p.get("title") or "").replace(" ", "").lower())
                for p in ds.projects()]
    for count in range(len(words), 0, -1):
        prefix = "".join(words[:count]).lower()
        for project_id, title in sorted(projects, key=lambda p: len(p[1])):
            if title.startswith(prefix):
                return project_id, " ".join(words[:count])
    return None, None


def _due(token, today):
    token = token.strip().lower()
    clock = re.search(r"(\d{1,2})[:.](\d{2})$", token)
    time = None
    if clock:
        hours, minutes = int(clock.group(1)), int(clock.group(2))
        if hours > 23 or minutes > 59:
            return None, None
        time = (hours, minutes)
        token = token[:clock.start()].strip()
    day = None
    if token in ("", "today"):
        day = today
    elif token == "tomorrow":
        day = dates.shift_day(today, 1)
    elif token in _WEEKDAYS:
        base = dates.parse_day(today)
        ahead = (_WEEKDAYS[token] - base.weekday()) % 7 or 7
        day = (base + timedelta(days=ahead)).strftime("%Y-%m-%d")
    if day is None:
        return None, None
    return day, time


def parse(ds, text, today=None):
    today = today or ds.today()
    cfg = (ds.config.get("shortSyntax") or {})
    parsed = Parsed(title=text.strip())
    title = parsed.title
    if cfg.get("isEnableProject", True):
        match = _PROJECT.search(title)
        if match:
            project_id, typed = _project(ds, match.group(1))
            if project_id:
                parsed.project_id = project_id
                start = match.start()
                title = _cut(title, _Span(start, start + 1 + len(typed)))
    if cfg.get("isEnableTag", True):
        while True:
            match = _TAG.search(title)
            if not match or match.group(1).isdigit():
                break
            parsed.tag_titles.append(match.group(1))
            title = _cut(title, match)
    if cfg.get("isEnableDue", True):
        match = _DUE.search(title)
        if match:
            day, time = _due(match.group(1), today)
            if day:
                parsed.due_day, parsed.due_time = day, time
                title = _cut(title, match)
    if cfg.get("isEnablePriority", True):
        match = _PRIORITY.search(title)
        if match:
            parsed.priority = _PRIORITY_FOR_TOKEN[match.group(1)]
            title = _cut(title, match)
    match = _TIME.search(title)
    if match:
        if "/" in match.group(0):
            parsed.spent = _ms(match.group(1))
            if match.group(2):
                parsed.estimate = _ms(match.group(2))
        else:
            parsed.estimate = _ms(match.group(1))
        title = _cut(title, match)
    parsed.title = title or text.strip()
    return parsed


class _Span:
    def __init__(self, start, end):
        self._start, self._end = start, end

    def start(self):
        return self._start

    def end(self):
        return self._end


def apply(ds, task, parsed, now=None):
    """Write what the syntax said onto a task just added."""
    from pensum.store import contexts, tasks, tracking
    now = now or dates.now_ms()
    tasks.update(ds, task["id"], now, title=parsed.title)
    if parsed.project_id:
        tasks.move_to_project(ds, task["id"], parsed.project_id, now)
    if parsed.tag_titles:
        by_title = {(t.get("title") or "").lower(): t["id"] for t in ds.tags()}
        tag_ids = list(task.get("tagIds", ()))
        for title in parsed.tag_titles:
            tag_id = by_title.get(title.lower()) or contexts.add_tag(ds, title, now)["id"]
            if tag_id not in tag_ids:
                tag_ids.append(tag_id)
        tasks.set_tags(ds, task["id"], tag_ids, now)
    if parsed.estimate is not None:
        tasks.set_estimate(ds, task["id"], parsed.estimate, now)
    if parsed.spent:
        tracking.set_time_on_day(ds, task["id"], ds.today(now), parsed.spent, now)
    if parsed.priority:
        tasks.set_priority(ds, task["id"], parsed.priority, now)
    if parsed.due_day:
        if parsed.due_time:
            tasks.schedule_time(ds, task["id"], parsed.due_day, *parsed.due_time, now=now)
        else:
            tasks.schedule_day(ds, task["id"], parsed.due_day, now)
