
import sys
import gi
import gatt
import dbus

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio

from .window import SigloWindow

class AnyDeviceManager(gatt.DeviceManager):
    def device_discovered(self, device):
        print("Discovered [%s] %s" % (device.mac_address, device.alias()))

class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.gnome.siglo',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = SigloWindow(application=self)
        win.present()
        manager = AnyDeviceManager(adapter_name='hci0')
        manager.start_discovery()
        manager.run()

def main(version):
    app = Application()
    return app.run(sys.argv)


