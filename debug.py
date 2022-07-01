#!@PYTHON@


import os
import sys
import signal
import gettext
import argparse

VERSION = '@VERSION@'
pkgdatadir = '@pkgdatadir@'
localedir = '@localedir@'

sys.path.insert(1, pkgdatadir)
signal.signal(signal.SIGINT, signal.SIG_DFL)
gettext.install('siglo', localedir)

def main():
    p = argparse.ArgumentParser(description="app to sync InfiniTime watch")
    p.add_argument('--start', '-d', required=False, action='store_true', help="start daemon")
    p.add_argument('--stop', '-x', required=False, action='store_true', help="stop daemon")
    args = p.parse_args()

    from siglo import config
    config = config.config()
    config.load_defaults()

    from siglo import daemon
    d = daemon.daemon()

    if args.start:
        d.start()
    elif args.stop:
        d.stop()
    else:
        import gi

        from gi.repository import Gio
        resource = Gio.Resource.load(os.path.join(pkgdatadir, 'siglo.gresource'))
        resource._register()

        from siglo import main
        sys.exit(main.main(VERSION))

if __name__ == '__main__':
    main()

