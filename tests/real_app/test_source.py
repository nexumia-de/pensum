"""The sync test's source for Pensum (check_sync.py, pensum_send.py): the
WebDAV test server, or with PENSUM_SYNC_SOURCE=github the GitHub stand-in
(tests/github_fake.py at PENSUM_GITHUB_API) on the repository that Git
Sync's cycle keeps (run_sync.sh, scenario git)."""
import os

from pensum.sync.github import GitHub
from pensum.sync.webdav import WebDav

FOLDER = os.environ.get("PENSUM_DAV_FOLDER") or "super-productivity"


def sync_source():
    """(source, name for messages)."""
    if os.environ.get("PENSUM_SYNC_SOURCE") == "github":
        return GitHub("test/sync", "test", api=os.environ["PENSUM_GITHUB_API"]), "GitHub"
    url = os.environ.get("PENSUM_DAV_URL", "http://127.0.0.1:2345/")
    return WebDav(url, "test", "test", FOLDER), "WebDAV"
