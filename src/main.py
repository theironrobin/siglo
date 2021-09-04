import sys
import gi
import dbus

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, Gio, Gdk
from .window import SigloWindow
from .config import config


class Application(Gtk.Application):
    def __init__(self):
        self.manager = None
        self.conf = config()
        self.conf.load_defaults()
        self.isHidden = False
        super().__init__(
            application_id="com.github.alexr4535.siglo", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SigloWindow(application=self)

        if not self.isHidden:
            win.present()
        win.do_scanning()

    def do_window_removed(self, window):
        win = self.props.active_window
        if win:
            win.destroy_manager()
        self.quit()


def portal_response_cb(response, results):
    if response != 0:
        print("Background request cancelled")
    else:
        if not results['background']:
            print("Background request denied")
        if not results['autostart']:
            print("Autostart request denied")

def main(version, isHidden):
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

    app.isHidden = isHidden

    bus = dbus.SessionBus()
    portal_obj = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
    background_iface = dbus.Interface(portal_obj, dbus_interface='org.freedesktop.portal.Background')
    obj_path = background_iface.RequestBackground("", dbus.Dictionary({
                                                      "reason":"Hide the Siglo window",
                                                      "autostart":True,
                                                      "commandline":["siglo", "--hidden"]
                                                        }, signature='sv', variant_level=1))
    request_iface = dbus.Interface(bus.get_object('org.freedesktop.portal.Desktop', obj_path),
                                    dbus_interface='org.freedesktop.portal.Request')
    request_iface.connect_to_signal("Response", portal_response_cb)

    return app.run()
