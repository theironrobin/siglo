import sys
import gi
import gatt

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gio, Gdk
from .window import SigloWindow
from .bluetooth import InfiniTimeManager
from .config import config


class Application(Gtk.Application):
    def __init__(self):
        self.manager = None
        self.conf = config()
        self.conf.load_defaults()
        super().__init__(
            application_id="org.gnome.siglo", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SigloWindow(
                application=self,
                mode=self.conf.get_property("mode"),
                deploy_type=self.conf.get_property("deploy_type"),
            )
        win.present()
        self.manager = InfiniTimeManager()
        info_prefix = "[INFO ] Done Scanning"
        try:
            self.manager.scan_for_infinitime()
        except gatt.errors.NotReady:
            info_prefix = "[WARN ] Bluetooth is disabled"
        if self.conf.get_property("mode") == "singleton":
            win.done_scanning_singleton(self.manager, info_prefix)
        if self.conf.get_property("mode") == "multi":
            win.done_scanning_multi(self.manager, info_prefix)

    def do_window_removed(self, window):
        self.manager.stop()
        self.quit()


def main(version):
    def gtk_style():
        css = b"""
#multi_mac_label { font-size: 33px; }
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
