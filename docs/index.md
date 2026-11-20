---
okf_version: "0.2"
---

# Pensum knowledge bundle

[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2) bundle of this app. Shared Phosh knowledge lives in
[../../phosh-toolkit/docs/index.md](../../phosh-toolkit/docs/index.md).
Change history is in [log.md](log.md).

# Plan

* [Roadmap](roadmap.md) - Goals and exit criteria of the milestones; the work items are GitHub issues.
* [Features](features.md) - Every Super Productivity feature, its data and the milestone in which Pensum rebuilds it, or why not.

# Super Productivity

* [Data model](super-productivity-data.md) - Every slice of the dataset with fields and consistency rules, the backup files, how Pensum stores, imports and exports them.
* [Sync files](super-productivity-sync.md) - The WebDAV/local-folder sync format (v2, v3), envelope, compression, encryption, operations, and what Pensum needs to sync.

# Notes

* [Markdown in notes](markdown-notes.md) - What Super Productivity renders in a task's notes, the subset Day Planner shows with Pango markup, checkboxes that can be ticked, links only on a tap, and that the stored note stays as typed.

# Reminders

* [Own journeys](own-journeys.md) - the quick form for a habit of the user's own, the journey QuestArc's engine writes and checks, the `journey:<id>` record, importing, exporting and removing a journey file.
* [Reminders](reminders.md) - `task.remindAt` and a repeat rule's time and reminder as Super Productivity 20 keeps them, the notification with Done and Snooze, the background while the window is closed, what is open on the phone.

# Journeys

* [QuestArc's journeys](journeys.md) - QuestArc's engine through gjs, the choice records in pluginUserData, stage tasks with their repeat rule, the journey pages, development.
* [QuestArc coverage](questarc-coverage.md) - Every QuestArc action, screen and text family and whether Day Planner covers it, with the file and the open issue.
* [The Valley](valley.md) - The home of the journeys: moments as places along one path, drawn from the engine's `valley` view and layout; the growing card, moments at the start, the demo places.

# Translations

* [Translations](translations.md) - gettext for Day Planner's own texts (`pensum/i18n.py`, `po/`), the wording, what is German so far and what is still English.

# Design

* [Visual design](design.md) - Stock libadwaita with Pensum's indigo accent, the screens at 360 px and on the desktop.

# Development

* [Owner checks](owner-checks.md) - What only the owner can check or do (phone, own data, accounts, other projects), per issue; nothing in it has been run by an agent.
* [Bundled dependencies](dependencies.md) - Only phosh-toolkit's shared package; Super Productivity's default values as data.
* [Release channels](release-channels.md) - Stable from tags, nightly from main, screenshots from the demo dataset.
* [Development environment](dev-environment.md) - Hosts, host packages, run, test, screenshot, Flatpak.

# Decision records

* [Decisions](decisions/index.md) - Super Productivity's backup format as storage, name, licence, habits first.
