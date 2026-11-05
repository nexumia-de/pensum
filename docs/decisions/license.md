---
type: Decision Record
title: AGPL-3.0 licence
description: Pensum is AGPL-3.0-or-later like the other apps; Super Productivity's transcribed default values and test fixtures stay MIT.
tags: [decision, license]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Status

Accepted (2026-11-05), following the owner's choice for the other apps.

# Decision

`AGPL-3.0-or-later`, contributions under the terms in
`CONTRIBUTING.md`. AppStream metadata is CC0-1.0. App icon and
symbolic icons were drawn for Pensum.

# Consequences

Pensum copies no code from Super Productivity (MIT). Two kinds of files
come from it and keep its licence, annotated in `REUSE.toml`:
`pensum/store/sp-defaults.json` (default values transcribed as data)
and `tests/fixtures/*.json` (its e2e and validation fixtures). MIT is
compatible with the AGPL; the Flatpak installs the MIT text under
`/app/share/licenses/de.nexumia.Pensum/super-productivity-defaults/`.
