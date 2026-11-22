"""A stand-in for the part of GitHub's REST API that pensum.sync.github
uses (refs, compare, commits, trees, blobs, and /user/repos for the
guided setup), and that Git Sync (nexumia-de/tabularium) uses besides
(the Contents API's first commit, removals in a tree), on a real bare repository
through git plumbing, so tests and the sync test (run_sync.sh, scenario
git) need no GitHub account. Answers like GitHub for the cases Day
Planner relies on: 404 for a missing ref, 409 for an empty repository,
422 for a ref update that is not a fast-forward or a ref that exists,
401 for a wrong token.

    python3 tests/github_fake.py REPO.git PORT TOKEN
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ZERO = "0" * 40


class Repo:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.Lock()

    def git(self, *args, data=None, env=None, check=True):
        result = subprocess.run(["git", "-C", self.path, *args], input=data,
                                capture_output=True, env={**os.environ, **(env or {})})
        if check and result.returncode:
            raise RuntimeError(result.stderr.decode())
        return result

    def out(self, *args, **kw):
        return self.git(*args, **kw).stdout.decode().strip()

    def ref(self, branch):
        r = self.git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        return r.stdout.decode().strip() if r.returncode == 0 else None

    def empty(self):
        return not self.out("for-each-ref", "refs/heads")

    def is_ancestor(self, older, newer):
        return self.git("merge-base", "--is-ancestor", older, newer, check=False).returncode == 0


def handler(repo, token, prefix):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, body=None):
            data = json.dumps(body if body is not None else {"message": str(code)}).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def route(self, method):
            if self.headers.get("Authorization") != f"Bearer {token}":
                return self.reply(401, {"message": "Bad credentials"})
            path = urlsplit(self.path).path
            if path == "/user/repos" and method == "GET":
                # The guided setup's list: the one repository, writable.
                return self.reply(200, [{"full_name": prefix.strip("/").split("/", 1)[1],
                                         "private": True, "permissions": {"push": True}}])
            if not path.startswith(prefix):
                return self.reply(404)
            parts = path[len(prefix):].strip("/").split("/")
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length)) if length else None
            with repo.lock:
                try:
                    return self.dispatch(method, parts, body)
                except RuntimeError:
                    return self.reply(422)

        def dispatch(self, method, parts, body):
            r = repo
            if parts[:3] == ["git", "ref", "heads"] and method == "GET":
                if r.empty():
                    return self.reply(409, {"message": "Git Repository is empty."})
                sha = r.ref("/".join(parts[3:]))
                return self.reply(200, {"object": {"sha": sha, "type": "commit"}}) if sha \
                    else self.reply(404)
            if parts[0] == "compare" and method == "GET":
                base, head = parts[1].split("...")
                merge = r.out("merge-base", base, head)
                if base == head:
                    status = "identical"
                elif merge == base:
                    status = "ahead"
                elif merge == head:
                    status = "behind"
                else:
                    status = "diverged"
                ahead = int(r.out("rev-list", "--count", f"{base}..{head}"))
                return self.reply(200, {"status": status, "ahead_by": ahead,
                                        "merge_base_commit": {"sha": merge}})
            if parts[:2] == ["git", "commits"] and method == "GET":
                return self.reply(200, {"sha": parts[2],
                                        "tree": {"sha": r.out("rev-parse", f"{parts[2]}^{{tree}}")}})
            if parts[:2] == ["git", "trees"] and method == "GET":
                entries = []
                for line in r.out("ls-tree", "-r", "-t", parts[2]).splitlines():
                    meta, path = line.split("\t", 1)
                    mode, kind, sha = meta.split()
                    entries.append({"path": path, "mode": mode, "type": kind, "sha": sha})
                return self.reply(200, {"sha": parts[2], "tree": entries, "truncated": False})
            if parts[:2] == ["git", "blobs"] and method == "GET":
                data = r.git("cat-file", "blob", parts[2]).stdout
                return self.reply(200, {"sha": parts[2], "encoding": "base64",
                                        "content": base64.encodebytes(data).decode()})
            if parts[0] == "git" and method == "POST" and r.empty():
                return self.reply(409, {"message": "Git Repository is empty."})
            if parts[0] == "contents" and method == "PUT":
                # The first commit of an empty repository (Git Sync's start).
                branch = body.get("branch") or "main"
                parent = r.ref(branch)
                with tempfile.TemporaryDirectory() as tmp:
                    env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
                    if parent:
                        r.git("read-tree", parent, env=env)
                    blob = r.out("hash-object", "-w", "--stdin",
                                 data=base64.b64decode(body["content"]))
                    r.git("update-index", "--add", "--cacheinfo",
                          f"100644,{blob},{'/'.join(parts[1:])}", env=env)
                    tree = r.out("write-tree", env=env)
                env = {"GIT_AUTHOR_NAME": "API", "GIT_AUTHOR_EMAIL": "api@localhost",
                       "GIT_COMMITTER_NAME": "GitHub", "GIT_COMMITTER_EMAIL": "noreply@github.com"}
                args = ["commit-tree", tree, "-m", body["message"]] + (["-p", parent] if parent else [])
                commit = r.out(*args, env=env)
                r.git("update-ref", f"refs/heads/{branch}", commit, parent or ZERO)
                return self.reply(201, {"commit": {"sha": commit}})
            if parts == ["git", "blobs"] and method == "POST":
                data = (body["content"].encode() if body.get("encoding") == "utf-8"
                        else base64.b64decode(body["content"]))
                return self.reply(201, {"sha": r.out("hash-object", "-w", "--stdin", data=data)})
            if parts == ["git", "trees"] and method == "POST":
                with tempfile.TemporaryDirectory() as tmp:
                    env = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
                    if body.get("base_tree"):
                        r.git("read-tree", body["base_tree"], env=env)
                    for e in body["tree"]:
                        if e["sha"] is None:  # GitHub removes the path
                            r.git("update-index", "--index-info", env=env,
                                  data=f"0 {ZERO}\t{e['path']}\n".encode())
                        else:
                            r.git("update-index", "--add", "--cacheinfo",
                                  f"{e['mode']},{e['sha']},{e['path']}", env=env)
                    return self.reply(201, {"sha": r.out("write-tree", env=env)})
            if parts == ["git", "commits"] and method == "POST":
                author = body.get("author") or {"name": "API", "email": "api@localhost"}
                env = {"GIT_AUTHOR_NAME": author["name"], "GIT_AUTHOR_EMAIL": author["email"],
                       "GIT_COMMITTER_NAME": "GitHub", "GIT_COMMITTER_EMAIL": "noreply@github.com"}
                args = ["commit-tree", body["tree"], "-m", body["message"]]
                for parent in body.get("parents") or []:
                    args += ["-p", parent]
                return self.reply(201, {"sha": r.out(*args, env=env)})
            if parts == ["git", "refs"] and method == "POST":
                name = body["ref"]
                if r.git("rev-parse", "--verify", "--quiet", name, check=False).returncode == 0:
                    return self.reply(422, {"message": "Reference already exists"})
                r.git("update-ref", name, body["sha"], ZERO)
                return self.reply(201, {"ref": name, "object": {"sha": body["sha"]}})
            if parts[:3] == ["git", "refs", "heads"] and method == "PATCH":
                branch = "/".join(parts[3:])
                old = r.ref(branch)
                if old is None:
                    return self.reply(422, {"message": "Reference does not exist"})
                if not body.get("force") and not r.is_ancestor(old, body["sha"]):
                    return self.reply(422, {"message": "Update is not a fast forward"})
                r.git("update-ref", f"refs/heads/{branch}", body["sha"], old)
                return self.reply(200, {"object": {"sha": body["sha"]}})
            return self.reply(404)

        def do_GET(self):
            self.route("GET")

        def do_POST(self):
            self.route("POST")

        def do_PATCH(self):
            self.route("PATCH")

        def do_PUT(self):
            self.route("PUT")

    return Handler


def serve(repo_path, port=0, token="test", repository="test/sync"):
    """Starts the server in a thread; returns (server, api base URL)."""
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 handler(Repo(repo_path), token, f"/repos/{repository}/"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    server = ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])),
                                 handler(Repo(sys.argv[1]), sys.argv[3], "/repos/test/sync/"))
    server.serve_forever()
