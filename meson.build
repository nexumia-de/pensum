project('pensum',
  version: '0.2.0',
  meson_version: '>= 1.0',
  license: 'AGPL-3.0-or-later',
)

base_id = 'de.nexumia.Pensum'
# Nightly app next to the stable one (docs/release-channels.md).
nightly = get_option('profile') == 'development'
app_id = nightly ? base_id + '.Devel' : base_id

python = import('python').find_installation('python3')
pythondir = python.get_install_dir()

python.install_sources(
  'pensum/__init__.py',
  'pensum/__main__.py',
  'pensum/day_watch.py',
  'pensum/demo.py',
  'pensum/duration.py',
  'pensum/main.py',
  'pensum/preferences.py',
  'pensum/settings.py',
  'pensum/timer.py',
  'pensum/window.py',
  subdir: 'pensum',
)
# Folder modules, one file per job.
python.install_sources(
  'pensum/store/__init__.py',
  'pensum/store/archive.py',
  'pensum/store/autobackup.py',
  'pensum/store/backup.py',
  'pensum/store/contexts.py',
  'pensum/store/dataset.py',
  'pensum/store/dates.py',
  'pensum/store/defaults.py',
  'pensum/store/files.py',
  'pensum/store/ids.py',
  'pensum/store/search.py',
  'pensum/store/short_syntax.py',
  'pensum/store/tasks.py',
  'pensum/store/tracking.py',
  'pensum/store/validate.py',
  subdir: 'pensum' / 'store',
)
python.install_sources(
  'pensum/sync/__init__.py',
  'pensum/sync/changes.py',
  'pensum/sync/crypto.py',
  'pensum/sync/envelope.py',
  'pensum/sync/keyring.py',
  'pensum/sync/local.py',
  'pensum/sync/reader.py',
  'pensum/sync/summary.py',
  'pensum/sync/webdav.py',
  subdir: 'pensum' / 'sync',
)

python.install_sources(
  'pensum/sync/replay/__init__.py',
  'pensum/sync/replay/config.py',
  'pensum/sync/replay/ops.py',
  'pensum/sync/replay/tasks.py',
  subdir: 'pensum' / 'sync' / 'replay',
)

python.install_sources(
  'pensum/store/repeat/__init__.py',
  'pensum/store/repeat/instances.py',
  'pensum/store/repeat/rules.py',
  'pensum/store/repeat/schedule.py',
  subdir: 'pensum' / 'store' / 'repeat',
)
python.install_sources(
  'pensum/game/__init__.py',
  'pensum/game/content.py',
  'pensum/game/engine.py',
  'pensum/game/records.py',
  'pensum/game/sentences.py',
  'pensum/game/stages.py',
  subdir: 'pensum' / 'game',
)
python.install_sources(
  'pensum/ui/journey/__init__.py',
  'pensum/ui/journey/banners.py',
  'pensum/ui/journey/base.py',
  'pensum/ui/journey/card.py',
  'pensum/ui/journey/checkin_page.py',
  'pensum/ui/journey/choose_page.py',
  'pensum/ui/journey/continue_page.py',
  'pensum/ui/journey/drawing.py',
  'pensum/ui/journey/model.py',
  'pensum/ui/journey/motivates_page.py',
  'pensum/ui/journey/page.py',
  'pensum/ui/journey/path.py',
  'pensum/ui/journey/setup_page.py',
  'pensum/ui/journey/shelf_page.py',
  'pensum/ui/journey/start_page.py',
  'pensum/ui/journey/station_page.py',
  subdir: 'pensum' / 'ui' / 'journey',
)
python.install_sources(
  'pensum/ui/__init__.py',
  'pensum/ui/archived_page.py',
  'pensum/ui/backup_actions.py',
  'pensum/ui/dialogs.py',
  'pensum/ui/repeat_page.py',
  'pensum/ui/search_page.py',
  'pensum/ui/sync_page.py',
  'pensum/ui/sidebar.py',
  'pensum/ui/tags_dialog.py',
  'pensum/ui/time_dialog.py',
  'pensum/ui/task_list.py',
  'pensum/ui/task_page.py',
  'pensum/ui/task_row.py',
  'pensum/ui/tracker_bar.py',
  subdir: 'pensum' / 'ui',
)
# Loaded next to the Python files, also from the source tree.
install_data('pensum/style.css', install_dir: pythondir / 'pensum')
install_data('pensum/store/sp-defaults.json', install_dir: pythondir / 'pensum' / 'store')
# Their licence: Super Productivity's default values are MIT (docs/dependencies.md).
install_data('LICENSES/MIT.txt', rename: 'LICENSE',
  install_dir: get_option('datadir') / 'licenses' / app_id / 'super-productivity-defaults')

conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('PYTHONDIR', get_option('prefix') / pythondir)
configure_file(
  input: 'data/pensum.in',
  output: 'pensum',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

config = configuration_data()
config.set('APP_ID', app_id)
config.set('BUILD_LABEL', get_option('build_label'))
configure_file(
  input: 'pensum/config.py.in',
  output: 'config.py',
  configuration: config,
  install: true,
  install_dir: pythondir / 'pensum',
)

if nightly
  # The stable files in data/ stay the only source; the nightly app gets
  # its own id and the name "Day Planner (Nightly)".
  sed = find_program('sed')
  variant = [sed, '-e', 's/' + base_id + '/' + app_id + '/g',
             '-e', 's/^Name=Day Planner$/Name=Day Planner (Nightly)/',
             '-e', 's|<name>Day Planner</name>|<name>Day Planner (Nightly)</name>|',
             '@INPUT@']
  desktop = configure_file(input: 'data' / base_id + '.desktop',
    output: app_id + '.desktop', command: variant, capture: true)
  metainfo = configure_file(input: 'data' / base_id + '.metainfo.xml',
    output: app_id + '.metainfo.xml', command: variant, capture: true)
else
  desktop = files('data' / base_id + '.desktop')
  metainfo = files('data' / base_id + '.metainfo.xml')
endif
install_data(desktop, install_dir: get_option('datadir') / 'applications')
install_data(metainfo, install_dir: get_option('datadir') / 'metainfo')
install_data('data/icons/hicolor/scalable/apps' / base_id + '.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps',
  rename: app_id + '.svg')
# Pensum's own symbolic icons.
install_subdir('data/icons/hicolor/symbolic/apps',
  install_dir: get_option('datadir') / 'icons/hicolor/symbolic',
  strip_directory: false)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('validate-desktop', desktop_file_validate, args: [desktop])
endif
appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-metainfo', appstreamcli,
    args: ['validate', '--no-net', metainfo])
endif
