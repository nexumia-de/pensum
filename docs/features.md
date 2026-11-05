---
type: Reference
title: Super Productivity's features and Pensum's plan for them
description: Every feature of Super Productivity 19.3.1, the data it uses, and the milestone in which Pensum rebuilds it on the same data (or why it is left out).
tags: [features, plan, super-productivity, parity]
sources:
  - id: sp
    title: Super Productivity 19.3.1, README and src/app/features (commit 590178d7)
    url: https://github.com/johannesjo/super-productivity/tree/590178d7b9f1214385457625efb9f6abbbe9f980
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

Inventory from Super Productivity's README and its feature folders
(`src/app/features/*`)[^sp]. Each line names the data
([data model](super-productivity-data.md)) and Pensum's milestone; the
work items are the GitHub issues of those milestones
([roadmap](roadmap.md)). Pensum stays light: it rebuilds what helps on
a phone and keeps everything else in the data untouched, so nothing is
lost when the same backup goes back to Super Productivity.

# Tasks and lists

| Feature | Data | Pensum |
|---|---|---|
| Tasks: add, rename, done/undone, delete | `task` | **M1, done** |
| Subtasks with summed time and estimate | `task.subTaskIds`, `parentId` | **M1, done** |
| Notes per task (Markdown) | `task.notes` | **M1, done** (plain text editing; Markdown rendering M2) |
| Time estimate | `task.timeEstimate` | **M1, done** |
| Inbox and projects: create, rename, archive, delete | `project`, `menuTree.projectTree` | **M1, done** (incl. archived projects page) |
| Tags: create, rename, delete, tag tasks | `tag`, `task.tagIds`, `menuTree.tagTree` | **M1, done** |
| Today list (virtual tag, logical day) | `task.dueDay`/`dueWithTime`, `TODAY.taskIds` | **M1, done** |
| Plan a task for a day | `task.dueDay`, `planner.days` | **M1, done** |
| Reorder tasks | `project/tag.taskIds`, `subTaskIds` | **M1**: menu (long press, right click, Alt+↑/↓) done; drag open (#3) |
| Move a task to another project | `task.projectId` | **M1, done** |
| Overdue tasks in Today | `dueDay` < today | **M2, done** (#6) |
| Plan with time of day, schedule timeline | `dueWithTime`, `hasPlannedTime`, `globalConfig.schedule` | M2 |
| Deadlines | `deadlineDay`, `deadlineWithTime`, `deadlineRemindAt` | M2 |
| Priority | `task.priority` | M2 |
| Backlog of a project | `project.backlogTaskIds`, `isEnableBacklog` | M2 |
| Sections in a list | `section` | M2 |
| Repeating tasks | `taskRepeatCfg`, `task.repeatCfgId` | M2 |
| Reminders as notifications | `task.remindAt`, `reminders`, `globalConfig.reminder` | M2 |
| Short syntax when adding (`#tag +project 1h @tomorrow`) | `globalConfig.shortSyntax` | M2 |
| Search | – | M2 |
| Finish day: archive done tasks | `archiveYoung`, `archiveOld`, `task` | M2 |
| Project notes | `note`, `project.noteIds` | M3 |
| Attachments and project bookmarks | `task.attachments` | M3 (show and open links) |
| Menu folders for projects and tags | `menuTree` folders | M3 (shown; editing later) |
| Hide subtasks, task view customiser | `_hideSubTasksMode` | backlog |
| Multi-select of tasks | – | backlog |

# Time

| Feature | Data | Pensum |
|---|---|---|
| Timer on the current task, booked per day | `task.currentTaskId`, `timeSpentOnDay`, `timeTracking` | **M1, done** |
| Work start and end per day | `timeTracking.*[id][day].s/e` | **M1, done** (written) |
| Edit time spent per day | `timeSpentOnDay` | M2 |
| Worklog: time sheet by day, week, month, export | `task`, archives, `advancedCfg.worklogExportSettings` | M3 |
| Daily summary and evaluation | `metric` | M3 |
| Focus mode: Pomodoro, Flowtime, countdown | `globalConfig.pomodoro`, `focusMode`, `flowtime` | M3 |
| Break reminder | `globalConfig.takeABreak`, `timeTracking.b/bt` | M3 |
| Idle detection | `globalConfig.idle` | out of scope (Phosh has no idle API for apps; the phone sleeps) |
| Tracking reminder ("you are not tracking") | `globalConfig.timeTracking.isTrackingReminderEnabled` | backlog |
| Anti-procrastination ("domina mode") | `globalConfig.dominaMode` | out of scope |

# Habits and views

| Feature | Data | Pensum |
|---|---|---|
| Habits: counters and stopwatches with streaks | `simpleCounter` | M3 |
| Planner: days ahead | `planner`, `dueDay` | M3 |
| Boards: Kanban, Eisenhower | `boards`, tags | backlog |
| Calendar events next to the plan (iCal, CalDAV) | `issueProvider` (calendar) | backlog |

# Data and sync

| Feature | Data | Pensum |
|---|---|---|
| Import and export of backups | `CompleteBackup` | **M1, done** |
| Automatic local backups | `backups/*.json` | **M1, done** |
| Light and dark style | – (Pensum's own setting) | **M1, done** |
| Day boundary ("start of next day") | `globalConfig.misc.startOfNextDay*` | **M1, done** |
| Read a WebDAV/local-folder sync file | `sync-data.json` | M4 ([sync files](super-productivity-sync.md)) |
| Sync as a client (WebDAV, Nextcloud) | ops in `recentOps` | M4 |
| Encrypted and compressed sync files | `pf_CE…` envelope | M4 |
| SuperSync server | – | backlog (after file sync) |
| Dropbox, OneDrive | OAuth | backlog |

# Out of scope

Kept in the data, never changed by Pensum:

- Issue integrations (Jira, GitHub, GitLab, Gitea, Trello, OpenProject,
  Linear, ClickUp, Redmine, Nextcloud Deck, Azure DevOps, CalDAV tasks):
  `issueProvider`, the `issue*` task fields, `project.issueIntegrationCfgs`.
  They need accounts and network; Super Productivity on the desktop
  keeps doing this, and imported tasks show in Pensum like any other.
- Plugins and custom themes (`pluginUserData`, `pluginMetadata`,
  `project.theme`, `globalConfig.misc.customTheme`): Pensum uses stock
  libadwaita (toolkit design rules).
- Electron and Android specifics: tray, global shortcuts, window title
  bar, home screen widget, share extension.
- Celebration effects, sounds, motivational images: Pensum follows
  GNOME's calm defaults.
