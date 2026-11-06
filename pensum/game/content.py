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
