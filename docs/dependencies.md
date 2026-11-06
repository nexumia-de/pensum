---
type: Reference
title: Bundled dependencies
description: Pensum bundles phosh-toolkit's shared package and QuestArc's engine archive; everything else comes from the GNOME runtime. Super Productivity's default values ship as MIT data.
tags: [dependencies, licensing, flatpak]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Rules

The shared rules are in
[../../phosh-toolkit/docs/licensing.md](../../phosh-toolkit/docs/licensing.md).
CI fails if a module of `de.nexumia.Pensum.yml` is missing here or
installs no licence files.

# Modules

| Module | Version | Licence | Licence files |
|---|---|---|---|
| `phosh-toolkit` | tag `v0.3.0` (commit `c29a2a1`) | GPL-3.0-or-later (own code, same author) | `LICENSE` → `/app/share/licenses/<app id>/phosh-toolkit/` |
| `questarc-engine` | release archive `v3.1.0` (sha256 `acb5a47f…`) | engine AGPL-3.0-or-later (same author); journeys in `content/journeys/` CC BY-SA 4.0 | `LICENSE` → `…/questarc-engine/`, `content/LICENSE` → `…/questarc-journeys/` |

Only `lib/phosh_toolkit/` is installed; Pensum uses `settings`
(`JsonStore`, `app_dir`) and `style` (light/dark)
([shared code](../../phosh-toolkit/docs/shared-connection.md#used-by)).

QuestArc's engine ([journeys](journeys.md)): Only `engine.mjs`, `engine-cli.mjs` and `content/` are installed, to
`/app/share/questarc/`; the runtime's `gjs` runs the engine. The
journeys' authors are named in the app ("Written by …").

# Data from Super Productivity

`pensum/store/sp-defaults.json`: default values transcribed from Super
Productivity 19.3.1 (MIT, © 2018 Johannes Millan), installed with
Pensum's package; its licence text goes to
`/app/share/licenses/<app id>/super-productivity-defaults/`.

# From the runtime (not bundled)

`org.gnome.Platform//51` provides Python 3, PyGObject, GTK 4 and
libadwaita. M4 (sync) will need Argon2id and AES-GCM
([sync files](super-productivity-sync.md#file-envelope)).
