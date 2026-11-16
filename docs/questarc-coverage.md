---
type: Concept
title: QuestArc coverage in Day Planner
description: Every user-facing feature, action, engine request and text family of QuestArc 4.3.1 (plugin and shared screens), and whether Day Planner's journey pages cover it, partly cover it or miss it, with the file and the open issue.
tags: [journeys, questarc, coverage]
resource: ../pensum/ui/journey/
generated: { by: claude-code/2.1.318, at: 2026-11-16 }
sources:
  - "[^behaviour]: QuestArc docs/behaviour.md at quest-arc 3d59bb5 (after v4.3.1)"
  - "[^rules]: QuestArc docs/game-rules.md at quest-arc 3d59bb5"
  - "[^actions]: QuestArc packages/engine/src/actions.ts and cli-gjs.ts, release 4.3.1"
  - "[^ui]: QuestArc packages/ui/src/ui (screens, journey, banners, habit-banners, reminder) at 3d59bb5"
  - "[^changelog]: QuestArc CHANGELOG.md up to 4.3.1"
---

# QuestArc coverage in Day Planner

What a QuestArc user can do in Super Productivity's plugin (the shared
screens of `packages/ui`[^ui], [behaviour](https://github.com/nexumia-de/quest-arc/blob/main/docs/behaviour.md)[^behaviour],
game rules[^rules], changelog up to 4.3.1[^changelog]) and where Day
Planner covers it. Day Planner pins QuestArc 4.3.1's engine and writes
records only through its actions[^actions] ([journeys](journeys.md)).

Status: **covered**, **partly** (what is missing is said), **missing**,
**n/a** (belongs to Super Productivity's plugin host only). Files are
under `pensum/ui/journey/` unless a path says otherwise.

## Engine requests and actions

| Request / action | What the user does | Status | Where |
| --- | --- | --- | --- |
| `evaluateHost`, `diff` | everything shown; the toast after a change | covered | `model.py`, `pensum/game/engine.py` |
| `guardWrite` | (every write checked; a newer QuestArc's run is never written) | covered | `model.write`, `pensum/game/stages.py` |
| `texts` | QuestArc in German | missing (#64) | — |
| `valley` | the Valley's geometry | covered | `page.py`, `place_piece.py` |
| `nameAnchor` | name or rename a moment | covered | `start_page.py`, `change_moment_page.py` |
| `anchorRun` | tie a new step to a step at the same moment (a chain) | missing (#64) | — |
| `confirmAnchor` | confirm the moment of a journey from before moments | covered | `confirm_card.py` |
| `removeAnchor` | remove a moment where nothing stands | covered | `change_moment_page.py` |
| `movePlace`, `choosePlaceSide`, `choosePlaceHue` | earlier or later, side, colour of a place | covered | `change_moment_page.py` |
| `choosePlaceKind`, `withdrawPlaceKind`, `withdrawPlace` | what grows at a place; the suggestion | covered | `change_moment_page.py`, `build_page.py` |
| `choosePlaceMarker` | what hangs (hidden while only flowers exist) | covered | `change_moment_page.py` |
| `startJourney` | start a journey at a moment, reason, start day | covered | `start_page.py` |
| `bindStage` | Create the task, use an existing one | covered | `setup_page.py`, `pensum/game/stages.py` |
| `continueJourney` | Continue at a met station; finish the journey | covered | `continue_page.py` |
| `stayHere` | Stay Here a While | missing (#64) | — |
| `skipStage`, `undoSkip` | I Already Do This; Do This Station After All | missing (#64) | — |
| `carryOn`, `callItAPause`, `stepBack` | the card after a long break; Start Smaller | missing (#64) | — |
| `pauseJourney`, `resumeJourney`, `endJourney` (+ Undo) | pause, resume, end | covered | `run_page.py`, `banners.py`, `shelf_page.py` |
| `repeatPause` | (pausing the bound repeat pauses the journey) | covered | `model.py` |
| `reminderSeen` | (the reminder of a followed task is recorded) | missing (#64) | — |
| `answerCheckin` | the weekly look back | covered | `checkin_page.py` |
| `graduate`, `graduateLater` | Let It Graduate; Not Now | missing (#64) | — |
| `answerStill`, `bringBack` | "Does it still run by itself?"; Bring It Back | missing (#64) | — |
| `chooseBuild` | what a journey without a moment builds | covered | `build_page.py` |
| `checkPlan` | the plan check at the start and from the menu | missing (#64) | — |
| `pairStage` | Pair it with | missing (#64) | — |
| `withdraw` | Undo (end, change of moment), suggestion | covered | `run_page.py`, `change_moment_page.py` |

## Screens

| QuestArc screen / flow | Status | Where / what is missing |
| --- | --- | --- |
| 0 Home: the Valley, growing card, A New Moment | covered | `page.py`, `valley.py`, `growing_card.py` |
| 0 Home: habit banners (still, graduate, habit look back, habit fade) | missing (#64) | — |
| 0a Change this moment | covered | `change_moment_page.py` |
| 0b The place, Extend This Moment | covered | `place_page.py`, `place_piece.py` |
| 1 Welcome | covered | `page.py` |
| 2 Choose a journey, preview | covered | `choose_page.py` |
| 3 Start: moment, reason, start day | covered | `start_page.py` |
| 3 Start: **Pick a date** | missing | — |
| 3 Start: **Tie the new step to** (chain) | missing (#64) | — |
| 3 Start: plan check (optional) | missing (#64) | — |
| 3 Start: what you build, **Change** | missing (#57) | — |
| 3a What you build | covered | `build_page.py` |
| 3b Plan check page (menu) | missing (#64) | — |
| 4 Journey: build in its place, versions, state in words | covered | `run_page.py`, `place_piece.py`, `build.py` |
| 4 Journey: plan sentence with the moment's words and the pairing | missing (#64) | `card.py` uses the journey's own anchor |
| 4 Journey: "already yours" under a skipped version | missing (#64) | — |
| 4 Journey: staying / started smaller hints on the card | missing (#64) | — |
| 4 Journey: the moment of the tick (animation), build beside the card at 720 px | missing (#57) | — |
| 4 Journey: read-only journey | covered | `read_only.py` (#58) |
| 4 Banners: paused, hard week, look back, nugget | covered | `banners.py` |
| 4 Banners: hard week with the plan for the obstacle | missing (#64) | — |
| 4 Banners: reminder suggestion and fade | missing (#64) | — |
| 5 Station details | partly (#64) | `station_page.py`; missing: skipped, undo skip, left, pair field, plan for the obstacle |
| 6 Weekly look back | partly (#64) | `checkin_page.py`; missing: last days, answers row and trend, the habit's look back, every four weeks |
| 7 Shelf | partly (#64) | `shelf_page.py`; missing: habits' last days and run, graduated habits, Let It Graduate, Bring It Back, set up a habit's task, brought back |
| 8 Settings: remove QuestArc's data | covered | `pensum/preferences.py` |
| 8 Settings: build in the side panel | n/a | Super Productivity's side panel |
| 9 How it motivates you | covered | `motivates_page.py` |
| B Set up the task, unsupported repeat | covered | `setup_page.py` |
| B I Already Do This | missing (#64) | — |
| B Pair it with | missing (#64) | — |
| B reminder sentence | missing (#64) | — |
| C Continue and Stay Here a While, the suggestion | partly (#64) | `continue_page.py` has Continue only |
| C after a step back: take up the step left | missing (#64) | — |
| C finished: "the weekly question goes on" | partly | `continue_page.py` |
| D long break card; Start Smaller page | missing (#64) | — |
| E pause and resume | covered | `run_page.py`, `banners.py` |
| F graduation, the question, bring back | missing (#64) | — |
| H reminders | missing (#64) | — |
| G problems: engine missing or failing | covered | `page.py` |
| G problems: a page out of date | partly | pages return to the journey |
| Messages after a completion (one text per event) | covered | `pensum/game/sentences.py` |
| Strip on Today | missing (#57) | — |
| Plugin's context menu "Use for current station", side panel, settings entry | n/a | Super Productivity only |

## Texts and language

| What | Status | Where |
| --- | --- | --- |
| QuestArc's English texts (`content/i18n/en.json`, journeys' `en`) | covered | `pensum/game/content.py` |
| German (`de.json`, journeys' `de`), the plan form `.plan` | missing (#64) | — |
| Sentences about Super Productivity's menus replaced by Day Planner wording | covered | `card.py`, `setup_page.py`, `continue_page.py` |
