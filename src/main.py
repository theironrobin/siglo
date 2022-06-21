import sys
import gi

gi.require_version("Gtk", "3.0")

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
    def gtk_style():
        css = b"""
#multi_mac_label { font-size: 33px; }
#bluetooth_button { background-color: blue;
                    background-image: none; }
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    gtk_style()
    app = Application()
    return app.run(sys.argv)
