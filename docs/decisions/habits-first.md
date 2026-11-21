---
type: Decision Record
title: Day Planner is the owner's one app for building habits
description: The owner wants one native Linux app to build habits. That app is Day Planner with QuestArc's journeys as its start; the task manager's finished features stay, M3 is on hold, simple counters are dropped, and sync with Super Productivity stays because the owner uses it on the desktop.
tags: [decision, plan, journeys, questarc]
generated: { by: claude-code/2.1.326, at: 2026-11-20 }
---

# Status

Accepted by the owner on 2026-11-20.

# Context

The owner wants one app to build habits. QuestArc's standalone web app
is not it on a Linux phone: a web app works badly there, and QuestArc
decided against a Flatpak of its own because Day Planner is the Flatpak
home of the journeys
([QuestArc decision](https://github.com/nexumia-de/quest-arc/blob/main/docs/decisions/standalone-app.md)).
Two ways were weighed: move Day Planner into QuestArc's repository and
drop the task manager's features, or integrate the journeys better
here.

# Decision

1. **Day Planner is the native habit app, in this repository.** A habit
   app needs what Day Planner has: repeating tasks to tick, the dataset,
   backups and the journey pages; QuestArc's engine computes progress
   from those tasks. Moving the code into QuestArc's TypeScript
   repository would change nothing a user sees and mix two builds.
2. **Journeys come first.** The journeys become the start page, and the
   next work is what makes them feel at home: reminders (#13), the strip
   on Today and the moment of the tick (#57), the start page (#78),
   German for Day Planner's own texts (#79) and the user's own habits
   (#80, QuestArc#89).
3. **Nothing finished is removed.** Time tracking, search, archive and
   tags are done and cost nothing; cutting them out would be work
   without a gain.
4. **M3 is on hold**: focus mode, break reminder, worklog, daily
   summary, project notes, attachments, planner days, menu folders.
   Their issues stay open.
5. **Simple counters are dropped** (#21): the journeys are Day
   Planner's habits. The `simpleCounter` slice stays in the data
   untouched.
6. **Sync stays** (M4): the owner uses Super Productivity on the
   desktop, so phone and desktop must see the same journeys. Its
   writing part follows the journey work.

# Consequences

- The [roadmap](../roadmap.md) has the goal _Habits first_ before M3
  and M4's writing part.
- Day Planner keeps following QuestArc's releases
  ([coverage](../questarc-coverage.md)); that cost is accepted. If it
  grows, showing QuestArc's shared screens in a web view is the
  alternative to weigh, at the price of the native look.
