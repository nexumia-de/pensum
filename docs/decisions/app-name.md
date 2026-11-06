---
type: Decision Record
title: App name Pensum
description: The code name is Pensum, Latin for a day's allotted work; app id de.nexumia.Pensum. The visible name is Day Planner.
tags: [decision, name]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Status

Code name accepted (2026-11-05) by the owner, who created
`nexumia-de/pensum` from the suggestions (Pensum, Diurna, Tempora).
The visible name **Day Planner** was chosen by the owner on 2026-11-06
(issue #1).

# Decision

*Pensum* is Latin for "the work allotted for a day". App id
`de.nexumia.Pensum`, Python package and command `pensum`. Users see
**Day Planner**: the `.desktop` `Name`, the metainfo `<name>`, the window
title and the About dialog; the nightly build says "Day Planner
(Nightly)". It must not contain "Super Productivity" (toolkit
[app names](../../../phosh-toolkit/docs/decisions/app-names.md)); the
description says that Pensum reads Super Productivity's backups.

# Consequences

No app named Pensum was found on Flathub (search on 2026-11-04).
