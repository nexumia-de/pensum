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


def journeys():
    """The built-in journeys in file-name order."""
    return list(_journeys(str(directory())))


def journey(journey_id):
    return next((j for j in journeys() if j.get("id") == journey_id), None)


@lru_cache(maxsize=4)
def _texts(base):
    table = {}
    app = Path(base) / "content" / "i18n" / "en.json"
    if app.is_file():
        table.update(json.loads(app.read_text(encoding="utf-8")))
    for item in _journeys(base):
        table.update(((item.get("texts") or {}).get("en")) or {})
    return table


def t(key, **params):
    """The English text for a key with {name} filled in; the key itself if
    unknown (German follows with QuestArc's texts)."""
    text = _texts(str(directory())).get(key, key)
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


def scene(name):
    """A scene of content/art/ (`<name>.scene.json`): pictures at fixed
    places, with its title in words; None if absent."""
    return _art_json(name, ".scene.json")


def ladder(name):
    """A ladder of content/art/ (`<name>.ladder.json`): the versions of one
    build, its material and the setting with its places; None if absent."""
    return _art_json(name, ".ladder.json")


def palette():
    """The region hues of content/art/palette.json: name → {title, light,
    dark}; empty if absent."""
    return _art_json("palette", ".json") or {}
