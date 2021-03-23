
import threading
from gi.repository import Gtk, GObject
from .bluetooth import InfiniTimeDevice
from .ble_legacy_dfu_controller import BleDfuControllerLegacy
from .unpacker import Unpacker

# calls f on another thread
def async_call(f, on_done):
    if not on_done:
        on_done = lambda r, e: None

    def do_call():
        result = None
        error = None

        try:
            result = f()
        except Exception as err:
            error = err

        GObject.idle_add(lambda: on_done(result, error))
    thread = threading.Thread(target = do_call)
    thread.start()

@Gtk.Template(resource_path='/org/gnome/siglo/window.ui')
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'SigloWindow'
    info_scan_pass = Gtk.Template.Child()
    scan_fail_box = Gtk.Template.Child()
    scan_pass_box = Gtk.Template.Child()
    sync_time_button = Gtk.Template.Child()
    ota_picked_box = Gtk.Template.Child()
    ota_selection_box = Gtk.Template.Child()
    main_info = Gtk.Template.Child()
    bt_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.ble_dfu = None
        self.ota_file = None
        self.manager = None
        super().__init__(**kwargs)
        GObject.threads_init()

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
        self.main_info.set_text("File Chosen: " + filename.split("/")[-1])
        self.ota_picked_box.set_visible(True)
        self.ota_selection_box.set_visible(False)

    @Gtk.Template.Callback()
    def ota_cancel_button_clicked(self, widget):
        self.main_info.set_text("Choose another OTA File")
        self.ota_picked_box.set_visible(False)
        self.ota_selection_box.set_visible(True)

    @Gtk.Template.Callback()
    def flash_it_button_clicked(self, widget):
        unpacker = Unpacker()
        try:
            hexfile, datfile = unpacker.unpack_zipfile(self.ota_file)	
        except Exception as e:
            print("ERR")
            print(e)
            pass
        self.ble_dfu = BleDfuControllerLegacy(self.manager.get_mac_address(), hexfile, datfile)
        self.ble_dfu.input_setup()

        # Connect to peer device. Assume application mode.
        if self.ble_dfu.scan_and_connect():
            if not self.ble_dfu.check_DFU_mode():
                print("Need to switch to DFU mode")
                success = self.ble_dfu.switch_to_dfu_mode()
                if not success:
                    print("Couldn't reconnect")
        else:
            # The device might already be in DFU mode (MAC + 1)
            self.ble_dfu.target_mac_increase(1)

            # Try connection with new address
            print("Couldn't connect, will try DFU MAC")
            if not self.ble_dfu.scan_and_connect():
                raise Exception("Can't connect to device")
    
        async_call(self.slow_load, self.slow_complete)
    
    def slow_complete(self, results, errors):
        # Disconnect from peer device if not done already and clean up.
        self.ble_dfu.disconnect()
        self.main_info.set_text("OTA Update Complete")
        self.bt_spinner.set_visible(False)
        self.sync_time_button.set_visible(True)
    
    def slow_load(self):
        self.main_info.set_text("Updating Firmware...")
        self.bt_spinner.set_visible(True)
        self.ota_picked_box.set_visible(False)
        self.sync_time_button.set_visible(False)
        self.ble_dfu.start()

        
