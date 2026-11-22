"""Task attachments as Super Productivity keeps them: `task.attachments`,
each `{id, type, path, title?}` with type LINK, FILE, IMG, COMMAND or
NOTE (read at commit 9980fd76: `task-attachment.model.ts`,
`drop-paste.model.ts`, `task.reducer.ts`, the edit dialog).

- Adding appends with a new id; a LINK or IMG path without a scheme
  gets `http://` (`//host` gets `http:`); an empty path adds nothing.
- Deleting removes by id; everything else of the list stays as read.
- Day Planner opens LINK and IMG through the URI launcher and FILE
  through the file launcher (portal), shows NOTE as text and never runs
  a COMMAND (`can_open`).
No GTK."""
import re

from pensum.store import dates
from pensum.store.ids import new_id

HAS_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)
OPENABLE = ("LINK", "IMG", "FILE")
SAFE_SCHEMES = ("http", "https", "mailto", "file")


def of_task(task):
    return [a for a in task.get("attachments") or () if isinstance(a, dict)]


def normalise(kind, path):
    path = (path or "").strip()
    if path and kind in ("LINK", "IMG") and not HAS_SCHEME.match(path):
        path = ("http:" if path.startswith("//") else "http://") + path
    return path


def add(ds, task_id, path, title="", kind="LINK", now=None):
    task = ds.tasks.get(task_id)
    path = normalise(kind, path)
    if task is None or not path:
        return None
    attachment = {"type": kind, "path": path, "id": new_id()}
    if title.strip():
        attachment["title"] = title.strip()
    task["attachments"] = list(task.get("attachments") or []) + [attachment]
    task["modified"] = now or dates.now_ms()
    return attachment


def delete(ds, task_id, attachment_id, now=None):
    task = ds.tasks.get(task_id)
    if task is None:
        return False
    kept = [a for a in task.get("attachments") or [] if not (
        isinstance(a, dict) and a.get("id") == attachment_id)]
    if len(kept) == len(task.get("attachments") or []):
        return False
    task["attachments"] = kept
    task["modified"] = now or dates.now_ms()
    return True


def label(attachment):
    return attachment.get("title") or attachment.get("path") or ""


def can_open(attachment):
    """Links and pictures with a safe scheme and files; never commands."""
    kind, path = attachment.get("type"), attachment.get("path") or ""
    if kind not in OPENABLE or not path:
        return False
    if kind == "FILE":
        return True
    scheme = path.split(":", 1)[0].lower() if HAS_SCHEME.match(path) else ""
    return scheme in SAFE_SCHEMES
