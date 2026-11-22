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
