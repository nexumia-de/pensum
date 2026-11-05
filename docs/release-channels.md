---
type: Playbook
title: Release channels
description: Pensum (stable, from tags v<version>) and Pensum (Nightly) (de.nexumia.Pensum.Devel, from every push to main), changelog fragments, and store screenshots from the demo dataset.
tags: [release, nightly, flatpak, ci, changelog, screenshots]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Channels

| Channel | App | App id | Fed by |
|---|---|---|---|
| Stable | Pensum | `de.nexumia.Pensum` | tags `v0.1.0`, … |
| Nightly | Pensum (Nightly) | `de.nexumia.Pensum.Devel` | every push to `main` |

Both come from the shared repository once `nexumia-de/pensum` is
listed in phosh-apps' `apps.txt` (after the first tag). The workflow
needs the secret `PUBLISH_TOKEN` in this repository, as in the other
apps. Mechanics: the toolkit's
[Flatpak workflow](../../phosh-toolkit/docs/flatpak-workflow.md#release-channels)
and [releases](../../phosh-toolkit/docs/releases.md).

# Nightly variant

`-Dprofile=development` gives the app id `de.nexumia.Pensum.Devel`
and derives desktop file and metainfo from `data/` with `sed` in
`meson.build`; `-Dbuild_label` shows the commit in the About dialog.
The nightly app has its own data directory, so it never touches the
stable app's tasks.

# Release

Every pull request users notice adds a fragment to `changelog.d/`.
The first release, 0.1.0, is in the metainfo already: push the tag
`v0.1.0` after merging the first pull request, then add the repository
to phosh-apps.

# Screenshots

`release.toml` lists them; CI takes each at 360×720 and 1000×700,
light and dark, from the built Flatpak with `PENSUM_DEMO=1`: the app
writes the made-up dataset of `pensum/demo.py` (dated today, fixed
list ids `demo-garden`, `demo-website`, `demo-calls`,
`demo-errands`) into a temporary directory and shows it. Never real
tasks.

| Shot | Actions |
|---|---|
| `today` | – |
| `task` | `app.show-current-task` |
| `lists` | `app.show-lists` |
| `project` | `app.show-list('project:demo-garden')` |
