---
type: Decision Record
title: Sync through a Git repository with Git Sync
description: The owner chose Git as a sync path between Super Productivity on the desktop and Day Planner; a Super Productivity plugin in its own repository (tabularium) keeps the sync folder in a private GitHub repository, Day Planner reads and hands over through GitHub's API.
tags: [decision, sync, git, github]
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
---

# Status

Accepted on 2026-11-22, decided by the owner: Git as in domus, built as
a Super Productivity plugin, code name and repository
`nexumia-de/tabularium` chosen by the owner, "setze um". The protocol's
details were chosen by the agent ([tabularium's decision](https://github.com/nexumia-de/tabularium/blob/main/docs/decisions/branch-handoff.md)).

# Context

- WebDAV needs a server; SuperSync is not planned (#34).
- Super Productivity has no Git sync, and a plugin cannot add a sync
  provider; a desktop plugin may run `git` (node execution) and trigger
  Super Productivity's own sync.

# Decision

- **Desktop**: the plugin Git Sync (tabularium) drives Super
  Productivity's local-file sync through a clone of a private
  repository and is the only writer of `main`.
- **Day Planner**: a third kind of sync folder, GitHub Repository; reads
  `main`, writes only the branch `day-planner`, through the REST API with
  a fine-grained token for that one repository ([Git Sync](../git-sync.md)).
- The plugin lives in its own repository (one deliverable per
  repository; a JavaScript plugin does not fit a GTK app's).
- The data repository is the user's own and private, never one of the
  project's repositories.

# Consequences

- Same limits as WebDAV writing ([sync writing](sync-writing.md)): one
  Day Planner and one Super Productivity, only the kinds of change Day
  Planner can send.
- The phone's changes reach Super Productivity only while it runs on
  the desktop.
- `api.github.com` is a new host for the Flatpak's network use.
