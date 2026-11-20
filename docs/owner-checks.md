---
type: Checklist
title: Owner checks
description: What only the owner can check or do - on the phone, with their own data and devices, with an account or a secret, or in another project - with the issue each item came from; nothing here has been run by an agent.
tags: [checks, phone, owner, release]
generated: { by: claude-code/2.1.330, at: 2026-11-22 }
---

# Owner checks

Agents cannot reach the phone, the owner's data, accounts or secrets,
or release other projects. What an agent could test is tested (CI jobs
`test` and `real-app`); what is left is listed here, one short list per
issue. None of these items has been run by an agent. Tick an item by
removing it, or reopen the issue if a check fails.

## Round trip with the owner's data (#2)

CI imports Pensum's exports into Super Productivity 20.0.0 and reads
its export back ([checked](super-productivity-data.md#checked-against-a-real-super-productivity)).
Left:

- [ ] Export the desktop's Super Productivity, import it in Day Planner
      on the phone, change tasks (add, subtasks, done, timer, tags,
      planned day, delete a project), export, import on the desktop:
      no repair dialog, everything as on the phone.
- [ ] If a 19.3.x Super Productivity is still in use anywhere: the same
      import there (CI tests 20.0.0 only).

## Reminders on the phone (#13)

Built and tested on a private session bus with a test notification
server ([reminders](reminders.md)). Left, on the phone with the
installed Flatpak:

- [ ] A task reminder comes at its time while Day Planner's window is
      closed; **Done** marks the task done, **Snooze** brings it back.
- [ ] After a reboot Phosh starts the portal's autostart entry and the
      windowless application keeps running.
- [ ] With the screen off: does the reminder come at its time or only
      when the phone wakes? (Nothing in the sandbox sets a wake alarm.)
- [ ] The notification's buttons on the lock screen.
- [ ] Memory of the windowless process over a day.

## A journey walked in Super Productivity's plugin (#64)

Day Planner covers QuestArc 4.3.1 ([coverage](questarc-coverage.md));
its flow tests use datasets written by the engine's actions, and CI
imports the demo dataset with QuestArc's records into Super
Productivity 20.0.0. Left, with QuestArc's plugin installed there:

- [ ] Start a journey in the plugin, tick a few days, export, import in
      Day Planner: the journey continues there and is not read-only.
- [ ] Tick a day in Day Planner, export, import in Super Productivity:
      the plugin shows the same day.

## Own habits need a QuestArc release (#80)

The quick form and journey files are built in Day Planner
([own journeys](own-journeys.md)) against QuestArc's main branch, but
QuestArc's latest release, 4.3.1, does not have them, so Day Planner
hides them. Apps pin only releases. Left:

- [ ] Release QuestArc with quest-arc#89 and #40 (the quick form and
      journey files); then let an agent pin that archive in
      `de.nexumia.Pensum.yml`, run `tests/test_own_journey.py` against
      it (it skips today) and add the changelog fragment
      "Build a habit of your own as a journey …".
- [ ] After that: make a habit with the form on the phone, walk a few
      days, export, and check what Super Productivity's plugin shows
      (it does not read own journeys before quest-arc#40 reaches it).
