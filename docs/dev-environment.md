---
type: Playbook
title: Development environment
description: Hosts, host packages, and how to run, test, screenshot and build Pensum.
tags: [development, environment, testing, flatpak]
generated: { by: claude-code/2.1.318, at: 2026-11-12T17:00:00Z }
---

# Hosts

Reached from the cloud environment on 2026-11-05: `github.com`
(Super Productivity's source), `flathub.org` (app search),
`registry.npmjs.org`. Pensum itself uses no network.

# Host packages (Ubuntu 24.04)

After `bash ../phosh-toolkit/setup.sh`: `python3-pytest xvfb
python3-gi-cairo` (the journey path draws with Cairo) and
`gir1.2-rsvg-2.0` (QuestArc's pictures, [journeys](journeys.md#pictures)). The cloud image's
default `python3` has no `gi`; use `/usr/bin/python3.12`.

# QuestArc's engine (journeys)

The journey pages need QuestArc's engine and gjs ([journeys](journeys.md)).
With a QuestArc checkout next to this one, built with `npm ci && npm run
build`, and gjs. Where apt works (it did on the cloud image on
2026-11-13), the packages of the CI job are enough: `python3-pytest
python3-gi python3-gi-cairo python3-cffi gir1.2-gtk-4.0 gir1.2-adw-1
gir1.2-rsvg-2.0 gjs`, and `libgtk-4-bin` for the screenshot script; then
only `PENSUM_QUESTARC_DIR` is needed. Ubuntu 24.04 has libadwaita 1.5,
older than the runtime's, so check the look in the Flatpak. Otherwise
gjs comes from the GNOME runtime (`flatpak run` does not work on the
cloud host, so a small wrapper runs it through bwrap):

```sh
flatpak --user install -y flathub org.gnome.Platform//51
```

```sh
printf '#!/bin/sh\nR=%s\nexec bwrap --ro-bind "$R" /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 --symlink usr/bin /bin --ro-bind "$R/etc" /etc --proc /proc --dev /dev --bind /home /home --bind /tmp /tmp --chdir "$PWD" gjs "$@"\n' "$(flatpak --user info --show-location org.gnome.Platform//51)/files" > ~/bin/gjs
```

```sh
chmod +x ~/bin/gjs
```

```sh
export PENSUM_QUESTARC_DIR=$PWD/../QuestArc PENSUM_GJS=$HOME/bin/gjs
```

The wrapper names the runtime's path directly, because the tests point
`XDG_DATA_HOME` elsewhere. `-a app.show-journey` opens the journey page
in screenshots (pass both variables with `-e`). Hosts: `dl.flathub.org`
for the runtime.

# Super Productivity's source

For the analysis in [data model](super-productivity-data.md):

```sh
git clone --depth 1 https://github.com/johannesjo/super-productivity ../super-productivity
```

Read it, never copy code from it; values are transcribed as data
(`pensum/store/sp-defaults.json`), fixtures copied with their licence.

# Run, test, screenshot

```sh
export PYTHONPATH=$PWD/../phosh-toolkit/lib
PENSUM_DEMO=1 /usr/bin/python3.12 -m pensum
dbus-run-session -- xvfb-run -a /usr/bin/python3.12 -m pytest
../phosh-toolkit/scripts/screenshot.sh -i de.nexumia.Pensum -d 4 -e PENSUM_DEMO=1 -e PYTHONPATH=$PWD:$PYTHONPATH -o shot.png -- /usr/bin/python3.12 -m pensum
```

Other states: `-a app.show-lists`, `-a app.show-current-task`,
`-a "app.show-list('project:demo-garden')"`. `PENSUM_DEBUG=1` logs
saves and consistency problems (by kind, never titles).

# Real-app test

`tests/real_app/` imports Pensum's exports into a real Super
Productivity and reads its export back
([what it checks](super-productivity-data.md#checked-against-a-real-super-productivity)):
`make_exports.py` writes the files without a display, `sp_import.mjs`
drives Super Productivity with Playwright, `check_round_trip.py`
compares, `run.sh` runs all and checks that a broken file fails. By
default it uses the live web app (through `HTTPS_PROXY`); the cloud
image has Playwright with Chromium and no Docker daemon:

```sh
tests/real_app/run.sh
```

Files go to `tests/real_app/out/`. CI (job `real-app`) runs the Docker
image pinned in `tests/real_app/Dockerfile` and points the test at it
with `PENSUM_SP_URL`; the same locally where Docker runs:

```sh
docker build -t pensum-sp tests/real_app
```

```sh
docker run -d -p 8080:80 pensum-sp
```

```sh
PENSUM_SP_URL=http://localhost:8080/ tests/real_app/run.sh
```

Hosts: `app.super-productivity.com` (the live app; it sometimes answers
a script with 502, so the test loads the page up to three times),
`hub.docker.com` (image digests). `registry-1.docker.io` answered 429
without login on 2026-11-12.

# Sync test

`tests/real_app/run_sync.sh` checks reading a sync folder against a real
Super Productivity ([what it checks](super-productivity-sync.md#checked-against-a-real-super-productivity)):
it starts the WebDAV test server (`wsgidav.yaml`: `127.0.0.1:2345`, user
and password `test`, CORS for the web app), runs `sp_sync.mjs` (round 1:
sets up WebDAV sync in Super Productivity's sync dialog, adds and
changes tasks, syncs, exports) and `check_sync.py` (Pensum reads the
folder and compares), then round 2 on the same browser profile. The
server comes from PyPI, pinned in `requirements-webdav.txt`:

```sh
python3 -m venv ../webdav
```

```sh
../webdav/bin/pip install --no-deps -r tests/real_app/requirements-webdav.txt
```

```sh
WSGIDAV=../webdav/bin/wsgidav PYTHON=/usr/bin/python3.12 tests/real_app/run_sync.sh
```

It runs twice, `plain` and `encrypted` (compression and encryption on,
password "test password"); files go to `tests/real_app/out-sync/`
(the folders in `dav/plain` and `dav/encrypted`, each scenario's browser
profile in `<scenario>/profile/`). The tests need Argon2id:

```sh
/usr/bin/python3.12 -m pip install --user --break-system-packages --no-deps -r tests/requirements.txt
```
 Like the real-app test it uses the
live web app unless `PENSUM_SP_URL` names another; CI uses the pinned
image. The live app (HTTPS) reaches the server on `127.0.0.1` because
Chromium treats loopback as secure and the proxy is bypassed for it.
Hosts: `pypi.org` and `files.pythonhosted.org` (the server; reachable
by default as package registries).

# SuperSync probe

Manual, not in CI (#34, [findings](super-productivity-sync.md#supersync)).
Needs the SuperSync **test account's** access token as a network secret
of the environment for `sync.super-productivity.com` (Authorization:
Bearer); the proxy adds it to every request to that host, so scripts
and the app only see a placeholder. Never use a real account.

```sh
node tests/real_app/sp_supersync.mjs ../supersync-probe 1
```

```sh
python3 tests/real_app/read_supersync.py
```

`sp_supersync.mjs` round 1 (for an empty account) adds tasks and sets up
SuperSync with encryption password "test password"; round 2 adds and
completes tasks. `read_supersync.py` downloads the ops (GET only),
decrypts them and prints the newest full-state op's counts and the
later ops a reader would have to replay. Hosts:
`sync.super-productivity.com` (allowed by the saved network secret).

# Flatpak

```sh
flatpak-builder --user --install --force-clean --disable-rofiles-fuse build-dir de.nexumia.Pensum.yml
```

Not yet built in the cloud container; CI builds it for x86_64 and
aarch64.
