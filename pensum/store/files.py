"""Where Pensum keeps its dataset, and loading, saving, importing and
exporting it with an automatic backup before every replacement. No GTK."""
import logging
from pathlib import Path

from phosh_toolkit.settings import app_dir

from pensum.store import autobackup, backup, dates, defaults, incoming, validate
from pensum.store.dataset import Dataset

log = logging.getLogger("pensum.store")


def data_dir():
    return app_dir("data", "pensum")


class Files:
    def __init__(self, directory=None):
        self.directory = Path(directory or data_dir())
        self.path = self.directory / "data.json"
        self.backups = self.directory / "backups"

    def load(self):
        """The saved dataset, or a fresh one on the first start. A broken
        file is kept as data.json.bad and the newest backup is used."""
        if not self.path.exists():
            return Dataset(defaults.fresh_dataset(dates.now_ms()))
        try:
            return Dataset(backup.read(self.path))
        except backup.BackupError as error:
            log.warning("data file unreadable: %s", error)
            self.path.replace(self.path.with_suffix(".json.bad"))
            for path in autobackup.listing(self.backups):
                try:
                    return Dataset(backup.read(path))
                except backup.BackupError:
                    continue
            return Dataset(defaults.fresh_dataset(dates.now_ms()))

    def save(self, ds):
        found = validate.problems(ds.data)
        if found:
            # Logged by kind only; titles and notes never reach the log.
            log.warning("dataset has %d consistency problems, first: %s",
                        len(found), found[0])
        backup.write(self.path, ds.data, dates.now_ms())
        if autobackup.due(self.backups):
            autobackup.write(self.backups, ds.data)

    def read_import(self, path):
        """The dataset of a backup file, before it replaces anything."""
        return Dataset(backup.read(path))

    def import_dataset(self, ds, current, keep_prefix=None):
        """Replace the dataset with an imported one; the current one is
        backed up first so the import can be undone from the backups
        folder. Records of `keep_prefix` that only the current dataset has
        are kept (pensum.store.incoming)."""
        kept = incoming.keep_records(current.data, ds.data, keep_prefix) if keep_prefix else []
        autobackup.write(self.backups, current.data)
        self.save(ds)
        log.info("imported %d tasks, kept %d local records", len(ds.data["task"]["ids"]),
                 len(kept))
        return ds

    def import_file(self, path, current, keep_prefix=None):
        return self.import_dataset(self.read_import(path), current, keep_prefix)

    def export_file(self, path, ds):
        backup.write(path, ds.data, dates.now_ms())
