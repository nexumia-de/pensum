# Pensum

Tasks and time tracking for Phosh phones and the desktop, in the data
format of [Super Productivity](https://github.com/johannesjo/super-productivity).

Pensum is a light GTK4/libadwaita app. It keeps your tasks as a Super
Productivity backup, so the same file moves between both apps: export
in Super Productivity, import in Pensum, and back.

- Today's list, projects and tags
- Tasks with subtasks, notes, estimates and a planned day
- A timer per task that books the time on the day you worked
- Import and export of Super Productivity backups, automatic backups
- Offline: no account, no network

Pensum is an independent project and not affiliated with the Super
Productivity project. What it rebuilds and what not:
[docs/features.md](docs/features.md).

## Install

Pensum ships as a Flatpak for x86_64 and aarch64 from the shared app
repository (see phosh-toolkit's `docs/app-repository.md`), once the
first release is tagged.

## Moving data from Super Productivity

1. In Super Productivity: Settings → Sync & Backup → Export data.
2. In Pensum: main menu → Import Backup…, choose the file.

The other way: Pensum's main menu → Export Backup…, then Import in
Super Productivity. Automatic desktop backups of Super Productivity
(`~/.config/superProductivity/backups/*.json`) can be imported as well.

## Development

```sh
export PYTHONPATH=$PWD/../phosh-toolkit/lib
PENSUM_DEMO=1 python3 -m pensum
dbus-run-session -- xvfb-run -a python3 -m pytest
```

Details: [docs/dev-environment.md](docs/dev-environment.md). Knowledge
bundle: [docs/index.md](docs/index.md).

## Support

Pensum is free software (AGPL-3.0-or-later). If it helps you, you can
support development at [liberapay.com/suitably](https://liberapay.com/suitably).
