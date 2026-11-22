---
type: Reference
title: Git Sync (sync folder in a GitHub repository)
description: Day Planner's side of Git Sync - the Super Productivity plugin in nexumia-de/tabularium keeps the desktop's sync folder in a GitHub repository; Day Planner reads it through the REST API and hands its sends over on the branch day-planner; pending, delivered and stale sends; setup, token, tests.
tags: [sync, git, github, super-productivity, tabularium]
sources:
  - id: protocol
    title: tabularium, docs/protocol.md
    url: https://github.com/nexumia-de/tabularium/blob/main/docs/protocol.md
  - id: api
    title: GitHub REST API, Git database (refs, commits, trees, blobs) and compare
    url: https://docs.github.com/en/rest/git
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
---

The owner asked for Git as the path between Super Productivity on the
desktop and Day Planner on the phone (2026-11-22,
[decision](decisions/git-sync.md)). The desktop side is the plugin Git
Sync in [nexumia-de/tabularium](https://github.com/nexumia-de/tabularium);
the shared protocol is in its `docs/protocol.md`[^protocol].

# How it fits

- Super Productivity syncs ("Local file", manual sync only) into a
  clone of a private repository; the plugin runs prepare (fetch, take
  Day Planner's hand-over), Super Productivity's sync, finish (commit,
  push). Only the plugin writes `main`.
- Day Planner: Sync Folder → Kind **GitHub Repository**, the
  repository `owner/name`, an optional folder in it, and a fine-grained
  token for that one repository with Contents: read and write (in the
  keyring under `github:<owner/name>`). `pensum/sync/github.py`, the form
  in `pensum/ui/sync_source.py`.
- Reading and Send Changes work as for WebDAV
  ([sync files](super-productivity-sync.md)); the files are the same,
  compression and encryption included.

# Branches as Day Planner sees them

`GitHub.state()` reads `main`, `day-planner` and, when they differ,
`compare/main...day-planner`[^api] once per object and pins the commit,
so all files of one read come from one commit:

| `day-planner` | Meaning | Reads and sends from |
|---|---|---|
| missing, equal, behind | delivered | `main` |
| ahead | last send waits for the desktop | `day-planner` |
| diverged | stale: the desktop synced on top of an older `main` first | `main` |

A send is one commit (blob, tree on the read commit's tree, commit with
author "Day Planner") and a ref update: create `day-planner`, or
fast-forward it (`force: false`, so a branch that moved answers 422 →
"changed while sending"). Only after a stale send the branch is moved
with force, after checking it is still where it was read.

# Stale sends

The plugin keeps Super Productivity's upload and leaves the hand-over
alone. Day Planner then:

- shows on Read Folder: "Your last sent changes did not reach Super
  Productivity. Send Changes sends them again.";
- on Send Changes takes the data at the merge base as its base
  (`sync_send._stale_base`), so the undelivered edits and the new ones go
  out together on top of `main`, with the usual checks (Super
  Productivity's ops since the base must not touch the same tasks).

# Tests

- `tests/test_sync_github.py` against `tests/github_fake.py` (the API
  endpoints above on a real bare repository, git plumbing): read, send,
  chained sends, delivery, a send after delivery, a stale send sent
  again, concurrent writes, wrong token, a folder in the repository, an
  empty repository, and the sync page.
- `tests/real_app/run_sync.sh`, scenario git (with `TABULARIUM` set to a
  tabularium checkout; CI pins one): the WebDAV folder is the clone, each
  Super Productivity sync runs between the plugin's prepare and finish
  (`git_cycle.mjs`), Pensum reads and sends through the stand-in; round 3
  checks the hand-over was taken and Super Productivity shows Pensum's
  edits. Green against the live web app on 2026-11-22.
- Not tested against github.com itself: the cloud session has no GitHub
  API access for scripts; the endpoints and answers used are the
  documented ones.

[^protocol]: https://github.com/nexumia-de/tabularium/blob/main/docs/protocol.md
[^api]: https://docs.github.com/en/rest/git and https://docs.github.com/en/rest/commits/commits#compare-two-commits
