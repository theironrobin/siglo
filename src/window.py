
from gi.repository import Gtk
from .bluetooth import InfiniTimeDevice
#import lib.ble_legacy_dfu_controller as BLDC
from .ble_legacy_dfu_controller import BleDfuControllerLegacy
from .unpacker import Unpacker

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'
    info_scan_pass = Gtk.Template.Child()
    scan_fail_box = Gtk.Template.Child()
    scan_pass_box = Gtk.Template.Child()
    ota_picked_box = Gtk.Template.Child()
    ota_selection_box = Gtk.Template.Child()
    main_info = Gtk.Template.Child()
    bt_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.ota_file = None
        self.manager = None
        super().__init__(**kwargs)

    def done_scanning(self, manager):
        self.manager = manager
        scan_result = manager.get_scan_result()
        self.bt_spinner.set_visible(False)
        if (scan_result):
            self.main_info.set_text("Done Scanning...Success")
            self.info_scan_pass.set_text(manager.alias + " Found!\n\nAdapter Name: "+ manager.adapter_name +"\nMac Address: " + manager.get_mac_address())
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

    @Gtk.Template.Callback()
    def ota_file_selected(self, widget):
        filename = widget.get_filename()
        self.ota_file = filename
        self.main_info.set_text("File Chosen: " + filename)
        self.ota_picked_box.set_visible(True)
        self.ota_selection_box.set_visible(False)

    @Gtk.Template.Callback()
    def ota_cancel_button_clicked(self, widget):
        self.main_info.set_text("Choose another OTA File")
        self.ota_picked_box.set_visible(False)
        self.ota_selection_box.set_visible(True)

    @Gtk.Template.Callback()
    def flash_it_button_clicked(self, widget):
        self.main_info.set_text("Starting OTA Update...")
        self.bt_spinner.set_visible(True)
        self.ota_picked_box.set_visible(False)
        unpacker = Unpacker()
        try:
            hexfile, datfile = unpacker.unpack_zipfile(self.ota_file)	
        except Exception as e:
            print("ERR")
            print(e)
            pass
        ble_dfu = BleDfuControllerLegacy(self.manager.get_mac_address(), hexfile, datfile)

        ble_dfu.input_setup()

        # Connect to peer device. Assume application mode.
        if ble_dfu.scan_and_connect():
            if not ble_dfu.check_DFU_mode():
                print("Need to switch to DFU mode")
                success = ble_dfu.switch_to_dfu_mode()
                if not success:
                    print("Couldn't reconnect")
        else:
            # The device might already be in DFU mode (MAC + 1)
            ble_dfu.target_mac_increase(1)

            # Try connection with new address
            print("Couldn't connect, will try DFU MAC")
            if not ble_dfu.scan_and_connect():
                raise Exception("Can't connect to device")
        GObject.threads_init()
        Gio.io_scheduler_push_job(slow_stuff, None, GLib.PRIORITY_DEFAULT, None)
        
        ble_dfu.start()

        # Disconnect from peer device if not done already and clean up.
        ble_dfu.disconnect()
        self.main_info.set_text("OTA Update Complete")
        self.bt_spinner.set_visible(False)

        
