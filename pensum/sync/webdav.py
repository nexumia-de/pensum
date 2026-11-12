"""A sync folder on a WebDAV server (also Nextcloud), read with GET only:
this module has no way to write, move or delete a file."""
import base64
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request

from pensum.sync import SyncError

TIMEOUT = 30


def file_url(base_url, folder, name):
    """Super Productivity's path: the base URL, the sync folder, the file."""
    base = base_url.strip()
    if not base.lower().startswith(("https://", "http://")):
        raise SyncError("The server address must start with https://.")
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
        request = urllib.request.Request(file_url(self.base_url, self.folder, name),
                                         method="GET")
        request.add_header("Authorization", self._auth)
        request.add_header("Cache-Control", "no-cache")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code in (401, 403):
                raise SyncError("The server refused the user name or "
                                "password.") from error
            raise SyncError(f"The server answered {error.code}.") from error
        except ssl.SSLError as error:
            raise SyncError("The server's certificate is not trusted.") from error
        except (urllib.error.URLError, socket.timeout, OSError) as error:
            raise SyncError("Can't reach the server.") from error
        except UnicodeDecodeError as error:
            raise SyncError("A sync file is damaged (not text).") from error
