prefix = get_option('prefix')
datadir = get_option('datadir')
libexecdir = join_paths(prefix, get_option('libexecdir'))

desktop_file = i18n.merge_file(
  input: 'com.github.alexr4535.siglo.desktop.in',
  output: 'com.github.alexr4535.siglo.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(datadir, 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

install_data(join_paths('icons', 'com.github.alexr4535.siglo.svg'),
  install_dir: join_paths(datadir, 'icons')
)

appstream_file = i18n.merge_file(
  input: 'com.github.alexr4535.siglo.appdata.xml.in',
  output: 'com.github.alexr4535.siglo.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(datadir, 'metainfo')
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', appstream_file]
  )
endif

install_data('com.github.alexr4535.siglo.gschema.xml',
  install_dir: join_paths(datadir, 'glib-2.0/schemas')
)

service_conf = configuration_data()
service_conf.set('appid', 'com.github.alexr4535.siglo.Daemon')
service_conf.set('bindir', join_paths(get_option('prefix'), get_option('bindir')))

configure_file(
	input: 'com.github.alexr4535.siglo.Daemon.service.in',
	output: 'com.github.alexr4535.siglo.Daemon.service',
	configuration: service_conf,
	install: true,
	install_dir: join_paths(datadir,'dbus-1', 'services')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

