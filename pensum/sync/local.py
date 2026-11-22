"""A sync folder on this device (Super Productivity's "Local File" sync,
or a folder another program keeps in sync), opened through the file
chooser portal. Read, and one file replaced when Day Planner sends
changes (#30), only if it is still the version read."""
import os
from pathlib import Path

from pensum.i18n import _
from pensum.sync import SyncError


class LocalFolder:
    def __init__(self, path):
        self.path = Path(path)

    def describe(self):
        return "local folder"

    def read_versioned(self, name):
        """(text or None, the version to write against: the text)."""
        text = self.read(name)
        return text, ("text", text)

    def write(self, name, text, version):
        from pensum.sync.webdav import Changed
        if self.read(name) != version[1]:
            raise Changed(_("The sync folder changed while sending. Try again."))
        target = self.path / name
        temporary = target.with_name(target.name + ".pensum-tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            os.replace(temporary, target)
        except OSError as error:
            raise SyncError(_("A sync file can't be written: {reason}").format(
                reason=error)) from error

    def read(self, name):
        """The text of one file, or None when it does not exist."""
        if not self.path.is_dir():
            raise SyncError(_("The folder does not exist."))
        try:
            return (self.path / name).read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as error:
            raise SyncError(_("A sync file can't be read: {reason}").format(
                reason=error)) from error
