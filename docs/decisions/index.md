# Decisions

* [Super Productivity's backup format as storage](backup-format.md) - Pensum keeps one CompleteBackup file and changes it like Super Productivity's reducers do.
* [App name Pensum](app-name.md) - Code name chosen by the owner; visible name still open.
* [AGPL-3.0 licence](license.md) - Like the other apps; Super Productivity's defaults and fixtures stay MIT.
* [Day Planner is the owner's one app for building habits](habits-first.md) - Journeys first and as the start page; finished features stay, M3 on hold, simple counters dropped, sync stays.
* [Sync through a Git repository](git-sync.md) - The owner chose Git: the plugin Git Sync (nexumia-de/tabularium) keeps the sync folder in a private GitHub repository; Day Planner reads main and hands over on day-planner.
* [Writing to Super Productivity's sync folder](sync-writing.md) - One Day Planner and one Super Productivity first; only Super Productivity's own ops, one kind at a time with an end-to-end test; nothing written on a conflict.
