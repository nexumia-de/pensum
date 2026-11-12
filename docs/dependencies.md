---
type: Reference
title: Bundled dependencies
description: Pensum bundles phosh-toolkit's shared package and QuestArc's engine archive; everything else comes from the GNOME runtime. Super Productivity's default values ship as MIT data.
tags: [dependencies, licensing, flatpak]
generated: { by: claude-code/2.1.318, at: 2026-11-05T00:30:00Z }
---

# Rules

The shared rules are in
[../../phosh-toolkit/docs/licensing.md](../../phosh-toolkit/docs/licensing.md).
CI fails if a module of `de.nexumia.Pensum.yml` is missing here or
installs no licence files.

# Modules

| Module | Version | Licence | Licence files |
|---|---|---|---|
| `phosh-toolkit` | tag `v0.3.0` (commit `c29a2a1`) | GPL-3.0-or-later (own code, same author) | `LICENSE` → `/app/share/licenses/<app id>/phosh-toolkit/` |
| `questarc-engine` | release archive `v3.1.0` (sha256 `acb5a47f…`) | engine AGPL-3.0-or-later (same author); journeys in `content/journeys/` CC BY-SA 4.0 | `LICENSE` → `…/questarc-engine/`, `content/LICENSE` → `…/questarc-journeys/` |

| `python3-build-tools` | wheels: setuptools 84.2.1, setuptools-scm 10.3.4, vcs-versioning 2.6.0, packaging 26.3, scikit-build-core 1.1.2, pathspec 1.1.1 | MIT; packaging Apache-2.0 OR BSD-2-Clause; scikit-build-core Apache-2.0; pathspec MPL-2.0 | each wheel's `dist-info/licenses/` → `…/python3-build-tools/<wheel>/`; the modules themselves are removed after the build (pure-Python build tools, not shipped) |
| `python3-pycparser` | sdist 3.12 | BSD-3-Clause | `LICENSE` → `…/python3-pycparser/` |
| `python3-cffi` | sdist 2.1.1 (uses the runtime's libffi) | MIT-0 | `LICENSE` → `…/python3-cffi/` |
| `python3-argon2-cffi-bindings` | sdist 26.1.0, bundles the Argon2 reference C code (`extras/libargon2`) | MIT; libargon2 CC0-1.0 OR Apache-2.0 | `LICENSE` → `…/python3-argon2-cffi-bindings/`, `extras/libargon2/LICENSE` → `…/libargon2/` |

The four Python modules (#29, Argon2id for encrypted sync files) are
built from their sdists with the pure-Python build tools, as Flathub
requires; Pensum calls `argon2_hash` of the bindings directly, so
`argon2-cffi` itself is not needed. Licences read from the sdists' and
wheels' files on 2026-11-12. `x-checker-data` asks PyPI's JSON API.

Only `lib/phosh_toolkit/` is installed; Pensum uses `settings`
(`JsonStore`, `app_dir`) and `style` (light/dark)
([shared code](../../phosh-toolkit/docs/shared-connection.md#used-by)).

QuestArc's engine ([journeys](journeys.md)): Only `engine.mjs`, `engine-cli.mjs` and `content/` are installed, to
`/app/share/questarc/`; the runtime's `gjs` runs the engine. The
journeys' authors are named in the app ("Written by …").

# Data from Super Productivity

`pensum/store/sp-defaults.json`: default values transcribed from Super
Productivity 19.3.1 (MIT, © 2018 Johannes Millan), installed with
Pensum's package; its licence text goes to
`/app/share/licenses/<app id>/super-productivity-defaults/`.

# Tests only (not bundled)

| What | Version | Licence | Used by |
|---|---|---|---|
| `playwright` (npm, `tests/real_app/package.json`) | 1.64.1 | Apache-2.0 | real-app test |
| Super Productivity Docker image `johannesjo/super-productivity` | `v20.0.0` (digest in `tests/real_app/Dockerfile`) | MIT (© 2018 Johannes Millan) | real-app test, CI only |
| `wsgidav` (PyPI, `tests/real_app/requirements-webdav.txt`) | 4.4.0 | MIT | sync test's WebDAV server |
| its dependencies: `cheroot` 11.1.2, `jaraco.functools` 4.6.0, `more-itertools` 11.2.1, `defusedxml` 0.7.1, `Jinja2` 3.1.6, `MarkupSafe` 3.0.4, `json5` 0.17.3, `PyYAML` 6.0.3 | as listed | BSD-3-Clause (cheroot), MIT (jaraco.functools, more-itertools, PyYAML), PSF-2.0 (defusedxml), BSD-3-Clause (Jinja2, MarkupSafe), Apache-2.0 (json5) | the same |

Licences read from each package's `LICENSE` file or licence metadata on
2026-11-12. None of these is bundled. Dependabot updates them.

# From the runtime (not bundled)

`org.gnome.Platform//51` provides Python 3, PyGObject, GTK 4,
libadwaita and libsecret (the WebDAV password in the keyring; without
it the password is not remembered) and OpenSSL's libcrypto (AES-GCM for
encrypted sync files, through ctypes). Reading WebDAV uses Python's
`urllib` ([sync files](super-productivity-sync.md#file-envelope)).

The tests need `argon2-cffi-bindings` too: CI installs the version
pinned in `tests/requirements.txt` from PyPI (Ubuntu 24.04 has no
package), with `python3-cffi` from Ubuntu.
