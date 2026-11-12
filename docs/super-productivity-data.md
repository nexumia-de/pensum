---
type: Reference
title: Super Productivity's data model
description: Every slice of Super Productivity's dataset (AppDataComplete, crossModelVersion 4.5) with its fields and the rules that keep it consistent, the backup files that carry it, and how Pensum reads and writes them.
tags: [super-productivity, data, backup, format, compatibility]
resource: ../pensum/store/
sources:
  - id: sp
    title: Super Productivity 19.3.1, commit 590178d7 (2026-11-04)
    url: https://github.com/johannesjo/super-productivity/tree/590178d7b9f1214385457625efb9f6abbbe9f980
generated: { by: claude-code/2.1.318, at: 2026-11-12T15:00:00Z }
---

Read from Super Productivity's source at version 19.3.1[^sp] (MIT,
Johannes Millan). Paths below are in that repository. Re-check them
before relying on a detail for a newer version; the model grows by
optional fields (its rule 11: new persisted fields are optional with a
runtime default), so a newer file usually only adds keys, which Pensum
keeps untouched.

# Files that carry the data

| File | Shape | Written by |
|---|---|---|
| "Export data" in Settings → Sync & Backup | `CompleteBackup`: `{timestamp, lastUpdate, crossModelVersion: 4.5, data: AppDataComplete}` | `BackupService.loadCompleteBackup` (`src/app/op-log/backup/backup.service.ts`) |
| Automatic desktop backups | bare `AppDataComplete`, `<userData>/backups/YYYY-MM-DD_HHMMSS.json`, newest 30 plus one per day for 21 days | `electron/backup.ts`, `electron/shared-with-frontend/backup-file-cleanup.util.ts` |
| Android/iOS automatic backup | bare `AppDataComplete` in a native key-value slot (two-slot ring) | `src/app/imex/local-backup/local-backup.service.ts` |
| Sync (WebDAV, Nextcloud, Dropbox, OneDrive, local folder) | `sync-data.json` (v2) or `sync-ops.json` + `sync-state.json` (v3), `state` is `AppDataComplete` minus the archives | [Super Productivity's sync](super-productivity-sync.md) |

Import (`BackupService.importCompleteBackup`) accepts both shapes: a
file with `crossModelVersion`, `timestamp` and `data` is unwrapped,
anything else is taken as the bare dataset. It then migrates pre-v14
backups, refuses a file without `task` or `project`
(`isDataRepairPossible`), fills missing slices with their defaults
(`withDefaultModelSlices` in `src/app/op-log/model/model-config.ts`),
validates every type with typia and runs the cross-model checks of
`src/app/op-log/validation/is-related-model-data-valid.ts`; a failed
check starts an automatic repair (`data-repair.ts`).

# Slices of `AppDataComplete`

`CROSS_MODEL_VERSION = 4.5`. Entity slices use NgRx entity state:
`{ids: string[], entities: {id: entity}}`. Ids are nanoids (21
characters). Days are local `YYYY-MM-DD` strings (`getDbDateStr`),
moments are epoch milliseconds, durations milliseconds.

| Slice | Content | Pensum M1 |
|---|---|---|
| `task` | open (not archived) tasks, plus `currentTaskId`, `selectedTaskId`, `lastCurrentTaskId`, `taskDetailTargetPanel`, `isDataLoaded`, `dismissedCalendarAutoImportEventIdsByProvider` | read and write |
| `project` | projects incl. the Inbox (`INBOX_PROJECT`) | read and write |
| `tag` | tags incl. the virtual `TODAY` tag | read and write |
| `timeTracking` | work start/end per project and tag per day | write `s`/`e` |
| `archiveYoung`, `archiveOld` | finished-day tasks (`task`), their `timeTracking`, `lastTimeTrackingFlush` | read for totals, kept |
| `globalConfig` | all settings, 21 sections | `misc.startOfNextDay*` and `tasks.defaultProjectId` used; rest kept |
| `menuTree` | `projectTree`, `tagTree`: folders (`k: "f"`, `name`, `children`, `isExpanded`), project (`k: "p"`) and tag (`k: "t"`) nodes | order read; new entries appended |
| `section` | sections inside a project or tag list (`contextId`, `contextType`, `title`, `taskIds`, `isExpanded`) | kept; deleted ids removed |
| `note` | notes (`projectId`, `content`, `isPinnedToToday`, `imgUrl`, `isLock`, `backgroundColor`, `created`, `modified`), `todayOrder` | kept |
| `taskRepeatCfg` | repeating task rules (below) | kept |
| `reminders` | `{id, remindAt, title, type: NOTE\|TASK, relatedId, recurringConfig?}` | kept; dropped with their task |
| `planner` | `days: {day: taskIds}` for future days, `addPlannedTasksDialogLastShown` | written when planning a later day |
| `boards` | `boardCfgs` (Kanban/Eisenhower panels) | kept |
| `simpleCounter` | habits/counters: `type` StopWatch, ClickCounter or RepeatedCountdownReminder, `countOnDay`, streak settings | kept |
| `metric` | daily evaluation (mood, productivity, notes) | kept |
| `issueProvider` | Jira, GitHub, GitLab, CalDAV … connections | kept |
| `pluginUserData`, `pluginMetadata` | plugin state | kept |

"Kept" means Pensum neither shows nor changes the slice and writes it
back exactly as read, so nothing is lost on a round trip through Pensum.

## Task (`src/app/features/tasks/task.model.ts`)

Required: `id`, `title`, `projectId` (string; `null` allowed by the
plugin type), `subTaskIds`, `timeSpentOnDay` (`{day: ms}`), `timeSpent`,
`timeEstimate`, `isDone`, `tagIds`, `created`, `attachments`.

Optional: `notes` (Markdown), `parentId`, `doneOn`, `wontDoOn`,
`modified`, `dueDay` (`YYYY-MM-DD` or `null`), `dueWithTime` (ms or
`null`), `hasPlannedTime`, `deadlineDay`, `deadlineWithTime`,
`deadlineRemindAt`, `remindAt`, `reminderId`, `repeatCfgId`, `priority`
(1, 2, 3, or the older `high|medium|low`, or `null`),
`_hideSubTasksMode` (1 hide done, 2 hide all), and the issue fields
`issueId`, `issueProviderId`, `issueType`, `issueWasUpdated`,
`issueLastUpdated`, `issueAttachmentNr`, `issueTimeTracked`,
`issuePoints`, `issueLastSyncedValues`.

Optional non-nullable fields (`doneOn`, `parentId`, `remindAt`,
`repeatCfgId`) must be absent rather than `null`, or typia rejects the
task; Pensum deletes the key (`tasks.update` with `None`).

Rules the reducers keep (`src/app/features/tasks/store/task.reducer.util.ts`):

- `timeSpent` is the sum of `timeSpentOnDay`.
- A parent's `timeSpentOnDay`/`timeSpent` are the sums of its subtasks';
  its `timeEstimate` is the time its open subtasks have left
  (`max(0, estimate − spent)`, done ones count 0). A parent is never
  tracked itself.
- Subtasks inherit the parent's `projectId`, are not in
  `project.taskIds` and usually have no tags.
- `dueWithTime` wins over `dueDay`; new data sets only one of them
  (ARCHITECTURE-DECISIONS #1).
- Marking done sets `isDone` and `doneOn`; undoing removes `doneOn`.

## Project and tag (`project.model.ts`, `tag.model.ts`, `work-context.model.ts`)

Both are "work contexts": `id`, `title`, `icon`, `taskIds` (order of the
top-level tasks), `theme` (colours, background images), `advancedCfg`
(`worklogExportSettings`). Projects add `isArchived`, `isHiddenFromMenu`,
`isDone`, `doneOn`, `isEnableBacklog`, `backlogTaskIds`, `noteIds`,
`issueIntegrationCfgs`; tags add `color` and `created`.

`TODAY` is a **virtual tag** (ARCHITECTURE-DECISIONS #2): a task is in
Today when its `dueDay` is today, or `dueWithTime` falls on today; the
id `TODAY` is never in `task.tagIds`, and `TODAY.taskIds` only orders
the list (stale ids there are harmless). "Today" is the logical day:
it starts at `globalConfig.misc.startOfNextDayTime` (`HH:MM`) or the
older `startOfNextDay` (hours), so work at 1:00 with a 4:00 boundary
counts for the previous day (`DateService`, `isTodayWithOffset`).

## Time tracking (`time-tracking.model.ts`, `archive.model.ts`)

`timeTracking.project[projectId][day]` and `timeTracking.tag[tagId][day]`
hold `s` (start of work, ms), `e` (end), `b` (number of breaks), `bt`
(break time). The time itself is on the tasks (`timeSpentOnDay`).
Super Productivity books the running task's time in ticks
(`addTimeSpent`); `tasks.isAutoAddWorkedOnToToday` (default on) puts a
task worked on into Today.

## Repeating tasks (`task-repeat-cfg.model.ts`)

`repeatCycle` DAILY/WEEKLY/MONTHLY/YEARLY with `repeatEvery`, weekday
flags `monday` … `sunday`, `monthlyWeekOfMonth`/`monthlyWeekday`/
`monthlyLastDay`, `startDate`, `repeatUntilDay`, `startTime`,
`remindAt`, `defaultEstimate`, `priority`, `projectId`, `tagIds`,
`notes`, `subTaskTemplates`, `shouldInheritSubtasks`,
`repeatFromCompletionDate`, `waitForCompletion`, `skipOverdue`,
`deletedInstanceDates`, `isPaused`, `order`, `quickSetting`, and
`lastTaskCreation`/`lastTaskCreationDay` (when an instance was last
made). Instances are normal tasks with `repeatCfgId`.

How Pensum creates and changes them (`pensum/store/repeat/`, written
anew from Super Productivity's behaviour at the recorded commit):

- **When:** at start, after an import and when the logical day changes
  (checked every minute, `pensum/day_watch.py`), for every rule that is
  not paused, whose `lastTaskCreationDay` is before today and whose
  skipped days (`deletedInstanceDates`) do not contain today.
- **Which day:** only the newest occurrence on or before today (or
  `repeatUntilDay`), after `lastTaskCreationDay`; missed occurrences are
  never backfilled. The series starts at `startDate`, or at
  `lastTaskCreationDay` with `repeatFromCompletionDate`. Weekly counts
  whole weeks from the start; monthly uses the start's day (clamped to
  the month's last day, or 31 with `monthlyLastDay`) or the n-th
  weekday (`monthlyWeekOfMonth` 1–4 or -1, `monthlyWeekday` 0 = Sunday);
  yearly the start's month and day (29 February → 28).
- **Skipped:** an instance for that day already exists (id or `created`
  day) → only `lastTaskCreationDay` moves; the day is skipped → nothing;
  `waitForCompletion` and any live or archived instance undone →
  nothing; `skipOverdue` and the day is before today → only
  `lastTaskCreationDay` moves.
- **The instance:** id `rpt_<rule>_<day>`, `created` local noon of the
  day, `dueDay` the day, title, `defaultEstimate`, `notes`, tags (never
  TODAY), `priority` (high/medium/low or 3/2/1), the rule's project or
  the default project; first in the project's order (last when `order`
  > 0). With `startTime` and `remindAt`: `dueWithTime` at that time on
  the logical day (a time before the start of the next day is that
  day's late night) and `remindAt` before it, `dueDay` removed. With
  `shouldInheritSubtasks`: subtasks `<instance>_sub_<n>` from
  `subTaskTemplates`.
- **Done:** ticking off the latest instance of a
  `repeatFromCompletionDate` rule sets `startDate` and
  `lastTaskCreationDay` to today; for `waitForCompletion` the next
  instance is created at once if it is due.
- **Making a task recurring:** the rule takes the task's title,
  project, tags, estimate and subtasks (as templates); `skipOverdue` is
  on only for every single day. The first occurrence from `startDate`
  becomes `lastTaskCreationDay`; when it is not today, the task moves to
  that day (`created` noon, `dueDay`).
- **Stopping:** the rule is removed and `repeatCfgId` is deleted (never
  set to `null`) on live and archived tasks; Undo puts both back.

### Archive (`src/app/features/archive/archive.service.ts`)

"Finish Day" moves done top-level tasks with their subtasks from `task`
into `archiveYoung.task`. On the way it drops `reminderId`, `dueDay`,
`dueWithTime` and `_hideSubTasksMode`, sets `isDone`, and keeps or sets
`doneOn` (subtasks get their parent's). It removes the ids from every
project, tag, section and planner day. Every work span except today's
moves from `timeTracking` into `archiveYoung.timeTracking`, and
`archiveYoung.lastFlush` is set. When `archiveOld.lastTimeTrackingFlush`
is missing or older than 14 days, top-level tasks done more than 21 days
ago move to `archiveOld`, all of `archiveYoung.timeTracking` merges into
`archiveOld`, and both archives get `lastTimeTrackingFlush`. Pensum does
the same (`pensum/store/archive.py`).

# Cross-model checks on import

From `is-related-model-data-valid.ts`, ported to
`pensum/store/validate.py` and run by the tests after every kind of
change (and logged before every save):

- every id in `project.taskIds`/`backlogTaskIds` names a task whose
  `projectId` is that project; every note id names a note of it;
- every task's `projectId`, `tagIds` and `repeatCfgId` exist; a
  top-level task has a project or a tag;
- parents and subtasks reference each other, also across the two
  archives;
- every id in a (non-Today) tag's `taskIds` and in `note.todayOrder`
  exists;
- `ids` and `entities` agree; `menuTree` nodes have ids and valid kinds.

# A new dataset

Pensum's first start writes what Super Productivity holds after its own
first start: the Inbox project, the Today tag, every slice empty and
`DEFAULT_GLOBAL_CONFIG`. These values are transcribed as data into
`pensum/store/sp-defaults.json` (MIT, annotated in `REUSE.toml`) from
`default-global-config.const.ts`, `project.const.ts`, `tag.const.ts`,
`work-context.const.ts` and the reducers' initial states. Two values
depend on Super Productivity's build and were taken as the release
build has them: `sync.superSync.baseUrl` is the production server, and
`sync.oneDrive` uses a custom app with no client id. `boards` starts
empty instead of Super Productivity's default boards, as in its own
e2e backups; Super Productivity accepts that.

# How Pensum stores the data

- `$XDG_DATA_HOME/pensum/data.json` (in the Flatpak
  `~/.var/app/de.nexumia.Pensum/data/pensum/`) is a `CompleteBackup`,
  written atomically shortly after every change.
- `backups/` next to it holds bare-dataset backups named and kept like
  the desktop app's, at most one per 15 minutes, and one before every
  import. Any of them can be imported into Super Productivity.
- **Import** reads both shapes, refuses files whose `crossModelVersion`
  is newer (made by a newer Super Productivity) or older than 4.5
  (Super Productivity must migrate them first), and fills missing slices
  like `withDefaultModelSlices`.
- **Export** writes a `CompleteBackup` with the full dataset, archives
  included, named `sp-backup-YYYY-MM-DD_HHMMSS.json`.
- The tests read Super Productivity's own fixtures
  (`tests/fixtures/`: `e2e/fixtures/test-backup*.json` and
  `frozen-state-v18.15.json`) and check that a round trip keeps every
  field.

# Checked against a real Super Productivity

CI (job `real-app`, [how to run it](dev-environment.md#real-app-test))
imports Pensum's exports into Super Productivity **20.0.0** (Docker
image pinned in `tests/real_app/Dockerfile`; first run by hand against
the live web app, also 20.0.0, on 2026-11-12) through its own "Import
from File", in a fresh profile each:

- Super Productivity's fixture changed in Pensum (tasks added, subtasks,
  done, time spent, tags, a planned later day, a daily repeat rule with
  an archived and a new instance, a deleted project with its tasks,
  Finish Day), a dataset started fresh in Pensum, and the demo dataset
  with QuestArc's records;
- each passes Super Productivity's typia type check and cross-model
  check with no repair and no dialog: its import logs no validation
  failure or repair. The fixture's own `globalConfig` is older than the
  app and is auto-fixed exactly as when Super Productivity imports the
  unchanged fixture; Pensum keeps that section as read;
- the projects show in its menu; its own export, read back into Pensum,
  has no `validate.problems()`, the task, project, tag and repeat-rule
  counts and the checked fields as written, and no other difference
  than what Super Productivity owns: settings it adds or retires,
  `currentTaskId` (its `loadAllData` stops the timer), its UI state, and
  an empty `menuTree` that its menu fills with every project and tag;
- a broken export (a task in a missing project) fails the job.

What the run found: Super Productivity 20 repairs an import without a
dialog (it logs `Validation failed, attempting repair`), so the test
reads its log instead of waiting for a dialog. Its `addTag` puts a new
tag into the tag tree also when the tree is empty; Pensum did that only
for a non-empty tree, and now does it the same way.

# Not yet checked

- The data model above was read at 19.3.1; CI tests 20.0.0. A 19.3.x
  app has not imported Pensum's files.
- The round trip on the owner's own data and devices
  ([#2](https://github.com/nexumia-de/pensum/issues/2)).
