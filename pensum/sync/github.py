"""A sync folder kept in a GitHub repository by Git Sync, the Super
Productivity plugin in nexumia-de/tabularium (docs/git-sync.md). Only
the plugin writes the branch `main`; Day Planner reads from it and hands
its changes over on the branch `day-planner`, one commit per send on top
of what it read. The plugin fast-forwards `main` to that branch before
Super Productivity syncs.

The state of both branches is read once per object and pinned, so all
files come from one commit:

- `day-planner` ahead of `main`: Day Planner's last send is still
  waiting for the desktop; reads and the next send build on it.
- missing, equal or behind: delivered; reads and sends start from main.
- diverged: the desktop synced on top of an older main before it took
  the send, so the send did not arrive. Reads use main; `stale_base()`
  gives the data the send was built on, so that the next send carries
  those edits again (pensum.ui.sync_send).

Uses the REST API (git data endpoints) with a fine-grained token for the
one repository (contents: read and write), sent only to the API host."""
import base64
import json
import os
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

from pensum.i18n import _
from pensum.sync import SyncError
from pensum.sync.webdav import Changed

API = os.environ.get("PENSUM_GITHUB_API") or "https://api.github.com"
MAIN = "main"
HANDOFF = "day-planner"
TIMEOUT = 30
AUTHOR = {"name": "Day Planner", "email": "day-planner@localhost"}


def parse_repository(text):
    """'owner/name' from what the user typed (also a github.com URL)."""
    value = text.strip().removesuffix(".git").rstrip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
    parts = value.split("/")
    if len(parts) != 2 or not all(parts) or any(c in value for c in " ?#"):
        raise SyncError(_("Enter the repository as owner/name."))
    return value


class GitHub:
    def __init__(self, repository, token, folder="", api=None, at=None):
        self.repository = parse_repository(repository)
        self.folder = "/".join(p for p in folder.strip().split("/") if p)
        self.api = (api or API).rstrip("/")
        self._token = token
        self._at = at  # a fixed commit, read-only (stale_base)
        self._state = None
        self._trees = {}

    def describe(self):
        return self.repository

    # --- REST ------------------------------------------------------------

    def _call(self, method, path, body=None, missing=(404,)):
        url = f"{self.api}/repos/{self.repository}/{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/vnd.github+json")
        request.add_header("X-GitHub-Api-Version", "2022-11-28")
        request.add_header("User-Agent", "DayPlanner")
        request.add_header("Cache-Control", "no-cache")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as error:
            if error.code in missing:
                return None
            if error.code == 401:
                raise SyncError(_("GitHub refused the token.")) from error
            if error.code == 403:
                raise SyncError(_("The token may not do this in the repository "
                                  "(contents: read and write needed).")) from error
            if error.code == 422:
                raise Changed(_("The sync folder changed while sending. "
                                "Try again.")) from error
            raise SyncError(_("GitHub answered {code}.").format(code=error.code)) from error
        except ssl.SSLError as error:
            raise SyncError(_("The server's certificate is not trusted.")) from error
        except (urllib.error.URLError, socket.timeout, OSError) as error:
            raise SyncError(_("Can't reach GitHub.")) from error
        except (UnicodeDecodeError, ValueError) as error:
            raise SyncError(_("GitHub sent an answer Day Planner can't read.")) from error

    def _ref(self, branch):
        # An empty repository answers 409 ("Git Repository is empty").
        found = self._call("GET", f"git/ref/heads/{branch}", missing=(404, 409))
        return found["object"]["sha"] if found else None

    def state(self):
        """{'view': commit to read, 'handoff': day-planner's commit or None,
        'pending': bool, 'stale': merge base or None}."""
        if self._state is not None:
            return self._state
        if self._at:
            self._state = {"view": self._at, "handoff": None, "pending": False, "stale": None}
            return self._state
        main = self._ref(MAIN)
        handoff = self._ref(HANDOFF)
        state = {"view": main, "handoff": handoff, "pending": False, "stale": None}
        if main is None:
            if handoff is not None:  # only Day Planner wrote so far
                state.update(view=handoff, pending=True)
        elif handoff is not None and handoff != main:
            compare = self._call("GET", f"compare/{main}...{handoff}")
            status = compare.get("status") if compare else None
            if status == "ahead":
                state.update(view=handoff, pending=True)
            elif status == "diverged":
                state["stale"] = compare["merge_base_commit"]["sha"]
        self._state = state
        return state

    def _path(self, name):
        return f"{self.folder}/{name}" if self.folder else name

    def _tree(self, commit):
        if commit not in self._trees:
            tree = self._call("GET", f"git/commits/{commit}")["tree"]["sha"]
            listing = self._call("GET", f"git/trees/{tree}?recursive=1")
            if listing.get("truncated"):
                raise SyncError(_("The repository holds too many files; keep only "
                                  "the sync folder in it."))
            self._trees[commit] = {e["path"]: e["sha"] for e in listing["tree"]
                                   if e.get("type") == "blob"}
        return self._trees[commit]

    # --- the source interface (pensum.sync.reader, pensum.sync.writer) ----

    def read(self, name):
        return self.read_versioned(name)[0]

    def read_versioned(self, name):
        """(text or None, the version to write against: the commit read)."""
        commit = self.state()["view"]
        if commit is None:
            return None, ("commit", None)
        blob = self._tree(commit).get(self._path(name))
        if blob is None:
            return None, ("commit", commit)
        found = self._call("GET", f"git/blobs/{blob}")
        try:
            text = base64.b64decode(found["content"]).decode("utf-8")
        except (KeyError, ValueError, UnicodeDecodeError) as error:
            raise SyncError(_("A sync file is damaged (not text).")) from error
        return text, ("commit", commit)

    def write(self, name, text, version):
        """One commit on top of the commit read, handed over on
        `day-planner`; raises Changed when a branch moved meanwhile."""
        if self._at:
            raise SyncError("read-only")
        state = self.state()
        parent = version[1]
        if parent is None or parent != state["view"]:
            raise Changed(_("The sync folder changed while sending. Try again."))
        blob = self._call("POST", "git/blobs", {"content": text, "encoding": "utf-8"})
        tree = self._call("POST", "git/trees", {
            "base_tree": self._call("GET", f"git/commits/{parent}")["tree"]["sha"],
            "tree": [{"path": self._path(name), "mode": "100644", "type": "blob",
                      "sha": blob["sha"]}]})
        commit = self._call("POST", "git/commits", {
            "message": "Day Planner: send changes", "tree": tree["sha"],
            "parents": [parent], "author": AUTHOR})["sha"]
        handoff = state["handoff"]
        if handoff is None:
            self._call("POST", "git/refs", {"ref": f"refs/heads/{HANDOFF}", "sha": commit})
        else:
            # After a stale send the branch starts again from main; only
            # then it is moved back (one Day Planner per repository).
            force = state["stale"] is not None
            if force and self._ref(HANDOFF) != handoff:
                raise Changed(_("The sync folder changed while sending. Try again."))
            self._call("PATCH", f"git/refs/heads/{HANDOFF}", {"sha": commit, "force": force})
        self._state = {"view": commit, "handoff": commit, "pending": True, "stale": None}

    def is_stale(self):
        return self.state()["stale"] is not None

    def stale_base(self):
        """A read-only source at the commit Day Planner's undelivered send
        was built on, or None when nothing is stale."""
        merge_base = self.state()["stale"]
        if merge_base is None:
            return None
        return GitHub(self.repository, self._token, self.folder, self.api, at=merge_base)
