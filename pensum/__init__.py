"""Pensum: tasks and time tracking for Phosh phones, in Super
Productivity's data format."""

try:
    from pensum.config import APP_ID, BUILD_LABEL
except ImportError:  # run from the source tree, config.py is not built
    APP_ID = "de.nexumia.Pensum"
    BUILD_LABEL = ""
VERSION = "0.2.0"
# The nightly app is built from every push to main.
NIGHTLY = APP_ID.endswith(".Devel")
NAME = "Day Planner (Nightly)" if NIGHTLY else "Day Planner"
# About dialog, e.g. "0.1.0 (main · 8534d2c)" for a nightly build.
VERSION_LABEL = f"{VERSION} ({BUILD_LABEL})" if BUILD_LABEL else VERSION
REPO_URL = "https://github.com/nexumia-de/pensum"
# Voluntary support for development (phosh-toolkit docs/support.md).
SUPPORT_URL = "https://liberapay.com/suitably"
