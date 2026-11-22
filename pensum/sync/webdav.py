"""A sync folder on a WebDAV server (also Nextcloud): files are read with
GET and, when Day Planner sends changes (#30), one file is replaced with
PUT on the condition that it is still the version read (If-Match with
its ETag). Nothing is moved or deleted."""
import base64
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

from pensum.i18n import _
from pensum.sync import SyncError

TIMEOUT = 30


def file_url(base_url, folder, name):
    """Super Productivity's path: the base URL, the sync folder, the file."""
    base = base_url.strip()
    if not base.lower().startswith(("https://", "http://")):
        raise SyncError(_("The server address must start with https://."))
    parts = [p for p in folder.strip().split("/") if p] + [name]
    path = "/".join(urllib.parse.quote(p) for p in parts)
    return base.rstrip("/") + "/" + path


class WebDav:
    def __init__(self, base_url, user, password, folder="super-productivity"):
        self.base_url = base_url
        self.folder = folder
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._auth = f"Basic {token}"

    def describe(self):
        return urllib.parse.urlsplit(self.base_url.strip()).hostname or "server"

    def read(self, name):
        """The text of one file, or None when the server has no such file."""
        return self.read_versioned(name)[0]

    def read_versioned(self, name):
        """(text or None, the version to write against: the ETag or, without
        one, the text itself)."""
        request = urllib.request.Request(file_url(self.base_url, self.folder, name),
                                         method="GET")
        request.add_header("Authorization", self._auth)
        request.add_header("Cache-Control", "no-cache")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                text = response.read().decode("utf-8")
                return text, ("etag", response.headers.get("ETag")) \
                    if response.headers.get("ETag") else ("text", text)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None, ("text", None)
            if error.code in (401, 403):
                raise SyncError(_("The server refused the user name or "
                                  "password.")) from error
            raise SyncError(_("The server answered {code}.").format(
                code=error.code)) from error
        except ssl.SSLError as error:
            raise SyncError(_("The server's certificate is not trusted.")) from error
        except (urllib.error.URLError, socket.timeout, OSError) as error:
            raise SyncError(_("Can't reach the server.")) from error
        except UnicodeDecodeError as error:
            raise SyncError(_("A sync file is damaged (not text).")) from error

    def write(self, name, text, version):
        """Replace a file read with `read_versioned`, only if it is still
        that version; raises Changed otherwise."""
        kind, value = version
        if kind == "text" and self.read(name) != value:
            raise Changed(_("The sync folder changed while sending. Try again."))
        request = urllib.request.Request(file_url(self.base_url, self.folder, name),
                                         data=text.encode("utf-8"), method="PUT")
        request.add_header("Authorization", self._auth)
        request.add_header("Content-Type", "application/octet-stream")
        if kind == "etag":
            request.add_header("If-Match", value)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT):
                return
        except urllib.error.HTTPError as error:
            if error.code == 412:
                raise Changed(_("The sync folder changed while sending. "
                                "Try again.")) from error
            if error.code in (401, 403):
                raise SyncError(_("The server refused the user name or "
                                  "password.")) from error
            raise SyncError(_("The server answered {code}.").format(
                code=error.code)) from error
        except (urllib.error.URLError, socket.timeout, OSError) as error:
            raise SyncError(_("Can't reach the server.")) from error


class Changed(SyncError):
    """The file changed after it was read."""
