---
type: Decision Record
title: Writing to Super Productivity's sync folder
description: How Day Planner starts to write sync data (#30) - one Day Planner and one Super Productivity, only the ops Super Productivity itself writes for the edits Day Planner sends, each kind enabled only with an end-to-end test against a real Super Productivity, and nothing written when a change can't be expressed or conflicts.
tags: [decision, sync, super-productivity]
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
---

# Status

Accepted on 2026-11-22 (issue #30, "Decision needed"), decided by best
practice as the owner asked; the owner can change it.

# Context

Super Productivity's file sync keeps a full `state` and the recent
operations; every client replays the others' operations through its
reducers and resolves concurrent edits by vector clock
([sync files](../super-productivity-sync.md)). The project's rule:
writing only with end-to-end tests against a real Super Productivity.
The question in #30: support only one Day Planner and one Super
Productivity, or many clients.

# Decision

1. **One Day Planner and one Super Productivity first.** The tests can
   reproduce that pair (CI's `real-app` job); more clients come only
   after two-client tests with concurrent edits stay green, as the
   planning note on #30 recommended.
2. **Only Super Productivity's own ops.** Day Planner writes exactly the
   op Super Productivity writes for the same user action, so its
   reducers and conflict handling apply unchanged. No full-state
   replacement (`SYNC_IMPORT`) for routine edits: it would drop the
   other device's concurrent changes.
3. **One kind of change at a time, each with an end-to-end test.** The
   first kind is a task's title, notes, done state and estimate as
   `[Task Shared] updateTask` (#30). Anything else Day Planner changed
   (new or deleted tasks, tracked time, moves, other slices) blocks the
   send with the reasons; the data stays local and can be exported.
   Later kinds (adding and deleting tasks, tracked time) each need their
   own round in `tests/real_app/run_sync.sh` before they are enabled.
4. **Never overwrite what was not read.** The file is replaced only if
   it is still the version read (WebDAV If-Match, else the content
   compared); when the folder changed the same tasks since Day Planner's
   base, nothing is written and the user imports first.
5. **Sending is an explicit action** (Send Changes on the sync page),
   not a background sync, until the first kinds have been used by the
   owner ([owner checks](../owner-checks.md)).

# Consequences

- Day Planner's edits reach Super Productivity on the desktop without a
  backup export, for the edits most made on the phone; tracking time on
  the phone still needs the backup route until its op is added.
- Each new kind of change is a small, testable step instead of a
  general client with its own conflict rules.
