"""Shared fixtures: private XDG directories and Super Productivity's own
test backups (tests/fixtures, from its e2e and validation fixtures)."""
import json
import sys
from pathlib import Path

import pytest

# The shared package from the sibling checkout (CI checks it out at the
# commit the Flatpak manifest pins and sets PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "phosh-toolkit" / "lib"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def xdg(tmp_path, monkeypatch):
    for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        monkeypatch.setenv(name, str(tmp_path / name.lower()))
    monkeypatch.delenv("PENSUM_DEMO", raising=False)


@pytest.fixture
def sp_backup():
    return FIXTURES / "test-backup-with-archives.json"


@pytest.fixture
def frozen_state(tmp_path):
    """Super Productivity 18.15's frozen state as a bare dataset file, the
    shape of its automatic desktop backups."""
    state = json.loads((FIXTURES / "frozen-state-v18.15.json").read_text())["state"]
    path = tmp_path / "2026-07-18_120000.json"
    path.write_text(json.dumps(state))
    return path


@pytest.fixture(scope="session")
def app():
    """One application for all UI tests, in every test module: a second
    one with the same id can't register on the session bus."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    from pensum.main import Application
    application = Application()
    application.register(None)
    Adw.init()
    yield application
