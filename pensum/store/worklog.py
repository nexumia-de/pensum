"""The worklog and its CSV time sheet as Super Productivity makes them
(read at commit 9980fd76: `worklog.model.ts`, `worklog-export.util.ts`,
`work-context.const.ts` `WORKLOG_EXPORT_DEFAULTS`, `round-duration.ts`,
`round-time.ts`, `ms-to-string.pipe.ts`, `ms-to-clock-string.pipe.ts`).

The tasks are the open and archived tasks of a list (a project's, a
tag's own or a subtask's parent's tags; Today: every task) with their
`timeSpentOnDay` cut to the range; work start and end come from the
list's `timeTracking` entry of the day. The export follows the list's
`advancedCfg.worklogExportSettings` (missing keys from the defaults):
grouping by DATE, PARENT, TASK or WORKLOG, the columns, rounding and
`separateTasksBy`; cells are joined by `;` and escaped against CSV
formula injection. Headers stay English, as in Super Productivity.
No GTK."""
import math
from datetime import datetime

DEFAULTS = {"cols": ["DATE", "START", "END", "TIME_CLOCK", "TITLES_INCLUDING_SUB"],
            "roundWorkTimeTo": None, "roundStartTimeTo": None, "roundEndTimeTo": None,
            "separateTasksBy": " | ", "groupBy": "DATE"}
HEADLINES = {"DATE": "Date", "START": "Start", "END": "End", "TITLES": "Parent Titles",
             "TITLES_INCLUDING_SUB": "Titles", "NOTES": "Descriptions",
             "PROJECTS": "Projects", "TAGS": "Tags", "TIME_MS": "Worked",
             "TIME_STR": "Worked", "TIME_CLOCK": "Worked", "ESTIMATE_MS": "Estimate",
             "ESTIMATE_STR": "Estimate", "ESTIMATE_CLOCK": "Estimate"}
ROUND_MINUTES = {"5M": 5, "QUARTER": 15, "HALF": 30, "HOUR": 60}
EMPTY = " - "
H, M = 3600 * 1000, 60 * 1000


def _all_tasks(ds):
    for source in (ds.data["task"]["entities"], ds.data["archiveYoung"]["task"]["entities"],
                   ds.data["archiveOld"]["task"]["entities"]):
        yield from source.values()


def _index(ds):
    return {t["id"]: t for t in _all_tasks(ds)}


def _belongs(task, parent, context):
    if context.kind == "today":
        return True
    if context.kind == "project":
        return task.get("projectId") == context.id
    tags = task.get("tagIds") or (parent or {}).get("tagIds") or []
    return context.id in tags


def tasks_in_range(ds, context, first, last):
    """Copies of the list's tasks that have time between two day strings
    (inclusive), with `timeSpentOnDay` cut to those days."""
    index = _index(ds)
    found = []
    for task in index.values():
        days = {d: ms for d, ms in (task.get("timeSpentOnDay") or {}).items()
                if first <= d <= last and ms}
        if not days or not _belongs(task, index.get(task.get("parentId")), context):
            continue
        found.append({**task, "timeSpentOnDay": days})
    return found


def work_times(ds, context):
    """{"start": {day: ms}, "end": {day: ms}} of a list."""
    kind, key = {"project": ("project", context.id), "today": ("tag", "TODAY"),
                 "tag": ("tag", context.id)}.get(context.kind, (None, None))
    days = ((ds.data.get("timeTracking") or {}).get(kind) or {}).get(key) or {}
    return {"start": {d: e["s"] for d, e in days.items() if e.get("s")},
            "end": {d: e["e"] for d, e in days.items() if e.get("e")}}


def per_day(tasks):
    """{day: ms} over top-level work: leaf tasks' time (a parent's is the
    sum of its subtasks')."""
    totals = {}
    for task in tasks:
        if task.get("subTaskIds"):
            continue
        for day, ms in task["timeSpentOnDay"].items():
            totals[day] = totals.get(day, 0) + ms
    return totals


def settings(ds, context):
    entity = (ds.project_entities.get(context.id) if context.kind == "project"
              else ds.tag_entities.get("TODAY" if context.kind == "today" else context.id)) or {}
    found = ((entity.get("advancedCfg") or {}).get("worklogExportSettings")) or {}
    merged = {**DEFAULTS, **found}
    merged["cols"] = [c for c in (found.get("cols") or DEFAULTS["cols"]) if c]
    return merged


# --- rows --------------------------------------------------------------


def _fields(ds, task, index):
    parent = index.get(task.get("parentId"))
    project = ds.project_entities.get(task.get("projectId")) or {}
    tags = task.get("tagIds") or (parent or {}).get("tagIds") or []
    return {"tasks": [task], "titlesWithSub": [task.get("title", "")],
            "titles": [(parent or task).get("title", "")],
            "notes": [task["notes"].replace("\n", " - ")] if task.get("notes") else [],
            "projects": [project.get("title", "")] if task.get("projectId") else [],
            "tags": [(ds.tag_entities.get(t) or {}).get("title", "") for t in tags]}


def _unique(values):
    return list(dict.fromkeys(values))


def rows(ds, tasks, times, group_by):
    index = _index(ds)
    groups = {}
    for task in tasks:
        fields = _fields(ds, task, index)
        days = task["timeSpentOnDay"]
        leaf = not task.get("subTaskIds")
        if group_by == "DATE":
            for day, ms in days.items():
                spent = ms if leaf else 0
                estimate = (task.get("timeEstimate") or 0) / len(days) if leaf else 0
                row = groups.get(day)
                if row is None:
                    groups[day] = {"dates": [day], "workStart": times["start"].get(day),
                                   "workEnd": times["end"].get(day), "timeSpent": spent,
                                   "timeEstimate": estimate,
                                   **{k: list(v) for k, v in fields.items()}}
                else:
                    for key in ("titles", "titlesWithSub", "tasks", "notes", "projects", "tags"):
                        row[key].extend(fields[key])
                    row["timeSpent"] += spent
                    row["timeEstimate"] += estimate
        elif group_by == "WORKLOG":
            for day, ms in days.items():
                groups[f"{day}_{task['id']}"] = {
                    "dates": [day], "workStart": times["start"].get(day),
                    "workEnd": times["end"].get(day),
                    "timeSpent": ms if leaf else 0,
                    "timeEstimate": (task.get("timeEstimate") or 0) if leaf else 0, **fields}
        else:
            if (group_by == "PARENT" and task.get("parentId")) or (
                    group_by == "TASK" and task.get("subTaskIds")):
                continue
            groups[task["id"]] = {"dates": sorted(days), "workStart": 0, "workEnd": 0,
                                  "timeSpent": sum(days.values()),
                                  "timeEstimate": task.get("timeEstimate") or 0, **fields}
    found = [groups[k] for k in sorted(groups)]
    if group_by == "DATE":
        for row in found:
            if len(row["tasks"]) > 1:
                for key in ("titles", "projects", "tags"):
                    row[key] = _unique(row[key])
    if group_by == "WORKLOG":
        seen = set()
        for row in found:
            if row["dates"][0] in seen:
                row["workStart"] = row["workEnd"] = 0
            seen.add(row["dates"][0])
    return found


# --- formatting --------------------------------------------------------


def round_duration(ms, option, up=False):
    factor = ROUND_MINUTES.get(option)
    if not factor:
        return ms
    minutes = round(ms / M)
    rounded = math.ceil(minutes / factor) * factor if up else _round_half_up(minutes / factor) * factor
    return rounded * M


def _round_half_up(value):
    """JavaScript's Math.round."""
    return math.floor(value + 0.5)


def round_time(ms, option):
    stamp = datetime.fromtimestamp(ms / 1000)
    factor = {"QUARTER": 15, "HALF": 30, "HOUR": 60}.get(option)
    if not factor:
        return stamp
    minutes = _round_half_up(stamp.minute / factor) * factor
    base = stamp.replace(minute=0, second=0, microsecond=0).timestamp() * 1000
    return datetime.fromtimestamp((base + minutes * M) / 1000)


def ms_to_string(ms):
    hours, minutes = int(ms // H), int((ms - (ms // H) * H) // M)
    text = (f"{hours}h " if hours > 0 else "") + (f"{minutes}m " if minutes > 0 else "")
    return text.strip() or "-"


def ms_to_clock(ms):
    total_minutes = int(abs(ms) // 1000) // 60
    text = ("-" if ms < 0 else "") + f"{total_minutes // 60}:{total_minutes % 60:02d}"
    return "-" if text == "0:00" else text


def _cell(row, col, options):
    spent = row["timeSpent"]
    if options.get("roundWorkTimeTo"):
        spent = round_duration(spent, options["roundWorkTimeTo"], True)
    estimate = row["timeEstimate"]
    if options["groupBy"] == "WORKLOG" and col.startswith("ESTIMATE"):
        total = sum(row["tasks"][0]["timeSpentOnDay"].values())
        estimate = estimate * (row["timeSpent"] / total) if total else 0
    sep = options.get("separateTasksBy")
    if col == "DATE":
        return row["dates"][0] + (" - " + row["dates"][-1] if len(row["dates"]) > 1 else "")
    if col in ("START", "END"):
        value = row["workStart" if col == "START" else "workEnd"]
        if not value:
            return EMPTY
        return round_time(value, options.get("roundStartTimeTo" if col == "START"
                                             else "roundEndTimeTo")).strftime("%H:%M")
    if col == "TITLES":
        return (sep or "<br>").join(row["titles"])
    if col == "TITLES_INCLUDING_SUB":
        return (sep or "<br>").join(row["titlesWithSub"])
    if col in ("NOTES", "PROJECTS", "TAGS"):
        values = row[col.lower()]
        return sep.join(values) if values else EMPTY
    return {"TIME_MS": spent, "TIME_STR": ms_to_string(spent), "TIME_CLOCK": ms_to_clock(spent),
            "ESTIMATE_MS": estimate, "ESTIMATE_STR": ms_to_string(estimate),
            "ESTIMATE_CLOCK": ms_to_clock(estimate)}.get(col, EMPTY)


def _escape(value):
    raw = "" if value is None else (str(int(value)) if isinstance(value, float) and value.is_integer()
                                    else str(value))
    if raw != "-" and raw[:1] in ("=", "+", "-", "@", "\t", "\r", "\n"):
        raw = "'" + raw
    if any(c in raw for c in ';"\r\n'):
        raw = '"' + raw.replace('"', '""') + '"'
    return raw


def csv_text(ds, context, first, last):
    options = settings(ds, context)
    found = rows(ds, tasks_in_range(ds, context, first, last), work_times(ds, context),
                 options["groupBy"])
    lines = [";".join(_escape(HEADLINES.get(c, "INVALID COL")) for c in options["cols"])]
    lines += [";".join(_escape(_cell(row, c, options)) for c in options["cols"]) for row in found]
    return "\n".join(lines)


def file_name(first, last):
    return f"tasks{first}-{last}.csv"
