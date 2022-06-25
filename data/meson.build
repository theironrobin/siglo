desktop_file = i18n.merge_file(
  input: 'com.github.theironrobin.siglo.desktop.in',
  output: 'com.github.theironrobin.siglo.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

install_data(join_paths('icons', 'com.github.theironrobin.siglo.svg'),
  install_dir: join_paths(get_option('datadir'), 'icons/hicolor/scalable/apps')
)

install_data('siglo.service', install_dir: '/etc/systemd/user/')

appstream_file = i18n.merge_file(
  input: 'com.github.theironrobin.siglo.appdata.xml.in',
  output: 'com.github.theironrobin.siglo.appdata.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'metainfo')
)

appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appstream file', appstream_util,
    args: ['validate', appstream_file]
  )
endif

install_data('com.github.theironrobin.siglo.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', '--dry-run', meson.current_source_dir()]
  )
endif

