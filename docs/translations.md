---
type: Concept
title: Translations
description: How Day Planner's own texts are translated - gettext with the domain pensum, marked with _() and N_(), po/de.po, read from the source tree in development and compiled by meson for the Flatpak; what is German so far and what is still English.
tags: [translations, gettext, german, i18n]
resource: ../pensum/i18n.py
generated: { by: claude-code/2.1.326, at: 2026-11-20 }
---

# Translations

Day Planner shows texts from two sources. **QuestArc's texts** (the
journeys, their pages' words) come from QuestArc in English and German
through the engine's `texts` request ([journeys](journeys.md)).
**Day Planner's own texts** are translated here with gettext (#79).
Both follow the same locale: `LC_ALL`, `LC_MESSAGES`, `LANG`.

## How it works

- `pensum/i18n.py`: `_("text")` gives the text in the user's language,
  the English text without a translation. `N_("text")` only marks a
  module constant; `_()` translates it where it is shown, because the
  language is not known when the module is read (the tests change it).
- Domain `pensum`. Installed, the catalogues are compiled into
  `share/locale/<language>/LC_MESSAGES/pensum.mo` by `po/meson.build`
  (`config.LOCALE_DIR`). From the source tree `po/<language>.po` is
  read directly, so a development run and the tests need no build.
- `po/POTFILES.in` lists the files with marked texts, `po/LINGUAS` the
  languages, `po/pensum.pot` is the template.

Update the template after marking texts:

```sh
xgettext --from-code=UTF-8 --keyword=_ --keyword=N_ --add-comments=Translators --package-name=pensum -o po/pensum.pot -f po/POTFILES.in
```

Merge it into a catalogue:

```sh
msgmerge --update po/de.po po/pensum.pot
```

A test checks that every text of the template has a German
translation (`tests/test_game.py`).

## Wording

German uses "du", like QuestArc's German texts, and QuestArc's words:
Reise, Station, Aufgabe, Moment, Wiederholung. A page of Day Planner
that is still English is named by its visible title in quotes (the
page „Repeat“) until it is translated.

## What is German

- **Step 1, done**: Day Planner's own sentences on the journey pages
  (set-up, continue, start smaller, graduation, the paused banner, the
  status pages, the hint on the card), the weekday names in a
  schedule, "Journeys" in the sidebar and the journey preferences.
  QuestArc's titles of what a journey builds and of the colours are
  shown in German too (`content.ladder`, `content.palette`, the keys
  `ui.art.ladder.*` and `ui.art.hue.*`), and "A hut stands" uses
  QuestArc's own words and grammar (`ui.build.words.*`,
  `ui.grammar.singular`).
- **Step 2, done** (#79): the task manager's pages (lists, task page,
  Repeat page, search, archived projects, sync, preferences, dialogs and
  toasts), the About dialog, the reminder notification and the
  background reason, the reminder options, and the error messages of
  backup and sync files that the page shows verbatim. The Repeat page's
  sentences are whole msgids with `{n}`, `{rule}` and `{date}`
  placeholders; ordinals are `{n}th`, `{n}st`, `{n}nd`, `{n}rd` (German
  "{n}."). Counts have no plural forms: a "1 …" text and a "{count} …"
  text are chosen in the code.
- **Still English**: the `.desktop` file and the metainfo (they are
  read as plain files by the nightly `sed` in `meson.build`, the CI
  validators, `tests/test_metadata.py` and the release script; making
  them gettext templates is a separate change), dates and months
  written by `strftime` (they follow the process locale, not the
  catalogue), the duration units "h" and "m", and the names the user
  gave projects, tags and tasks.

## Found on the way

gjs prints in the locale's character set. With a locale that is not
installed (a Flatpak without its language pack, the cloud container)
QuestArc's German texts came back with "?" for every umlaut. The engine
gets its language from the request, so Day Planner now runs it with
`LC_ALL=C.UTF-8` and reads its answer as UTF-8 (`pensum/game/engine.py`).
