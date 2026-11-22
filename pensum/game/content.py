"""QuestArc's content shipped with Pensum: the engine files, the built-in
journeys (every file in content/journeys/, each with its own texts) and
the app texts (content/i18n/en.json). Found in /app/share/questarc in
the Flatpak, or where PENSUM_QUESTARC_DIR points (a QuestArc release
archive or checkout). No GTK."""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

DEFAULT_DIR = "/app/share/questarc"
_PLACEHOLDER = re.compile(r"\{([a-zA-Z][a-zA-Z0-9-]*)\}")


def directory():
    return Path(os.environ.get("PENSUM_QUESTARC_DIR") or DEFAULT_DIR)


def cli_path():
    """engine-cli.mjs of a release archive, or of a built checkout."""
    base = directory()
    for path in (base / "engine-cli.mjs", base / "packages/engine/dist/engine-cli.mjs"):
        if path.is_file():
            return path
    return None


def available():
    return cli_path() is not None and (directory() / "content").is_dir()


@lru_cache(maxsize=4)
def _journeys(base):
    folder = Path(base) / "content" / "journeys"
    if not folder.is_dir():
        return ()
    return tuple(json.loads(p.read_text(encoding="utf-8"))
                 for p in sorted(folder.glob("*.json")))


def builtin():
    """The built-in journeys in file-name order."""
    return list(_journeys(str(directory())))


_own = {"journeys": (), "texts": {}}


def set_own(found):
    """The user's own journeys (`journey:<id>` records, pensum.game.own),
    told on every evaluation: they are listed after the built-in ones,
    never in place of one, and their texts are read like QuestArc's:
    the user's language with English behind every missing key."""
    taken = {j.get("id") for j in builtin()}
    kept = tuple(j for j in found if isinstance(j, dict) and j.get("id") not in taken
                 and isinstance(j.get("stages"), list))
    if kept == _own["journeys"]:
        return
    texts = {}
    for item in kept:
        blocks = item.get("texts") if isinstance(item.get("texts"), dict) else {}
        for name in ("en", language()):
            if isinstance(blocks.get(name), dict):
                texts.update(blocks[name])
    _own["journeys"], _own["texts"] = kept, texts


def own():
    return list(_own["journeys"])


def journeys():
    """The built-in journeys, then the user's own."""
    return builtin() + own()


def journey(journey_id):
    return next((j for j in journeys() if j.get("id") == journey_id), None)


def locale():
    """The locale messages are shown in (LC_ALL, LC_MESSAGES, LANG)."""
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name)
        if value:
            return value
    return ""


def language():
    """The language QuestArc's texts are shown in: the locale's, if
    QuestArc has it, else English."""
    name = locale().split(".")[0].split("_")[0].split("@")[0].lower()
    return name if name and (directory() / "content" / "i18n" / f"{name}.json").is_file() \
        else "en"


def _english(base):
    table = {}
    app = Path(base) / "content" / "i18n" / "en.json"
    if app.is_file():
        table.update(json.loads(app.read_text(encoding="utf-8")))
    for item in _journeys(base):
        table.update(((item.get("texts") or {}).get("en")) or {})
    return table


@lru_cache(maxsize=4)
def _texts(base, wanted):
    """QuestArc's texts in the language of `wanted` (a locale): English
    from the files; any other language QuestArc has (German) through the
    engine's `texts` request, which picks the language and puts English
    behind every missing key (QuestArc texts.ts, #39)."""
    folder = Path(base) / "content" / "i18n"
    language = wanted.split(".")[0].split("_")[0].split("@")[0].lower()
    if not language or language == "en" or not (folder / f"{language}.json").is_file():
        return _english(base)
    from pensum.game import engine  # engine imports this module
    ui = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")}
    try:
        answer = engine.run({"texts": {"locale": wanted, "ui": ui,
                                       "journeys": list(_journeys(base))}})
    except (engine.EngineError, ValueError):
        return _english(base)
    texts = answer.get("texts") if isinstance(answer, dict) else None
    return texts if isinstance(texts, dict) else _english(base)


def has_text(key):
    return key in _own["texts"] or key in _texts(str(directory()), locale())


def ui_texts():
    """QuestArc's app and journey texts in the user's language, as the
    engine's quick journey needs them."""
    return _texts(str(directory()), locale())


def t(key, **params):
    """QuestArc's text for a key in the user's language (English behind a
    missing one), {name} filled in; the key itself if unknown."""
    text = _own["texts"].get(key)
    if text is None:
        text = _texts(str(directory()), locale()).get(key, key)
    return _PLACEHOLDER.sub(lambda m: str(params[m.group(1)])
                            if m.group(1) in params else m.group(0), text)


def art_path(name):
    """A picture of QuestArc's content/art/ by name (`tree` → tree.svg), or
    None. Journeys name pictures; there are no other pictures."""
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", name or ""):
        return None
    path = directory() / "content" / "art" / f"{name}.svg"
    return path if path.is_file() else None


def _art_json(name, suffix):
    path = directory() / "content" / "art" / f"{name}{suffix}"
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", name or "") or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ladder(name):
    """A ladder of content/art/ (`<name>.ladder.json`): the versions of one
    build, its default marker and the setting with its places; None if
    absent. The titles of the ladder and its versions are in the user's
    language where QuestArc has them (`ui.art.ladder.*`, as its art pack
    does); a title without a text stays as content/art has it."""
    found = _art_json(name, ".ladder.json")
    if found is None:
        return None
    found["title"] = _titled(f"ui.art.ladder.{name}", found.get("title"))
    for number, version in enumerate(found.get("versions") or (), start=1):
        version["title"] = _titled(f"ui.art.ladder.{name}.{number}", version.get("title"))
    return found


def _titled(key, fallback):
    text = t(key)
    return fallback if text == key else text


def palette():
    """The region hues of content/art/palette.json: name → {title, light,
    dark}; empty if absent. Titles in the user's language (`ui.art.hue.*`)."""
    found = _art_json("palette", ".json") or {}
    for name, entry in found.items():
        if isinstance(entry, dict):
            entry["title"] = _titled(f"ui.art.hue.{name}", entry.get("title"))
    return found


def ladders():
    """Every ladder of content/art/ by name, in file-name order."""
    folder = directory() / "content" / "art"
    names = sorted(p.name[:-len(".ladder.json")] for p in folder.glob("*.ladder.json"))
    return {name: found for name in names if (found := ladder(name)) is not None}
