"""Day Planner's own texts in the user's language (#79): gettext with the
domain `pensum`. QuestArc's texts come from QuestArc
(`pensum.game.content.t`); this is for the sentences Day Planner says
itself. The language follows LC_ALL, LC_MESSAGES and LANG like
QuestArc's texts do. Installed, the catalogues are compiled in
share/locale; from the source tree the `po/<language>.po` files are read
directly, so a development run and the tests need no build. No GTK."""
import ast
import gettext
import re
from functools import lru_cache
from pathlib import Path

from pensum.game.content import locale

DOMAIN = "pensum"
SOURCE_PO = Path(__file__).resolve().parent.parent / "po"
_ENTRY = re.compile(r'^(msgid|msgstr)\s+(".*")\s*$')


def locale_dir():
    try:
        from pensum.config import LOCALE_DIR
        return LOCALE_DIR
    except ImportError:  # run from the source tree
        return None


def languages(name):
    """"de_AT.UTF-8" → ["de_AT", "de"]; nothing for C and POSIX."""
    code = name.split(".")[0].split("@")[0]
    if not code or code in ("C", "POSIX"):
        return []
    return [code] + ([code.split("_")[0]] if "_" in code else [])


def read_po(path):
    """msgid → msgstr of a .po file (single-line and continued strings;
    no plurals or contexts, which Day Planner's catalogue does not use)."""
    found, key, value, field = {}, None, None, None
    for line in list(path.read_text(encoding="utf-8").splitlines()) + [""]:
        entry = _ENTRY.match(line)
        if entry:
            if entry.group(1) == "msgid":
                if key and value:
                    found[key] = value
                key, value, field = ast.literal_eval(entry.group(2)), "", "msgid"
            else:
                value, field = ast.literal_eval(entry.group(2)), "msgstr"
        elif line.startswith('"') and field:
            part = ast.literal_eval(line.strip())
            if field == "msgid":
                key += part
            else:
                value += part
        elif not line.strip():
            if key and value:
                found[key] = value
            key, value, field = None, None, None
    return found


@lru_cache(maxsize=4)
def _catalogue(name):
    wanted = languages(name)
    installed = locale_dir()
    if installed:
        return gettext.translation(DOMAIN, installed, languages=wanted, fallback=True).gettext
    for language in wanted:
        path = SOURCE_PO / f"{language}.po"
        if path.is_file():
            texts = read_po(path)
            return lambda text: texts.get(text, text)
    return lambda text: text


def _(text):
    """`text` in the user's language; the English text without one."""
    return _catalogue(locale())(text)


def N_(text):
    """Marks a text for translation where it is defined; `_()` translates
    it where it is shown (module constants are read before the language
    is known in the tests)."""
    return text
