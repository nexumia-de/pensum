---
type: Reference
title: Super Productivity's sync files
description: The remote files Super Productivity writes to WebDAV, Nextcloud, Dropbox, OneDrive or a local folder (v2 sync-data.json, v3 split files), their prefix, compression and encryption, the operation log inside, and what Pensum needs to read them and to join as a sync client.
tags: [super-productivity, sync, webdav, format, encryption]
sources:
  - id: sp
    title: Super Productivity 19.3.1, commit 590178d7 (2026-11-04)
    url: https://github.com/johannesjo/super-productivity/tree/590178d7b9f1214385457625efb9f6abbbe9f980
  - id: sp20
    title: Super Productivity 20.0.0, commit 4db0e112 (2026-11-06)
    url: https://github.com/johannesjo/super-productivity/tree/4db0e11236bc784d3184a9e252930b4bd53df823
  - id: syncdocs
    title: Super Productivity, docs/sync-and-op-log/
    url: https://github.com/johannesjo/super-productivity/tree/590178d7b9f1214385457625efb9f6abbbe9f980/docs/sync-and-op-log
generated: { by: claude-code/2.1.318, at: 2026-11-12T17:00:00Z }
---

Analysis for milestone M4 (sync with Super Productivity). Facts from
version 19.3.1[^sp] and its sync documentation[^syncdocs], checked
again at 20.0.0[^sp20] where marked. Pensum **reads** a sync folder
since #28 ([below](#what-pensum-reads-28)); it does not write to one.

# Architecture in one paragraph

Since version 17 every change in Super Productivity is an **operation**
(op) in a local operation log. One user intent is one op; ops carry a
vector clock and are replayed through the same reducers on other
devices. Sync providers move ops: SuperSync (Super Productivity's own
server) through an ordered op API, all file providers (WebDAV,
Nextcloud, Dropbox, OneDrive, local folder) through one shared file
format that holds a **full state snapshot plus the recent ops**.

# File envelope

Every remote file is text: `pf_` + `C` if gzip-compressed + `E` if
encrypted + a model version + `__`, then the payload
(`packages/sync-core/src/sync-file-prefix.ts`, prefix constant in
`src/app/op-log/sync-providers/provider.const.ts`). For the sync files
the version is the file format version (`2`), e.g. `pf_C2__H4sIA…`.

- Compression: gzip, then base64 (`packages/sync-core/src/compression.ts`).
  Off by default (`globalConfig.sync.isCompressionEnabled`).
- Encryption: AES-256-GCM with a key from Argon2id (memory 64 MiB,
  3 iterations, parallelism 1); binary layout
  `[salt 16][iv 12][ciphertext + tag]`, base64. Files of older versions
  use PBKDF2 without a salt prefix (`packages/sync-core/src/encryption.ts`,
  `encryption/argon2.ts`, `encryption/legacy.ts`). Compression is applied
  before encryption.

Checked at 20.0.0 (`compression.ts`, `encryption.ts`,
`encryption/argon2.ts`, `encryption/legacy.ts`, `encryption/web-crypto.ts`):
compressed text is base64 of gzip; the encrypted part is the compressed
(or plain) text; the Argon2id key uses the UTF-8 password, a 32-byte
output and no secret or associated data; AES-GCM has no associated
data. The older layout is `[iv 12][ciphertext + tag]` with
PBKDF2-SHA256, salt = the password, 1000 rounds; Super Productivity
falls back to it when the Argon2id layout fails, and so does Pensum.
Pensum (`pensum/sync/crypto.py`, #29) takes Argon2id from the bundled
`argon2-cffi-bindings` (built from source) and AES-GCM from the
runtime's OpenSSL through ctypes; PBKDF2 from Python's `hashlib`.

# v2: one file, `sync-data.json`

Default for an empty folder (`EMPTY_FOLDER_SYNC_FORMAT = 'v2'`), in the
folder `super-productivity` (WebDAV/Nextcloud) or `Super Productivity`
(OneDrive). Shape `FileBasedSyncData`
(`packages/sync-providers/src/file-based-sync-data.ts`):

| Field | Meaning |
|---|---|
| `version` | `2` |
| `syncVersion` | counter, +1 per upload; optimistic lock |
| `schemaVersion` | app data schema version |
| `vectorClock` | causal state after all ops in this file |
| `snapshotBaseClock` | clock of the last full replacement (optional) |
| `lastModified`, `clientId` | last writer |
| `state` | full `AppDataComplete` without the archives |
| `archiveYoung`, `archiveOld` | the archives (optional) |
| `recentOps` | up to 2000 compact ops, each with `sv` (the `syncVersion` it arrived in) |
| `oldestOpSyncVersion`, `oldestBatchComplete` | how far back `recentOps` reaches |

`sync-data.json.bak` is the previous version; `migration.lock` guards a
migration. A folder with only the old v16 `__meta_` file is refused.

# v3: split files (opt-in "Surgical sync")

`sync-ops.json` (small, the commit point: the same fields without
`state`/archives, plus `snapshotRef {syncVersion, vectorClock, rev?,
file?}`) and an immutable snapshot `sync-state__<syncVersion>__<random>.json`
(or the fixed `sync-state.json`) with `state` and archives. After the
migration `sync-data.json` is overwritten with a tombstone
`{version: 3, format: "split"}` so v2 clients stop.

# Compact operations

`src/app/op-log/persistence/compact/compact-operation.types.ts`:
`id` (uuid v7), `a` action type (short code), `o` op type (`CRT`, `UPD`,
`DEL`, `MOV`, `BATCH`, `SYNC_IMPORT`, `BACKUP_IMPORT`, `REPAIR`), `e`
entity type (`TASK`, `PROJECT`, `TAG`, …), `d` entity id or `ds` ids,
`p` payload (the NgRx action's payload), `c` client id, `v` vector clock
(`{clientId: counter}`, at most 20 entries), `t` timestamp, `s` schema
version. The short codes are mapped in `operation-codec.service.ts` and
`core/action-types.enum.ts`.

A generic op exists for every entity type: `[<ENTITY>] LWW Update`
(`packages/sync-core/src/lww-update-action-types.ts`) carries the
changed fields of one entity and resolves conflicts last-writer-wins.

# How a client syncs with a v2 file

1. Download `sync-data.json` and remember its revision (ETag).
2. Apply the ops of `recentOps` with `sv` above the last `syncVersion`
   it saw; if it missed more than `recentOps` holds, replace the local
   state with `state` (a gap).
3. Concurrent ops (by vector clock) go through conflict resolution:
   field-level patches, then last-writer-wins.
4. Upload: own ops appended to `recentOps`, `state` replaced by the
   merged state, `syncVersion` + 1, written with the revision as
   condition (CAS where the provider supports it; WebDAV only with
   strong ETags).

# What this means for Pensum

- **Reading** (show a synced Super Productivity dataset, read-only) needs
  only the envelope, gzip and decryption, and `state`: small and safe.
- **Writing as a client** means producing ops that Super Productivity's
  reducers replay to exactly the state Pensum shows. Plain field edits
  of one entity map to LWW Update ops; creating and deleting tasks and
  moving them between lists are multi-entity actions with their own
  reducers (`src/app/root-store/meta/task-shared-meta-reducers/`) whose
  payloads Pensum would have to match exactly. Super Productivity's own
  rules call sync changes high-risk and require reproductions for every
  conflict path. M4 therefore starts read-only and writes only after an
  end-to-end test against a real Super Productivity on a test folder.
- A **full-state write** (a `SYNC_IMPORT` op with a new `state`) is
  simpler but replaces the data on every device and drops their
  concurrent changes by design; acceptable only as an explicit
  "Replace remote data" action, never for routine edits.

# What Pensum reads (#28)

`pensum/sync/` (no GTK), page "Read Sync Folder…" in the main menu
(`pensum/ui/sync_page.py`):

- **Sources**: a WebDAV server (also Nextcloud: the WebDAV address,
  e.g. `https://cloud.example.org/remote.php/dav/files/<user>/`, plus
  the folder, default `super-productivity`) read with **GET only**
  (`webdav.py`; a test checks that no other module opens connections),
  password in the keyring (libsecret, Secret portal in the Flatpak); or
  a folder on the device chosen through the file chooser portal.
- **v2**: `sync-data.json`, envelope without `C`/`E`. At 20.0.0 every
  upload rewrites `state` with the uploader's full state after its ops
  (`_buildMergedSyncData` in `file-based-sync-adapter.service.ts`), so
  `state` is the current dataset; `recentOps` only says what changed.
  At 20.0.0 the archives are inside `state` (19.x: next to it); both are
  read. Login settings are stripped from `state` before upload.
- **v3**: `sync-ops.json` and the snapshot its `snapshotRef` names
  (then `sync-state.json`, `.bak`, each checked against `syncVersion`
  and vector clock). At 20.0.0 the snapshot is rewritten only on
  compaction; the ops after it are replayed ([below](#replaying-operations-30)),
  and a folder with an op Pensum can't apply yet is refused with the
  action's name.
- Compressed and encrypted files (#29): the encryption password is a
  field on the page, kept in the keyring per folder; a missing or wrong
  password is said as such.
- Refused with a message: a v16 `__meta_` folder, a v3 tombstone
  without ops file, an unknown version.
- **Changes since the last read**: the ops with `sv` above the
  `syncVersion` read last from the same source (remembered in
  settings); task ids from `d`/`ds`, plus the subtasks a `DEL` op's
  payload carries (deleting a parent sends one op naming only the
  parent). If `oldestOpSyncVersion` is past that version the count is
  "more than the folder keeps".
- **Import** replaces Pensum's data like a backup import (backup of the
  current data first, `Files.import_data`); `validate.problems()` stays
  empty (unit, UI and real-app tests).

## Checked against a real Super Productivity

`tests/real_app/run_sync.sh` (CI job `real-app`, [how to run
it](dev-environment.md#sync-test)): a WebDAV test server (wsgidav, with
CORS, since the web app calls WebDAV from the browser), Super
Productivity set up through its own sync dialog ("Other options" →
WebDAV) by Playwright. Round 1 adds four tasks, completes one, adds a
subtask; round 2 renames, completes, deletes the parent with its
subtask and adds a task; each round syncs. Pensum then reads the folder
over WebDAV and from disk and the test checks: every file byte-identical
before and after; ids of tasks, projects, tags and archived tasks and
the task fields (title, done, project, tags, parent, subtasks,
estimate, time spent, doneOn, notes, dueDay, created) equal Super
Productivity's own export; the tasks it shows open/done in Today are
open/done in the read data; `validate.problems()` empty, also after an
import; in round 2 the ops since round 1 name every task Super
Productivity changed. Three wrong decodes must fail these checks and
do: keeping the first snapshot, ignoring `recentOps`, and reading the
previous file `sync-data.json.bak`. The whole run is done twice: with
plain files, and with compression and encryption switched on in Super
Productivity's own settings (#29; there a wrong or missing password
must fail too). First runs on 2026-11-12 against the live web app
(20.0.0), green; CI runs the pinned image.

Found on the way: Super Productivity 20 itself moved a done task's
`doneOn` by a few milliseconds between the export after round 1 and
round 2 with no op (the op carried the later value), so "changed" in
the test means user-visible fields, not timestamps.

## Replaying operations (#30)

`pensum/sync/replay/` applies ops the way Super Productivity's reducers
do on a device that receives them (20.0.0: `task-shared-crud.reducer.ts`,
`section-shared.reducer.ts`, `task-shared-deadline.reducer.ts`,
`task.reducer.ts`, `task.reducer.util.ts`, `task-shared-helpers.ts`,
`global-config.reducer.ts`; meta-reducer order from
`meta-reducer-registry.ts`). It takes compact ops (`a` short code,
`action-type-codes.ts`) and SuperSync's full ops. Supported, read-only:

| Action | Code | Rules |
|---|---|---|
| `[Task Shared] addTask` | `HA` | default task fields, Today never in `tagIds`, top or bottom of the project list or backlog (backlog only if enabled), above the previous repeat instance if there is one, Today's order when due today, a planner day when due later |
| `[Task] Add SubTask` | `TA` | parent's project, no tags; the first subtask takes the parent's time spent and estimate; parent's `subTaskIds`, estimate (open time left of the subtasks) and time spent (per-day sums) recalculated |
| `[Task Shared] updateTask` | `HU` | a completion-day `dueDay` dropped for scheduled tasks and subtasks; the in-progress tag dropped on completion; tag lists (out of left tags, on top of joined ones); time spent with the difference passed to the parent; estimate recalculated on the parent; `doneOn` from the change or now, removed when undone; `modified` = now; Today's order and planner days follow `dueDay` |
| `[Task Shared] deleteTask` | `HD` | the task and all its subtasks out of tasks, the project's lists, every tag and every section; a last subtask gives its time spent and estimate to the parent |
| `[Global Config] Update Global Config Section` | `CU` | only `sync`, which stays local (stripped from synced data): no change |

Refused for now: every other action; `updateTask` with `projectId`
(project moves touch sections); `addTask` with a deadline (auto
planning); deleting a calendar (`ICAL`) task; other settings sections.
"Today" is the replaying device's logical day, as in Super
Productivity. JavaScript's truthiness is kept where the reducers rely
on it (an empty `tagIds` list or `timeSpentOnDay` object counts as
given).

The real-app sync test checks it: in round 2 the data read in round 1
plus the ops since must equal what Super Productivity holds (tasks with
all fields, task order, project, tag and section lists, planner days),
and the same replay without the deletes, updates or adds must fail. A
third scenario uses Surgical sync (v3), where reading itself needs the
replay. Not compared: `modified` (the time of replay) and `doneOn`
within a second, because the device that completes a task keeps its own
clock's value in its state while the op carries a value a few ms later,
which every other device applies (and Super Productivity itself after a
reload).

## SuperSync

Super Productivity 20 offers SuperSync first in its sync dialog; WebDAV,
Dropbox and the local folder are behind "Other options" and a code
comment calls them "legacy sync providers", but they are neither
deprecated nor removed.

Probed on 2026-11-12 with a test account on `sync.super-productivity.com`
(live web app 20.0.0, [how](dev-environment.md#supersync-probe), #34):

- The API answers `GET /api/sync/ops?sinceSeq=<n>&limit=<m>` with a
  bearer token: `{ops: [{serverSeq, receivedAt, op}], hasMore,
  latestSeq, serverTime, capabilities}`. Each `op` has `id`,
  `clientId`, `actionType`, `opType`, `entityType`, `entityId`,
  `payload`, `vectorClock`, `schemaVersion`, `timestamp`,
  `isPayloadEncrypted`.
- Encryption is mandatory (Super Productivity asks for the password on
  setup). `payload` is encrypted exactly like an encrypted sync file
  (`pensum.sync.crypto.decrypt` reads it) and decrypts to JSON.
- Setting up SuperSync uploads one full-state op (`SYNC_IMPORT`, action
  `[SP_ALL] Load(import) all data`) whose payload is the whole dataset:
  read into Pensum it has `validate.problems()` empty. Every later change
  is a single op with the NgRx action's payload, e.g. `CRT [Task Shared]
  addTask` (`{actionPayload: {task, workContextId, …}}`) and `UPD [Task
  Shared] updateTask` (`{actionPayload: {task: {id, changes}},
  entityChanges}`).
- So the current data = the newest full-state op + every later op
  replayed through Super Productivity's reducers. The server cannot do
  that (it cannot decrypt). Reading SuperSync therefore needs the op
  replay of #30; without it Pensum could only show the data as of the
  last full-state op, which would silently miss later changes.
- The WebSocket (`/api/sync/ws?token=…`) carries the token in the URL;
  it is only a push trigger and not needed for reading.

# Not yet checked

- WebDAV from the Flatpak on the phone (`--share=network` is set), and
  the Secret portal on Phosh.
- A real Nextcloud (the test server is wsgidav).
- Argon2id speed on the phone (64 MiB, 3 passes; 0.14 s on the cloud host), and that the GNOME runtime's libcrypto loads as `libcrypto.so.3` in the Flatpak.
- Which ETag strength the owner's WebDAV server gives.
