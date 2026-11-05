"""Super Productivity's default values (sp-defaults.json, transcribed from
its source): a fresh dataset and new projects, tags and tasks. No GTK."""
import copy
import json
from functools import lru_cache
from pathlib import Path

# The data model version Pensum reads and writes (CROSS_MODEL_VERSION).
CROSS_MODEL_VERSION = 4.5
INBOX_ID = "INBOX_PROJECT"
TODAY_ID = "TODAY"


@lru_cache(maxsize=1)
def _defaults():
    path = Path(__file__).with_name("sp-defaults.json")
    return json.loads(path.read_text(encoding="utf-8"))


def get(name):
    """A fresh copy of one default ("project", "tag", "task", …)."""
    return copy.deepcopy(_defaults()[name])


def slices():
    """Every model slice of a complete dataset with its empty state."""
    return copy.deepcopy(_defaults()["slices"])


def fresh_dataset(now):
    """What Super Productivity holds after its first start: the Inbox
    project, the Today tag and the default settings."""
    data = slices()
    data["globalConfig"] = get("globalConfig")
    inbox = get("inboxProject")
    data["project"] = {"ids": [INBOX_ID], "entities": {INBOX_ID: inbox}}
    today = get("todayTag")
    today["created"] = now
    data["tag"] = {"ids": [TODAY_ID], "entities": {TODAY_ID: today}}
    return data
