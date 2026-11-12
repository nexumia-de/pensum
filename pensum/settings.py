"""Pensum's own preferences on disk: the style, the list shown on the
last start and the journey banners already seen. The tasks themselves are in the dataset (pensum.store). No
GTK."""
from dataclasses import dataclass, field

from phosh_toolkit.settings import JsonStore, app_dir

VERSION = 1


@dataclass
class Settings:
    style: str = "system"
    last_list: str = "today:TODAY"
    # Journey banners the user closed ("Got it"), e.g. "nugget:<run>:<stage>".
    seen: list = field(default_factory=list)
    # The Super Productivity sync folder last read (pensum.sync): "webdav"
    # or "local", the server, user and folder (the password is in the
    # keyring), and the syncVersion read last from which source.
    sync_kind: str = "webdav"
    sync_url: str = ""
    sync_user: str = ""
    sync_folder: str = "super-productivity"
    sync_local_path: str = ""
    sync_seen_source: str = ""
    sync_seen_version: int = 0


def config_dir():
    return app_dir("config", "pensum")


class Store(JsonStore):
    def __init__(self, path=None):
        super().__init__(path or config_dir() / "settings.json", Settings, VERSION)
