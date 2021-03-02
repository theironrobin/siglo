
from gi.repository import Gtk

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'
    info_scan_fail = Gtk.Template.Child()
    info_scan_pass = Gtk.Template.Child()
    bbox_scan_fail = Gtk.Template.Child()
    bbox_scan_pass = Gtk.Template.Child()
    bt_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.manager = None
        super().__init__(**kwargs)

    def done_scanning(self, manager):
        scan_result = manager.get_scan_result()
        self.bt_spinner.set_visible(False)
        if (scan_result):
            self.info_scan_pass.set_text("InfiniTime Found!\nMac Address: " + manager.get_mac_address() + "\nConnecting...")
            self.info_scan_pass.set_visible(True)
            self.bbox_scan_pass.set_visible(True)
        else:
            self.manager = manager
            self.info_scan_fail.set_visible(True)
            self.bbox_scan_fail.set_visible(True)

    @Gtk.Template.Callback()
    def rescan_button_clicked(self, widget):
        if self.manager is not None:
            print("Rescan button clicked...")
            self.bt_spinner.set_visible(True)
            self.info_scan_fail.set_visible(False)
            self.bbox_scan_fail.set_visible(False)
            self.manager.scan_for_infinitime()
            self.done_scanning(self.manager)


