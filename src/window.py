
from gi.repository import Gtk
import gatt
import dbus

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'

    sync_button = Gtk.Template.Child()
    SigloWindow = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @Gtk.Template.Callback()
    def sync_button_clicked(self, widget):
        pass
        #print("Hello World")

    @Gtk.Template.Callback()
    def on_window_focus(self, widget, user_data):
        print("Hello world!")
        #manager = AnyDeviceManager(adapter_name='hci0')
        #manager.start_discovery()
        #manager.run()

class AnyDeviceManager(gatt.DeviceManager):
    def device_discovered(self, device):
        print("Discovered [%s] %s" % (device.mac_address, device.alias()))



