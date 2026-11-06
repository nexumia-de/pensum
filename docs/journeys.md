---
type: Concept
title: QuestArc's journeys in Day Planner
description: How Day Planner shows QuestArc's journeys natively - the engine through gjs, the choice records in pluginUserData, setting up a stage's task with its repeat rule, the pages, and how to run it in development.
tags: [journeys, questarc, game, gjs]
resource: ../pensum/game/
generated: { by: claude-code/2.1.318, at: 2026-11-06 }
---

# QuestArc's journeys in Day Planner

[QuestArc](https://github.com/nexumia-de/QuestArc) turns a habit into a
journey of small stages. Day Planner shows the same journeys natively,
on the same data as QuestArc's Super Productivity plugin (pensum#38,
#39, #40). The game logic exists once, in QuestArc's TypeScript engine;
Day Planner adds no second implementation.

## How it fits together

- **Engine:** `pensum/game/engine.py` runs QuestArc's `engine-cli.mjs`
  with `gjs` from the GNOME runtime: one JSON request on stdin, the
  answer on stdout ([QuestArc decision](https://github.com/nexumia-de/QuestArc/blob/main/docs/decisions/engine-in-gjs.md)).
  Requests: `evaluateHost` (the dataset's live and archived tasks,
  repeat rules and choice records as they are; the engine builds its
  snapshot), `diff` (events between two views, for the toast) and
  `action` (the records a user action writes: `startJourney`,
  `bindStage`, `continueJourney`, `pauseJourney`, `resumeJourney`,
  `endJourney`, `repeatPause`, `answerCheckin`, `setMode`, `withdraw`).
  So both hosts write the same records.
- **Records:** QuestArc's choice records are entries of the dataset's
  `pluginUserData` slice with id `questarc:<key>`, the value as JSON
  text, `GZ1:<base64 gzip>` from 1024 characters on, `''` for a
  withdrawn record (`pensum/game/records.py`). They travel with every
  backup and import into Super Productivity unchanged, where the plugin
  reads them.
- **Content:** the built-in journeys (every file in
  `content/journeys/`, each with its own texts and optional `author`)
  and the app texts (`content/i18n/en.json`) come from QuestArc's
  release archive (`pensum/game/content.py`). Day Planner uses
  QuestArc's texts; only the sentences about Super Productivity's own
  menus are replaced by Day Planner wording.
- **Stage tasks:** Day Planner can create repeat rules, so **Create
  the Task** makes the task ("Getting up: drink a glass of water") and
  its repeat rule from the stage's suggested schedule in one go and
  binds both (`pensum/game/stages.py`). A journey follows only rules
  that repeat daily, every 2–7 days, or on chosen weekdays every week,
  without repeat-from-completion or wait-for-completion (QuestArc game
  rules §2). Pausing the bound rule writes a pause record
  (`repeatPause`).
- **Updates:** after each change the window asks the model
  (`pensum/ui/journey/model.py`) to evaluate after 300 ms in a thread;
  the request is made on the main thread, a late result from an older
  request is dropped. Without any QuestArc record the engine never runs.
- **When the journey comes forward:** only when the engine reports a new
  completion of the current station's own task (`event.completion` or
  `event.welcome-back`); then, after the toast, the journey page is
  shown. Every other change (other tasks, lists, an import or sync with
  several completions at once, `event.progress-summary`) leaves the user
  where they are, with the toast only. QuestArc's plugin shows only the
  toast (its behaviour, flow A); the owner asked for this in Day
  Planner on 2026-11-06.
- **Listening pages:** a pushed journey page that redraws on changes
  subscribes with `JourneySubpage.listen()`, which drops the subscription
  once the page is off the navigation stack. A popped `AdwNavigationPage`
  is not destroyed while the model still holds its callback, so a
  "destroy" handler never ran: the set-up page stayed subscribed after
  its task was created and showed the journey after every change in the
  task lists.

## Pages

`pensum/ui/journey/`, one file per page, every page pushed on the one
navigation view so a swipe goes back:

- **Journeys** (sidebar, `app.show-journey`): the welcome with calm or
  game, the empty state with **Choose a Journey**, or the active
  journey: banners (paused, a hard week, weekly look back, a new
  nugget), the current station's card (plan, progress bar and words,
  the last due days, runs, guardian in the game, hint, the user's
  reason) and the path from the goal at the top to the start at the
  bottom. The bottom bar holds the main action (**Continue**, **Set Up
  the Task**, **Change How Often**); the menu holds pause or resume,
  end (with Undo), the shelf and how QuestArc motivates you. The level
  is the title's subtitle in the game.
- Choose and preview, start (own reason, start day), set up, continue
  and finished, station details, weekly look back (1–7 or skip), shelf,
  how it motivates you.
- Preferences → Journeys: calm or game, and removing the journey data
  (asks first: it cannot be undone).

The GTK path draws each station's node with Cairo in the theme's accent
colour (done, met, current) or the dimmed text colour (ahead); every
node also has its state in words. Closed banners are kept in Pensum's
settings (`seen`).

## Development

The engine is found where `PENSUM_QUESTARC_DIR` points (a QuestArc
release archive, or a QuestArc checkout after `npm ci && npm run build`)
and run with `PENSUM_GJS` (default `gjs`); in the Flatpak it is
`/app/share/questarc`, from the release archive the manifest pins
(module `questarc-engine`, QuestArc 3.1.0, updated by the update check).
Without it the page says "Journeys Are Not Installed". On the cloud host gjs comes from the GNOME
runtime through bwrap ([development environment](dev-environment.md)).
Tests that need the engine are skipped without it; CI fetches the
archive the manifest pins, installs gjs and sets
`PENSUM_REQUIRE_ENGINE=1`, so they must pass there. Screenshots: the
demo dataset (`PENSUM_DEMO=1`) has "First Things First" in the game at
its second station with one gap.

## Open

- German texts follow with QuestArc's (QuestArc#39).
- The engine runs once per change; its time on the phone is still to be
  measured (QuestArc#16).
