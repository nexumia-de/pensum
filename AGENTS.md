@../phosh-toolkit/agents/core.md
@../phosh-toolkit/agents/gtk-app.md

# Pensum

A light task list with time tracking for Phosh phones and the desktop
that keeps its data in [Super Productivity](https://github.com/johannesjo/super-productivity)'s
backup format.

- App id: `de.nexumia.Pensum`.
- Plan: work items are [issues](https://github.com/nexumia-de/pensum/issues)
  in [milestones](https://github.com/nexumia-de/pensum/milestones); goals
  are in [docs/roadmap.md](docs/roadmap.md), which Super Productivity
  feature lands where in [docs/features.md](docs/features.md).
- **Same data as Super Productivity**
  ([decision](docs/decisions/backup-format.md)): the dataset is a
  `CompleteBackup` (`crossModelVersion` 4.5). Read
  [docs/super-productivity-data.md](docs/super-productivity-data.md)
  before touching `pensum/store/`. Change only fields of features Pensum
  has, with the rules of Super Productivity's reducers; keep every other
  slice and field exactly as read. Optional non-nullable fields are
  deleted, never set to `null`.
- Every change to the store keeps `pensum.store.validate.problems()`
  empty (Super Productivity's import checks); add a test that says so.
- Facts about Super Productivity come from its source at a recorded
  commit (MIT). Transcribe values as data with attribution
  (`REUSE.toml`), never copy its code.
- Sync (M4) is high-risk: read-only first, writing only with end-to-end
  tests against a real Super Productivity
  ([docs/super-productivity-sync.md](docs/super-productivity-sync.md)).
- Screenshots and UI tests use the demo dataset (`PENSUM_DEMO=1`,
  `pensum/demo.py`), never real tasks. Logs name ids and counts, never
  titles or notes.
- Visible name: **Day Planner** (chosen by the owner on 2026-11-06,
  [decision](docs/decisions/app-name.md)); the code name Pensum stays for
  the repository, app id, package and docs.
- Run PyGObject code with `/usr/bin/python3.12` on the cloud host; the
  default `python3` has no `gi`.
