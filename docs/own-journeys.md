---
type: Concept
title: Own journeys
description: How Day Planner lets the user build a habit of their own as a journey - the quick form, the journey QuestArc's engine writes from its answers, the journey:<id> record, and a journey file in and out; what is the engine's and what is Day Planner's.
tags: [journeys, questarc, quick-form, import, export]
resource: ../pensum/game/own.py
generated: { by: claude-code/2.1.326, at: 2026-11-20 }
sources:
  - id: questarc
    title: QuestArc 4.4.0, docs/story-format.md (the quick journey), docs/data-model.md (journey records), docs/behaviour.md (screen 2a)
    url: https://github.com/nexumia-de/quest-arc/tree/v4.4.0/docs
---

# Own journeys

Beside the built-in journeys the user can walk journeys of their own
(#80): a habit put in a few answers, or a journey file. Nothing about
them is decided in Day Planner: QuestArc's engine writes the journey,
checks it and names its record[^questarc]; Day Planner adds the pages.

## The quick form

**Choose a Journey → Your Own Habit** (`quick_page.py`,
`app.show-own-habit`): one scrolling page with a group per question,
nothing focused when it opens.

| Question | Answer |
| --- | --- |
| What do you want to do? | the action in the user's words, at most 80 characters: after "I will" in English, the infinitive in German ("lesen") |
| After what? | the moment, at most 40: after "After" in English, the dative after "Nach" in German |
| How should it grow? | minutes, pages, times or "it stays the same"; a first and a last step; the engine proposes the steps between them (`quickSteps`) and the user may change them (at most six) |
| How often? | every day, every 2 or 3 days, or chosen weekdays |
| Name and what it builds | the journey's name (40) and one of QuestArc's ladders |

**Look at the Steps** asks the engine for the journey (`quick`, with
QuestArc's `ui.quick.…` texts in the language its texts are shown in)
and shows every step as its plan sentence (`quick_preview.py`), with the
engine's kind hint when the first step is not tiny. **Keep This
Journey** writes the record and goes on to the start page, where the
moment is already filled with the user's words.

## Records

A journey of the user's own is one QuestArc record, `journey:<id>`, in
`pluginUserData` like every other ([journeys](journeys.md)). `keepJourney`
gives it after the journey checker; with an error, or with a built-in
journey's id, nothing is written and the reason is told. The quick
form's ids start with `own-`.

`pensum.game.engine.host_input` tells `pensum.game.content` the own
journeys of the dataset on every evaluation: `content.journeys()` lists
them after the built-in ones, never in place of one, and `content.t`
reads their texts (the user's language, English behind a missing key).
The engine gets only the built-in journeys as `journeys`; the own ones
reach it as records.

## A journey file

**Import a Journey File** on the Choose page keeps a story-format-3
file the same way (`own_file.py`). An own journey's preview has
**Export as a File**, which writes the record as QuestArc reads it, and
**Remove This Journey** with Undo: `forgetJourney` withdraws the record
only while no run uses the journey, so what was walked stays readable.

## Open

- QuestArc's plugin does not yet read `journey:<id>` records into its
  list of journeys and texts (QuestArc #40), so a run of an own journey
  that reaches Super Productivity by a backup is not shown there.
- No editor: a kept journey is changed by exporting, editing and
  importing it under a new id (QuestArc #89, step 2).

[^questarc]: QuestArc 4.4.0: `packages/engine/src/quick.ts`, `own-journeys.ts`, `cli-gjs.ts`.
