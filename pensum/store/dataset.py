"""Read access to a dataset in Super Productivity's model: projects, tags,
tasks and which tasks a list shows. Changes are in tasks.py, contexts.py
and tracking.py. No GTK."""
from dataclasses import dataclass

from pensum.store import dates
from pensum.store.defaults import INBOX_ID, TODAY_ID


@dataclass(frozen=True)
class Context:
    """A list of tasks: "today", or a project or tag by id."""
    kind: str
    id: str = TODAY_ID

    @classmethod
    def today(cls):
        return cls("today", TODAY_ID)


class Dataset:
    def __init__(self, data):
        self.data = data

    # Slices
    @property
    def config(self):
        return self.data["globalConfig"]

    @property
    def tasks(self):
        return self.data["task"]["entities"]

    @property
    def project_entities(self):
        return self.data["project"]["entities"]

    @property
    def tag_entities(self):
        return self.data["tag"]["entities"]

    def today(self, ms=None):
        return dates.logical_day(self.config, ms)

    def default_project_id(self):
        pid = (self.config.get("tasks") or {}).get("defaultProjectId")
        if pid in self.project_entities:
            return pid
        return INBOX_ID if INBOX_ID in self.project_entities else next(
            iter(self.data["project"]["ids"]), None)

    # Projects and tags, in the order of the menu tree
    def _tree_order(self, tree_name, ids):
        order = []

        def walk(nodes):
            for node in nodes or ():
                if node.get("k") == "f":
                    walk(node.get("children"))
                elif node.get("id") in ids and node["id"] not in order:
                    order.append(node["id"])

        walk((self.data.get("menuTree") or {}).get(tree_name))
        return order + [i for i in ids if i not in order]

    def projects(self, archived=False):
        ids = [pid for pid in self.data["project"]["ids"]
               if pid in self.project_entities
               and bool(self.project_entities[pid].get("isArchived")) == archived]
        return [self.project_entities[pid] for pid in self._tree_order("projectTree", ids)]

    def tags(self):
        ids = [tid for tid in self.data["tag"]["ids"]
               if tid in self.tag_entities and tid != TODAY_ID]
        return [self.tag_entities[tid] for tid in self._tree_order("tagTree", ids)]

    def context_title(self, context):
        if context.kind == "today":
            return "Today"
        source = self.project_entities if context.kind == "project" else self.tag_entities
        entity = source.get(context.id)
        return entity.get("title") or "" if entity else ""

    def context_exists(self, context):
        if context.kind == "today":
            return True
        source = self.project_entities if context.kind == "project" else self.tag_entities
        return context.id in source

    # Tasks
    def task(self, task_id):
        return self.tasks.get(task_id)

    def subtasks(self, task):
        return [self.tasks[i] for i in task.get("subTaskIds", ()) if i in self.tasks]

    def is_due_today(self, task, today=None):
        """TODAY is a virtual tag: a task is in it through its dueDay or
        dueWithTime, never through tagIds (ARCHITECTURE-DECISIONS #2)."""
        today = today or self.today()
        if task.get("dueWithTime"):
            # dueWithTime wins over dueDay (ARCHITECTURE-DECISIONS #1).
            return self.today(task["dueWithTime"]) == today
        return task.get("dueDay") == today

    def top_level_ids(self, context, today=None):
        """Ids of the top-level tasks a list shows, in their stored order."""
        if context.kind == "project":
            project = self.project_entities.get(context.id) or {}
            ids = list(project.get("taskIds", ()))
        elif context.kind == "tag":
            tag = self.tag_entities.get(context.id) or {}
            ids = [i for i in tag.get("taskIds", ())
                   if context.id in (self.tasks.get(i) or {}).get("tagIds", ())]
            # Tasks carrying the tag that the order list misses.
            ids += [i for i in self.data["task"]["ids"]
                    if i not in ids and i in self.tasks
                    and not self.tasks[i].get("parentId")
                    and context.id in self.tasks[i].get("tagIds", ())]
        else:
            today = today or self.today()
            member = {i for i, t in self.tasks.items()
                      if self.is_due_today(t, today)
                      and not (t.get("parentId") and self._parent_due_today(t, today))}
            order = (self.tag_entities.get(TODAY_ID) or {}).get("taskIds", ())
            ids = [i for i in order if i in member]
            ids += [i for i in self.data["task"]["ids"] if i in member and i not in ids]
        return [i for i in ids if i in self.tasks]

    def planned_day(self, task):
        """The day a task is planned for: dueWithTime's day wins over dueDay."""
        if task.get("dueWithTime"):
            return self.today(task["dueWithTime"])
        return task.get("dueDay") or None

    def overdue_tasks(self, today=None):
        """Open top-level tasks planned for a day before today, oldest first."""
        today = today or self.today()
        found = [t for t in self.tasks.values()
                 if not t.get("isDone") and not t.get("parentId")
                 and (self.planned_day(t) or today) < today]
        return sorted(found, key=lambda t: (self.planned_day(t), t.get("created", 0)))

    def _parent_due_today(self, task, today):
        parent = self.tasks.get(task.get("parentId"))
        return bool(parent) and self.is_due_today(parent, today)

    def list_tasks(self, context, today=None):
        """(open, done) top-level tasks of a list."""
        tasks = [self.tasks[i] for i in self.top_level_ids(context, today)]
        return ([t for t in tasks if not t.get("isDone")],
                [t for t in tasks if t.get("isDone")])

    def backlog_tasks(self, project_id):
        project = self.project_entities.get(project_id) or {}
        return [self.tasks[i] for i in project.get("backlogTaskIds", ()) if i in self.tasks]

    def current_task_id(self):
        current = self.data["task"].get("currentTaskId")
        return current if current in self.tasks else None
