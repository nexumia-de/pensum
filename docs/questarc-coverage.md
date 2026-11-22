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
**n/a** (belongs to Super Productivity's plugin host only, or not in
QuestArc's screens either), **waits** (on a Day Planner feature named by
its issue). Files are under `pensum/ui/journey/` unless a path says otherwise.

## Engine requests and actions

| Request / action | What the user does | Status | Where |
| --- | --- | --- | --- |
| `evaluateHost`, `diff` | everything shown; the toast after a change | covered | `model.py`, `pensum/game/engine.py` |
| `guardWrite` | (every write checked; a newer QuestArc's run is never written) | covered | `model.write`, `pensum/game/stages.py` |
| `texts` | QuestArc in German (locale from `LC_ALL`, `LC_MESSAGES`, `LANG`) | covered | `pensum/game/content.py` |
| `valley` | the Valley's geometry | covered | `page.py`, `place_piece.py` |
| `nameAnchor` | name or rename a moment | covered | `start_page.py`, `change_moment_page.py` |
| `anchorRun` | tie a new step to a step at the same moment (a chain) | covered | `start_page.py` (`startJourney`'s `anchor.after`) |
| `confirmAnchor` | confirm the moment of a journey from before moments | covered | `confirm_card.py` |
| `removeAnchor` | remove a moment where nothing stands | covered | `change_moment_page.py` |
| `movePlace`, `choosePlaceSide`, `choosePlaceHue` | earlier or later, side, colour of a place | covered | `change_moment_page.py` |
| `choosePlaceKind`, `withdrawPlaceKind`, `withdrawPlace` | what grows at a place; the suggestion | covered | `change_moment_page.py`, `build_page.py` |
| `choosePlaceMarker` | what hangs (hidden while only flowers exist) | covered | `change_moment_page.py` |
| `startJourney` | start a journey at a moment, reason, start day or a picked date | covered | `start_page.py` |
| `bindStage` | Create the task, use an existing one; also for a habit whose task is gone | covered | `setup_page.py`, `pensum/game/stages.py` |
| `continueJourney` | Continue at a met station; finish the journey | covered | `continue_page.py` |
| `stayHere` | Stay Here a While | covered | `continue_page.py` |
| `skipStage`, `undoSkip` | I Already Do This; Do This Station After All | covered | `setup_page.py`, `station_page.py` |
| `carryOn`, `callItAPause`, `stepBack` | the card after a long break; Start Smaller | covered | `come_back.py`, `smaller_page.py` |
| `pauseJourney`, `resumeJourney`, `endJourney` (+ Undo) | pause, resume, end | covered | `run_page.py`, `banners.py`, `shelf_page.py` |
| `repeatPause` | (pausing the bound repeat pauses the journey) | covered | `model.py` |
| `reminderSeen` | (the reminder of a followed task or habit is recorded) | covered | `model.py`, `pensum/game/reminders.py` |
| `answerCheckin` | the weekly look back, also a habit's | covered | `checkin_page.py` |
| `graduate`, `graduateLater` | Let It Graduate (keep repeating or end the repeat); Not Now | covered | `graduate_page.py`, `habits.py` |
| `answerStill`, `bringBack` | "Does it still run by itself?"; Bring It Back | covered | `still_page.py` |
| `chooseBuild` | what a journey builds: at the start, and from the menu without a moment | covered | `start_build.py`, `build_page.py` |
| `checkPlan` | the plan check at the start and from the menu | covered | `start_page.py`, `plan_check.py` |
| `pairStage` | Pair it with | covered | `pair_row.py` (set-up, station details) |
| `withdraw` | Undo (end, change of moment), suggestion | covered | `run_page.py`, `change_moment_page.py` |

## Screens

| QuestArc screen / flow | Status | Where / what is missing |
| --- | --- | --- |
| 0 Home: the Valley, growing card, A New Moment | covered | `page.py`, `valley.py`, `growing_card.py` |
| 0 Home: habit banners (still, graduate, habit look back) | covered | `habits.py` |
| 0 Home: habit fade (reminder no longer needed) | covered | `habits.py`, `reminder_banner.py` |
| 0a Change this moment | covered | `change_moment_page.py` |
| 0b The place, Extend This Moment | covered | `place_page.py`, `place_piece.py` |
| 1 Welcome | covered | `page.py` |
| 2 Choose a journey, preview | covered | `choose_page.py` |
| 3 Start: moment, reason, start day | covered | `start_page.py` |
| 3 Start: **Pick a date** (today or later) | covered | `start_page.py` |
| 3 Start: **Tie the new step to** (chain) | covered | `start_page.py` |
| 3 Start: plan check (optional) | covered | `plan_check.py` |
| 3 Start: what you build, **Change**; "builds another of the same kind" | covered | `start_build.py` |
| 3a What you build | covered | `build_page.py` |
| 3b Plan check page (menu) | covered | `plan_check.py` |
| 4 Journey: build in its place, versions, state in words | covered | `run_page.py`, `place_piece.py`, `build.py` |
| 4 Journey: plan sentence with the moment's words and the pairing | covered | `pensum/game/sentences.py` |
| 4 Journey: "already yours" under a skipped version | covered | `build.py` |
| 4 Journey: staying / started smaller hints on the card | covered | `card.py` |
| 4 Journey: the moment of the tick (animation), build beside the card at 720 px | covered | `tick.py`, `run_page.py` |
| 4 Journey: read-only journey | covered | `read_only.py` (#58) |
| 4 Banners: paused, hard week (with the plan for the obstacle), look back, nugget | covered | `banners.py` |
| 4 Banners: reminder suggestion and fade | covered | `banners.py`, `reminder_banner.py` |
| 5 Station details (skipped, undo skip, left, pair field, plan for the obstacle) | covered | `station_page.py` |
| 6 Weekly look back (last days, answers row, the habit's, every four weeks) | covered | `checkin_page.py`, `answers_row.py` |
| 7 Shelf (habits with last days and run, Let It Graduate, graduated habits, Bring It Back, brought back) | covered | `shelf_page.py` |
| 7 Shelf: **Set up the task** for a habit whose task no longer repeats | covered | `shelf_page.py`, `setup_page.py` |
| 8 Settings: remove QuestArc's data | covered | `pensum/preferences.py` |
| 8 Settings: build in the side panel | n/a | Super Productivity's side panel |
| 9 How it motivates you | covered | `motivates_page.py` |
| B Set up the task, unsupported repeat | covered | `setup_page.py` |
| B the task is gone; its repeat ended (after Start Smaller) | covered | `setup_page.py`, `stages.binding_problem` |
| B the earlier station's task stays (**Open the earlier task**) | covered | `setup_page.py` |
| B I Already Do This | covered | `setup_page.py` |
| B Pair it with | covered | `pair_row.py` |
| B reminder sentence | covered | `setup_page.py` |
| C Continue and Stay Here a While, the suggestion | covered | `continue_page.py` |
| C after a step back: take up the step left | covered | `continue_page.py` |
| C finished: "the weekly question goes on" | covered | `continue_page.py` |
| D long break card; Start Smaller page | covered | `come_back.py`, `smaller_page.py` |
| E pause and resume | covered | `run_page.py`, `banners.py` |
| F graduation, the question, bring back | covered | `graduate_page.py`, `still_page.py`, `habits.py` |
| H reminders: recorded for graduation | covered | `pensum/game/reminders.py` |
| H reminders: suggested, faded | covered | `reminder_banner.py`; the reminder itself is Day Planner's ([reminders](reminders.md)) |
| G problems: engine missing or failing | covered | `page.py` |
| G problems: a page out of date | covered | pages return to the journey or say "gone" (`ui.error.gone`) |
| G problems: "This journey was updated; you continue at …" | n/a | in behaviour.md, but no text or screen in QuestArc 4.3.1 |
| Messages after a completion (one text per event) | covered | `pensum/game/sentences.py` |
| Strip on Today | covered | `today_strip.py` (Day Planner's "build at a glance") |
| Plugin's context menu "Use for current station", side panel, settings entry | n/a | Super Productivity only |

## Texts and language

| What | Status | Where |
| --- | --- | --- |
| QuestArc's English texts (`content/i18n/en.json`, journeys' `en`) | covered | `pensum/game/content.py` |
| German (`de.json`, journeys' `de`), the plan form `.plan` | covered | `texts` request, `pensum/game/sentences.py` |
| Sentences about Super Productivity's menus replaced by Day Planner wording | covered, English and German ([translations](translations.md)) | `card.py`, `setup_page.py`, `smaller_page.py`, `continue_page.py`, `graduate_page.py`; `po/de.po` |
| Titles of what a journey builds and of the colours (`ui.art.ladder.*`, `ui.art.hue.*`), "… stands" (`ui.build.words.*`) | covered | `pensum/game/content.py`, `art.build_words` |

## Still open

Nothing of QuestArc 4.3.1. Left for the owner: Day Planner's own
reminders on the phone and a journey walked in Super Productivity's
plugin and continued here ([owner checks](owner-checks.md), #13, #64).
