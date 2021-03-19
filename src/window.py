
from gi.repository import Gtk
from .bluetooth import InfiniTimeDevice

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'
    info_scan_pass = Gtk.Template.Child()
    scan_fail_box = Gtk.Template.Child()
    scan_pass_box = Gtk.Template.Child()
    main_info = Gtk.Template.Child()
    bt_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.manager = None
        super().__init__(**kwargs)

    def done_scanning(self, manager):
        self.manager = manager
        scan_result = manager.get_scan_result()
        self.bt_spinner.set_visible(False)
        if (scan_result):
            self.main_info.set_text("Done Scanning...Success")
            self.info_scan_pass.set_text("InfiniTime Found!\n\nAdapter Name: "+ manager.adapter_name +"\nMac Address: " + manager.get_mac_address())
            self.scan_pass_box.set_visible(True)
        else:
            self.main_info.set_text("Done Scanning...Failed")
            self.scan_fail_box.set_visible(True)

    @Gtk.Template.Callback()
    def rescan_button_clicked(self, widget):
        if self.manager is not None:
            print("Rescan button clicked...")
            self.main_info.set_text("Rescanning...")
            self.bt_spinner.set_visible(True)
            self.scan_fail_box.set_visible(False)
            self.manager.scan_for_infinitime()
            self.done_scanning(self.manager)

    @Gtk.Template.Callback()
    def sync_time_button_clicked(self, widget):
        if self.manager is not None:
            print("Sync Time button clicked...")
            device = InfiniTimeDevice(manager=self.manager, mac_address=self.manager.get_mac_address())
            device.connect()
            self.main_info.set_text("InfiniTime Sync... Success!")
            self.scan_pass_box.set_visible(False)

