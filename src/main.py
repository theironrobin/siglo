import sys
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gio
from .window import SigloWindow
from .bluetooth import InfiniTimeManager


class Application(Gtk.Application):
    def __init__(self):
        self.manager = None
        super().__init__(
            application_id="org.gnome.siglo", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SigloWindow(application=self)
        win.present()
        self.manager = InfiniTimeManager()
        self.manager.scan_for_infinitime()
        win.done_scanning(self.manager)

    def do_window_removed(self, window):
        self.manager.stop()
        self.quit()


def main(version):
    app = Application()
    return app.run(sys.argv)
