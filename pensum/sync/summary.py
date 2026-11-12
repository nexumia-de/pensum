"""Counts of a dataset, to show what a sync folder holds before import."""
from dataclasses import dataclass

from pensum.store.defaults import TODAY_ID


@dataclass
class Summary:
    open_tasks: int
    done_tasks: int
    archived_tasks: int
    projects: int
    tags: int


def summarize(data):
    tasks = data["task"]["entities"].values()
    done = sum(1 for t in tasks if t.get("isDone"))
    archived = sum(len(data[a]["task"]["ids"]) for a in ("archiveYoung", "archiveOld"))
    projects = sum(1 for p in data["project"]["entities"].values()
                   if not p.get("isArchived"))
    tags = sum(1 for t in data["tag"]["ids"] if t != TODAY_ID)
    return Summary(open_tasks=len(data["task"]["ids"]) - done, done_tasks=done,
                   archived_tasks=archived, projects=projects, tags=tags)
