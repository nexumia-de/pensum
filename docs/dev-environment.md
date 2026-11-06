---
type: Playbook
title: Development environment
description: Hosts, host packages, and how to run, test, screenshot and build Pensum.
tags: [development, environment, testing, flatpak]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Hosts

Reached from the cloud environment on 2026-11-05: `github.com`
(Super Productivity's source), `flathub.org` (app search),
`registry.npmjs.org`. Pensum itself uses no network.

# Host packages (Ubuntu 24.04)

After `bash ../phosh-toolkit/setup.sh`: `python3-pytest xvfb
python3-gi-cairo` (the journey path draws with Cairo). The cloud image's
default `python3` has no `gi`; use `/usr/bin/python3.12`.

# QuestArc's engine (journeys)

The journey pages need QuestArc's engine and gjs ([journeys](journeys.md)).
With a QuestArc checkout next to this one, built with `npm ci && npm run
build`, and gjs from the GNOME runtime (the cloud image has no `gjs`
package; `flatpak run` does not work there, so a small wrapper runs it
through bwrap):

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

# Flatpak

```sh
flatpak-builder --user --install --force-clean --disable-rofiles-fuse build-dir de.nexumia.Pensum.yml
```

Not yet built in the cloud container; CI builds it for x86_64 and
aarch64.
