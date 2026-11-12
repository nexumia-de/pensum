"""A sync folder on this device (Super Productivity's "Local File" sync,
or a folder another program keeps in sync), opened through the file
chooser portal. Read-only."""
from pathlib import Path

from pensum.sync import SyncError


class LocalFolder:
    def __init__(self, path):
        self.path = Path(path)

    def describe(self):
        return "local folder"

    def read(self, name):
        """The text of one file, or None when it does not exist."""
        if not self.path.is_dir():
            raise SyncError("The folder does not exist.")
        try:
            return (self.path / name).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            raise SyncError(f"A sync file can't be read: {error}") from error
