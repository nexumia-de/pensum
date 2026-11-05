---
type: Decision Record
title: Super Productivity's backup format as storage
description: Pensum stores its whole dataset as one Super Productivity CompleteBackup file and changes it the way Super Productivity's reducers do, instead of an own database with converters.
tags: [decision, data, backup, super-productivity]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Status

Accepted (2026-11-05). The owner asked for "the same data base, so that
their backup system can be reused".

# Context

Options: (1) port Super Productivity (Electron/Angular) to aarch64 —
not lighter; (2) an own model (SQLite) with import and export
converters — every round trip risks losing fields Pensum does not
know; (3) keep Super Productivity's own dataset as the storage and
change it in place.

# Decision

Option 3. `data.json` is a `CompleteBackup` (`crossModelVersion`
4.5). Pensum changes only the fields of the features it has, with the
same rules as Super Productivity's reducers, and keeps every other
slice and field as read. Its automatic backups use the desktop app's
names and shape. Super Productivity's cross-model import checks run in
the tests after every kind of change.

# Consequences

- Export is a copy of the file; import replaces it (after a backup).
- The data stays small for a phone (JSON in memory, written within a
  second of a change, atomically).
- A newer `crossModelVersion` is refused instead of guessed.
- Live sync (M4) is separate work: it needs Super Productivity's
  operation log, not just the state ([sync files](../super-productivity-sync.md)).
