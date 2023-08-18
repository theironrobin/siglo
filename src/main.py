import sys
import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gio, Gdk
from .window import SigloWindow
from .config import config


class Application(Gtk.Application):
    def __init__(self):
        self.manager = None
        self.conf = config()
        self.conf.load_defaults()
        super().__init__(
            application_id="com.github.theironrobin.siglo", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SigloWindow(application=self)
        win.present()
        win.do_scanning()

    def do_window_removed(self, window):
        win = self.props.active_window
        if win:
            win.destroy_manager()
        self.quit()


def main(version):
    app = Application()
    return app.run(sys.argv)
