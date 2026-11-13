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
  bottom. **With the game the build replaces the path** (QuestArc#42,
  #57; QuestArc behaviour, screen 4): on top the journey's build in its
  setting and hue (the ladder's standing version, the marker of the
  stage under way, its hanging elements "on" while the stage is ready),
  the row of versions that stand with the next one as an empty step, and
  one line of state in words ("A log stands · a plank bridge is on its
  way"); then the banners and the card. Everything comes from the
  engine's `build` view (`pensum/ui/journey/build.py`); an engine
  without it (the pinned 3.1.0 archive) or calm mode shows the path as
  before. The bottom bar holds the main action (**Continue**, **Set Up
  the Task**, **Change How Often**); the menu holds pause or resume,
  end (with Undo), the shelf and how QuestArc motivates you, and with a
  build **What you build** and **Stations** (the path as its own page,
  `stations_page.py`). The level
  is the title's subtitle in the game.
- Choose and preview, start (own reason, start day), set up, continue
  and finished, station details, weekly look back (1–7 or skip), shelf,
  how it motivates you.
- **What you build** (`build_page.py`, QuestArc behaviour, screen 3a):
  what grows (a ladder), what hangs (lanterns, pennants, flowers;
  flowers are disabled over water with "Only on land") and the colour
  (the palette's hues by name with a swatch). Each change is written at
  once through the engine's `chooseBuild`, only what the user picked; a
  marker that no longer fits a changed ladder is dropped; **Use the
  journey's suggestion** withdraws the record.
- Still open from #57: the strip on Today, the moment of the tick in
  it, the choice on the start page, and the build beside the card at
  desktop width.
- Preferences → Journeys: calm or game, and removing the journey data
  (asks first: it cannot be undone).

The GTK path draws each station's node with Cairo in the theme's accent
colour (done, met, current) or the dimmed text colour (ahead); every
node also has its state in words. Closed banners are kept in Pensum's
settings (`seen`).

## Pictures

QuestArc's pictures are symbolic SVG files in its `content/art/`
(QuestArc decision [shared pictures](https://github.com/nexumia-de/QuestArc/blob/main/docs/decisions/shared-pictures.md),
QuestArc#86, #97): no colours of their own, every shape marked with one
of six roles (`art.ROLES`: `fg`, `accent`, `dim`, `bg`, `tint`,
`tint-strong`), checked by QuestArc's picture checker. Day Planner draws the
same files as the plugin, with librsvg from the GNOME runtime into Cairo
(`pensum/ui/journey/art.py`): a stylesheet fills `fg` with the text
colour, `accent` with the colour of libadwaita's `.accent` class (the
app's indigo, lightened in dark style from libadwaita 1.6 on), `bg`
with the surface the picture stands on (window or card), `dim` with the
text colour mixed 30 % into it and `tint`/`tint-strong` with the accent
mixed 16 %/40 % into it, all made opaque so overlapping shapes stay one
colour. A scene places pictures at fixed spots in three depth bands,
scales with the width and is clipped to its size; a picture in the far
band is drawn with every role in `tint`, one silhouette with the ground
(QuestArc's journey design, "Look and depth bands"). Scenes are composed
from a ladder file (below); QuestArc's first region scenes (a meadow, a
shore) were removed after 3.1.0. Titles become accessible labels. Pictures are found by
name only (`content.art_path`); names cannot leave the folder.

The journey page draws the build with them. The demo
`tests/art_demo.py sizes|sequence-crossing|journey-home|palette` shows
every picture at 48, 32 and 24 px and the ladders; `tests/test_art.py`
checks that a ladder's scene is drawn only in the roles' colours, the
far band in `tint`, and that every class in `content/art/` is a role
Day Planner fills. Both need a QuestArc with `content/art/` (a checkout
of QuestArc's `main`, or a release after 3.1.0); with the pinned 3.1.0
archive the tests are skipped.

```sh
PENSUM_QUESTARC_DIR=$PWD/../QuestArc /usr/bin/python3.12 tests/art_demo.py
```

**Ladders and hues** (QuestArc#42, QuestArc's journey design "Builds and
ladders"): a journey builds one thing in versions, each whole, in the same
slot of the same setting. `art.ladder_scene(ladder, version, progress,
ready, marker, graduated)` composes the scene from `<ladder>.ladder.json`
(`content.ladder`): the setting and its plants, the standing version in
the `build` slot and, while a stage runs, its marker in the foreground:
the first ceil(p × E) elements (`art.elements_shown`; plain posts first,
then the hanging lanterns, pennants or flowers; a line once both its
posts stand), p the stage's best progress so it never loses one; when
`ready` every hanging element in its "on" form (`-lit` picture), the
posts stay plain. `marker` picks the kind (the ladder's default if None);
the lantern after graduation; never a count. `art.build_words` says the
state under the row of versions ("… is on its way", "… is ready"); the
row may show a zoomed part of each version (`row`, `art.draw_part`). A region may take a hue from
`palette.json` (`content.palette`): `art.colours(widget, card, hue)` then
takes `accent`, `tint` and `tint-strong` from the hue's light or dark
value (by `Adw.StyleManager`'s dark state); `fg`, `bg` and `dim` stay
libadwaita's. The demo's parts `sequence-<ladder>[-<marker>]`,
`journey-<ladder>[-ready]` (a static mock of the journey screen) and
`palette` are in `tests/ladder_demo.py`, a palette hue as the second
argument. `tests/test_art.py` checks the composed scenes and that every
hue keeps WCAG contrast against libadwaita's cards in light and dark
(accent 3 : 1, tint-strong 1.5 : 1, the text colour on tint-strong
3 : 1).

Measured on the cloud host (x86_64): the test scene (15 pictures)
takes about 1.8 ms per draw with cached handles and 3.7 ms on the first
draw with parsing, the same with the host's librsvg 2.58 and the
runtime's 2.63.2.

## Development

The engine is found where `PENSUM_QUESTARC_DIR` points (a QuestArc
release archive, or a QuestArc checkout after `npm ci && npm run build`)
and run with `PENSUM_GJS` (default `gjs`); in the Flatpak it is
`/app/share/questarc`, from the release archive the manifest pins
(module `questarc-engine`, QuestArc 3.1.0, updated by the update check).
That archive has no pictures and no `build` view, so the Flatpak shows
the build only once the manifest pins the QuestArc release after 3.1.0
(3.2.0); the tests that need ladders are skipped until then.
Without it the page says "Journeys Are Not Installed". On the cloud host gjs comes from Ubuntu's
package or from the GNOME runtime through bwrap ([development environment](dev-environment.md)).
Tests that need the engine are skipped without it; CI fetches the
archive the manifest pins, installs gjs and sets
`PENSUM_REQUIRE_ENGINE=1`, so they must pass there. Screenshots: the
demo dataset (`PENSUM_DEMO=1`) has "First Things First" in the game at
its second station with one gap.

## Open

- German texts follow with QuestArc's (QuestArc#39).
- The engine runs once per change; its time on the phone is still to be
  measured (QuestArc#16).
