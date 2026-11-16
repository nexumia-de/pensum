---
type: Concept
title: The Valley, the home of the journeys
description: How Day Planner draws QuestArc's Valley - moments as places along one path, from the engine's valley view and layout; the growing card, the moment a journey starts from, the demo places.
tags: [journeys, questarc, valley, ui]
resource: ../pensum/ui/journey/valley.py
generated: { by: claude-code/2.1.318, at: 2026-11-16 }
---

# The Valley

Since QuestArc 4.2.0 the home of the journeys is the Valley[^1]: one path
through the day, a place for every moment. Nothing is placed or counted
here; Day Planner asks the engine and draws.

- **The places** are the engine's `valley` view (`GameView.valley`): in
  the order of the day, each with its side, hue (a name of
  `palette.json`), one to three things (the first journey's ladder, the
  version that stands per journey), the `lantern` sign, and `growing`.
  The name is the user's name, else "After <words>" or "At <time>"
  (`pensum/game/moments.py`).
- **The geometry** is the engine's too: `engine.valley_layout(sides,
  things, 360, height)` runs `engine-cli.mjs` with `{"valley": …}` and
  returns the path, and per place its band, slot, boxes for every thing,
  bay, ground patches, doorstep and name box, in units of a scene 360
  wide. The height is two thirds of the window, never less than 480 (the
  layout's checks hold from there); with more than six places, or with
  things behind the first, the engine returns a longer scene and the
  page scrolls. Layouts are cached per request.
- **Drawing** (`pensum/ui/journey/valley.py`, `ValleyScene`): a
  `Gtk.DrawingArea` as wide as the page up to 440 px, its height
  following the width. Back to front: the ground (each place's `tint`,
  passing into the next one's), the path and bays in one colour (the
  surface in the light style, the hue's `tint-strong` in the dark one),
  the things (second and third first, so the first stands in front), the
  flowers of the growing thing (only where `growing_flowers` is on: the
  place's own page, not the Valley, QuestArc #152), the lit lantern in
  the first thing's slot (`place-lantern-<side>`, its picture reaches
  past the box, so the stylesheet lets the picture overflow), the names
  (Pango, two lines, then an ellipsis; **bold** for the growing place:
  the shape, not the colour, tells). Pictures are QuestArc's, drawn by
  `art.py` with librsvg in libadwaita's colours and the place's hue.
- **Taps**: one flat button of at least 44 px per place over the picture
  (its band, edge to edge), named in words for screen readers ("After
  lunch: A lookout platform, version 2 of 5. Growing here. The lantern is
  lit: the routine runs by itself."); the drawing is hidden from them.
- **Below the scene** the growing step as a card (`growing_card.py`):
  "Growing here · Station 2 of 4", the plan sentence, the condition in
  words, one line of state; a tap opens the journey's own page. Then the
  banners of the journey. **A New Moment** is the main action (outlined
  while a journey is active). At 720 sp and wider the scene stands on the
  left and the card on the right (an `AdwBreakpoint` on the page's box).
- **A moment at the start** (`start_page.py`, `moment_rows.py`): the user's
  moments as options and **A new moment** with the journey's example
  words ("After …") or a fixed time; **Start** writes the moment
  (`nameAnchor`) and the run's anchor (`startJourney` with `anchor`) in
  one change. A journey from before anchors asks once
  (`confirm_card.py`): **Yes, That Is It** writes the suggested words,
  **Change the Words** opens `moment_page.py`; the answer ties every run
  of the journey to the moment (`confirmAnchor`).
- **The place** (`place_page.py`, `place_piece.py`; screen 0b): a place
  without a growing journey opens here, also where nothing stands yet.
  The Valley's layout for one place (230 units high; `engine.valley_layout`
  with one side), every thing at the place with its flowers, and the
  **pencil** (44 × 44, on the free side of the path, top corner) that opens
  "Change this moment". Under it, once for each thing, the versions that
  stand as small pictures with their numbers and the words ("A well house
  stands"; a version that stands for a skipped stage is listed as "already
  yours"); where the place holds more than one thing each row is headed by
  its journey's title. One card **Your routine here**: the steps in words,
  each **Still followed** or **Runs by itself** (then also "Nothing is
  ticked or counted for it any more."), what waits with **Waiting**, or
  "Nothing stands here yet." Then **Extend This Moment**
  (`ChoosePage(anchor_id)` → the start page with the moment chosen). The
  journey's own page (`run_page.py`) is set in the same piece, with the
  versions of its own thing only. At 720 px and wider the piece stands on
  the left and the card on the right (an `AdwBreakpoint`), narrower one column.
- **Change this moment** (`change_moment_page.py`; screen 0a): the words
  ("After …" or a fixed time) and a name, saved with **Save**
  (`nameAnchor`); under them the places in the order of the day as a
  numbered list (this one bold, "This moment"), **Move Earlier** and
  **Move Later** (disabled at the ends), **Side of the path** (Left, Right),
  **Colour** (the eight hues: a swatch and the name, so the name carries
  it) and **Use the suggestion** (only while something was chosen). Each
  change is written at once through the engine's `movePlace`,
  `choosePlaceSide`, `choosePlaceHue` and `withdrawPlace` as
  `place:<anchorId>` records, only what the user picked; the fields above
  keep what was typed. **Remove This Moment** appears only where nothing
  stands (`removeAnchor`, with Undo that writes the records back). The
  hue belongs to the place, not the journey.
- **Not done here** (pensum#64): the plan sentence still uses the
  journey's own words, not the moment's; chains ("Tie the new step to"),
  stay and skip, long break, graduation (so the questions that are due at
  a moment, banners of flow F, are missing on the place), German.

# Demo places

`PENSUM_DEMO=1` has the growing journey at "sitting down at my desk".
`PENSUM_DEMO_VALLEY` (`pensum/demo_valley.py`) adds the other places as
records: `1` (only the desk), `3` (default: getting up with a lit
lantern, the desk, an evening moment where a journey waits), `6` and
`6-stacked` (two and three things at some places). The waiting journeys
started before the growing one, so it stays the active journey. Screenshots
use these, never real tasks; `app.show-run`, `app.show-place('<moment>')`
and `app.show-change-moment('<moment>')` open the pages for
`screenshot.sh -a` (the moments of the demo: `getting-up`, `desk`,
`lunch`, `dinner`, `bedtime`, `evening`).

[^1]: QuestArc docs/behaviour.md screens 0, 0a, 0b and 3; docs/journey-design.md "The place piece" and "The sign of a place"; docs/game-rules.md §8 (QuestArc 4.2.0, nexumia-de/quest-arc#114).
