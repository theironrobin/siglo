import subprocess
import configparser
import threading
import urllib.request
from pathlib import Path
import gatt
from gi.repository import Gtk, GObject, GLib
from .bluetooth import (
    InfiniTimeDevice,
    InfiniTimeManager,
    BluetoothDisabled,
    NoAdapterFound,
)
from .ble_dfu import InfiniTimeDFU
from .unpacker import Unpacker
from .quick_deploy import *
from .config import config


class ConnectionThread(threading.Thread):
    def __init__(self, manager, mac, callback):
        threading.Thread.__init__(self)
        self.mac = mac
        self.manager = manager
        self.callback = callback
        self.device = None

    def run(self):
        self.device = InfiniTimeDevice(manager=self.manager, mac_address=self.mac)
        self.device.services_done = self.data_received
        self.device.connect()

    def data_received(self):
        firmware = bytes(self.device.firmware).decode()
        if self.device.battery == -1:
            battery = "n/a"
        else:
            battery = "{}%".format(self.device.battery)
        GLib.idle_add(self.callback, [firmware, battery])


@Gtk.Template(resource_path="/com/github/alexr4535/siglo/window.ui")
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "SigloWindow"
    # Navigation
    main_stack = Gtk.Template.Child()
    header_stack = Gtk.Template.Child()

    # Watches view
    watches_listbox = Gtk.Template.Child()

    # Watch view
    watch_name = Gtk.Template.Child()
    watch_address = Gtk.Template.Child()
    watch_firmware = Gtk.Template.Child()
    watch_battery = Gtk.Template.Child()
    ota_pick_tag_combobox = Gtk.Template.Child()
    ota_pick_asset_combobox = Gtk.Template.Child()
    firmware_run = Gtk.Template.Child()
    firmware_file = Gtk.Template.Child()
    firmware_run_file = Gtk.Template.Child()
    keep_paired_switch = Gtk.Template.Child()

    # Flasher
    dfu_stack = Gtk.Template.Child()
    dfu_progress_bar = Gtk.Template.Child()
    dfu_progress_text = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.ble_dfu = None
        self.ota_file = None
        self.manager = None
        self.current_mac = None
        self.asset = None
        self.asset_download_url = None
        self.tag = None
        self.conf = config()
        super().__init__(**kwargs)
        GObject.threads_init()
        self.full_list = get_quick_deploy_list()
        if self.conf.get_property("deploy_type") == "manual":
            self.auto_switch_deploy_type = True
            self.deploy_type_switch.set_active(True)
        else:
            self.auto_switch_deploy_type = False
        if self.conf.get_property("paired"):
            self.auto_switch_paired = True
        else:
            self.auto_switch_paired = False
        GObject.signal_new(
            "flash-signal",
            self,
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_PYOBJECT,
            (GObject.TYPE_PYOBJECT,),
        )

    def disconnect_paired_device(self):
        try:
            devices = self.manager.devices()
            for d in devices:
                if d.mac_address == self.manager.get_mac_address() and d.is_connected():
                    d.disconnect()
        finally:
            self.conf.set_property("paired", "False")

    def destroy_manager(self):
        if self.manager:
            self.disconnect_paired_device()
            self.manager.stop()
            self.manager = None

    def make_watch_row(self, name, mac):
        row = Gtk.ListBoxRow()
        grid = Gtk.Grid()
        grid.set_hexpand(True)
        grid.set_row_spacing(8)
        grid.set_column_spacing(8)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        grid.set_margin_left(8)
        grid.set_margin_right(8)
        row.add(grid)

        icon = Gtk.Image.new_from_resource("/com/github/alexr4535/siglo/watch-icon.svg")
        grid.attach(icon, 0, 0, 1, 2)

        label_alias = Gtk.Label(label="Name", xalign=1.0)
        label_alias.get_style_context().add_class("dim-label")
        grid.attach(label_alias, 1, 0, 1, 1)
        value_alias = Gtk.Label(label=name, xalign=0.0)
        value_alias.set_hexpand(True)
        grid.attach(value_alias, 2, 0, 1, 1)

        label_mac = Gtk.Label(label="Address", xalign=1.0)
        label_mac.get_style_context().add_class("dim-label")
        grid.attach(label_mac, 1, 1, 1, 1)
        value_mac = Gtk.Label(label=mac, xalign=0.0)
        grid.attach(value_mac, 2, 1, 1, 1)

        arrow = Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.BUTTON)
        grid.attach(arrow, 4, 0, 1, 2)

        row.show_all()
        return row

    def do_scanning(self):
        print("Start scanning")
        self.main_stack.set_visible_child_name("scan")
        self.header_stack.set_visible_child_name("scan")
        if not self.manager:
            # create manager if not present yet
            try:
                self.manager = InfiniTimeManager()
            except (gatt.errors.NotReady, BluetoothDisabled):
                print("Bluetooth is disabled")
                self.main_stack.set_visible_child_name("nodevice")
            except NoAdapterFound:
                print("No bluetooth adapter found")
                self.main_stack.set_visible_child_name("nodevice")
        if not self.manager:
            return

        if self.conf.get_property("paired"):
            self.disconnect_paired_device()

        self.depopulate_listbox()
        self.manager.scan_result = False
        try:
            self.manager.scan_for_infinitime()
        except (gatt.errors.NotReady, gatt.errors.Failed) as e:
            print(e)
            self.main_stack.set_visible_child_name("nodevice")
            self.destroy_manager()

        if len(self.manager.get_device_set()) > 0:
            self.main_stack.set_visible_child_name("watches")
            self.header_stack.set_visible_child_name("watches")
        else:
            self.main_stack.set_visible_child_name("nodevice")

        for mac in self.manager.get_device_set():
            print("Found {}".format(mac))
            row = self.make_watch_row(self.manager.aliases[mac], mac)
            row.mac = mac
            row.alias = self.manager.aliases[mac]
            self.watches_listbox.add(row)
        self.populate_tagbox()

    def depopulate_listbox(self):
        children = self.watches_listbox.get_children()
        for child in children:
            self.watches_listbox.remove(child)

    def populate_tagbox(self):
        self.ota_pick_tag_combobox.remove_all()
        for tag in get_tags(self.full_list):
            self.ota_pick_tag_combobox.append_text(tag)

    def populate_assetbox(self):
        self.ota_pick_asset_combobox.remove_all()
        for asset in get_assets_by_tag(self.tag, self.full_list):
            self.ota_pick_asset_combobox.append_text(asset)

    def done_scanning_multi(self, info_prefix):
        if self.manager:
            scan_result = self.manager.get_scan_result()
        self.bt_spinner.set_visible(False)
        self.rescan_button.set_visible(True)
        if self.manager and scan_result:
            info_suffix = "\n[INFO ] Scan Succeeded"
            self.populate_listbox()
        else:
            info_suffix += "\n[INFO ] Scan Failed"
            self.scan_fail_box.set_visible(True)
        self.main_info.set_text(info_prefix + info_suffix)

    def done_scanning_singleton(self, manager):
        self.manager = manager
        scan_result = manager.get_scan_result()
        print("[INFO ] Single-Device Mode")
        if scan_result:
            print("[INFO ] Scan Succeeded")
            print(
                "[INFO ] Got watch {} on {}".format(
                    manager.get_mac_address(), manager.adapter_name
                )
            )

            if self.deploy_type == "quick":
                self.auto_bbox_scan_pass.set_visible(True)
            if self.deploy_type == "manual":
                self.bbox_scan_pass.set_visible(True)
        else:
            print("[INFO ] Scan Failed")
            self.main_stack.set_visible_child_name("nodevice")

    def callback_device_connect(self, data):
        firmware, battery = data

        self.watch_firmware.set_text(firmware)
        self.watch_battery.set_text(battery)

    @Gtk.Template.Callback()
    def on_watches_listbox_row_activated(self, widget, row):
        mac = row.mac
        self.current_mac = mac
        alias = row.alias

        if self.conf.get_property("paired"):
            self.disconnect_paired_device()

        if self.keep_paired_switch.get_active():
            self.conf.set_property("paired", "True")

        if self.manager is not None:
            thread = ConnectionThread(self.manager, mac, self.callback_device_connect)
            thread.daemon = True
            thread.start()

        self.watch_name.set_text(alias)
        self.watch_address.set_text(mac)
        self.main_stack.set_visible_child_name("watch")
        self.header_stack.set_visible_child_name("watch")

    @Gtk.Template.Callback()
    def on_back_to_devices_clicked(self, *args):
        self.main_stack.set_visible_child_name("watches")
        self.header_stack.set_visible_child_name("watches")

    @Gtk.Template.Callback()
    def ota_pick_tag_combobox_changed_cb(self, widget):
        self.tag = self.ota_pick_tag_combobox.get_active_text()
        self.populate_assetbox()

    @Gtk.Template.Callback()
    def ota_pick_asset_combobox_changed_cb(self, widget):
        self.asset = self.ota_pick_asset_combobox.get_active_text()
        if self.asset is not None:
            self.firmware_run.set_sensitive(True)
            self.asset_download_url = get_download_url(
                self.asset, self.tag, self.full_list
            )
        else:
            self.firmware_run.set_sensitive(False)
            self.asset_download_url = None

    @Gtk.Template.Callback()
    def firmware_file_file_set_cb(self, widget):
        print("File set!")
        filename = widget.get_filename()
        self.ota_file = filename
        self.firmware_run_file.set_sensitive(True)

    @Gtk.Template.Callback()
    def rescan_button_clicked(self, widget):
        self.do_scanning()

    @Gtk.Template.Callback()
    def on_bluetooth_settings_clicked(self, widget):
        subprocess.Popen(["gnome-control-center", "bluetooth"])

    @Gtk.Template.Callback()
    def sync_time_button_clicked(self, widget):
        if self.manager is not None:
            print("Sync Time button clicked...")
            device = InfiniTimeDevice(
                manager=self.manager, mac_address=self.manager.get_mac_address()
            )
            device.connect(sync_time=True)
            if device.successful_connection:
                self.main_info.set_text("InfiniTime Sync... Success!")
            else:
                self.main_info.set_text("InfiniTime Sync... Failed!")
            self.scan_pass_box.set_visible(False)
            self.rescan_button.set_visible(True)

    @Gtk.Template.Callback()
    def ota_file_selected(self, widget):
        filename = widget.get_filename()
        self.ota_file = filename
        self.main_info.set_text("File: " + filename.split("/")[-1])
        self.ota_picked_box.set_visible(True)
        self.ota_selection_box.set_visible(False)
        self.ota_picked_box.set_sensitive(True)

    @Gtk.Template.Callback()
    def ota_cancel_button_clicked(self, widget):
        if self.conf.get_property("deploy_type") == "quick":
            self.ota_pick_asset_combobox.remove_all()
            self.ota_pick_tag_combobox.remove_all()
            self.populate_tagbox()
            self.ota_picked_box.set_sensitive(False)
        if self.conf.get_property("deploy_type") == "manual":
            self.main_info.set_text("Choose another OTA File")
            self.ota_picked_box.set_visible(False)
            self.ota_selection_box.set_visible(True)

    @Gtk.Template.Callback()
    def firmware_run_file_clicked_cb(self, widget):
        self.dfu_stack.set_visible_child_name("ok")
        self.main_stack.set_visible_child_name("firmware")

        self.firmware_mode = "manual"

        self.start_flash()

    @Gtk.Template.Callback()
    def on_firmware_run_clicked(self, widget):
        self.dfu_stack.set_visible_child_name("ok")
        self.main_stack.set_visible_child_name("firmware")

        self.firmware_mode = "auto"

        file_name = "/tmp/" + self.asset

        print("Downloading {}".format(self.asset_download_url))

        local_filename, headers = urllib.request.urlretrieve(
            self.asset_download_url, file_name
        )
        self.ota_file = local_filename

        self.start_flash()

    def start_flash(self):
        unpacker = Unpacker()
        try:
            binfile, datfile = unpacker.unpack_zipfile(self.ota_file)
        except Exception as e:
            print("ERR")
            print(e)
            pass

        self.ble_dfu = InfiniTimeDFU(
            mac_address=self.current_mac,
            manager=self.manager,
            window=self,
            firmware_path=binfile,
            datfile_path=datfile,
            verbose=False,
        )
        self.ble_dfu.on_failure = self.on_flash_failed
        self.ble_dfu.on_success = self.on_flash_done
        self.ble_dfu.input_setup()
        self.dfu_progress_text.set_text(self.get_prog_text())
        self.ble_dfu.connect()

    def on_flash_failed(self):
        self.dfu_stack.set_visible_child_name("fail")

    def on_flash_done(self):
        self.dfu_stack.set_visible_child_name("done")

    @Gtk.Template.Callback()
    def on_dfu_retry_clicked(self, widget):
        if self.firmware_mode == "auto":
            self.on_firmware_run_clicked(widget)

    @Gtk.Template.Callback()
    def flash_it_button_clicked(self, widget):
        if self.deploy_type == "quick":
            file_name = "/tmp/" + self.asset
            local_filename, headers = urllib.request.urlretrieve(
                self.asset_download_url, file_name
            )
            self.ota_file = local_filename

    @Gtk.Template.Callback()
    def deploy_type_toggled(self, widget):
        if (
            self.conf.get_property("deploy_type") == "manual"
            and self.auto_switch_deploy_type
        ):
            self.auto_switch_deploy_type = False
        else:
            if self.conf.get_property("deploy_type") == "quick":
                self.conf.set_property("deploy_type", "manual")
            else:
                self.conf.set_property("deploy_type", "quick")
            self.rescan_button.emit("clicked")

    @Gtk.Template.Callback()
    def pair_switch_toggled(self, widget):
        self.conf.set_property("last_paired_device", self.manager.get_mac_address())
        print(self.manager)
        if self.conf.get_property("paired") and self.auto_switch_paired == True:
            self.auto_switch_paired = False
        else:
            if not self.conf.get_property("paired"):
                self.conf.set_property("paired", "True")
                if self.manager is not None:
                    print("Pairing with", self.manager.get_mac_address())
                    device = InfiniTimeDevice(
                        manager=self.manager, mac_address=self.manager.get_mac_address()
                    )
                    device.connect(sync_time=True)
                    subprocess.call(["systemctl", "--user", "daemon-reload"])
                    subprocess.call(["systemctl", "--user", "restart", "siglo"])
            else:
                try:
                    device = InfiniTimeDevice(
                        manager=self.manager, mac_address=self.manager.get_mac_address()
                    )
                    device.disconnect()
                except dbus.exceptions.DBusException:
                    raise BluetoothDisabled
                finally:
                    subprocess.call(["systemctl", "--user", "daemon-reload"])
                    subprocess.call(["systemctl", "--user", "stop", "siglo"])
                    self.conf.set_property("paired", "False")

    def update_progress_bar(self):
        self.dfu_progress_bar.set_fraction(
            self.ble_dfu.total_receipt_size / self.ble_dfu.image_size
        )
        self.dfu_progress_text.set_text(self.get_prog_text())

    def get_prog_text(self):
        return (
            str(self.ble_dfu.total_receipt_size)
            + " / "
            + str(self.ble_dfu.image_size)
            + " bytes received"
        )

    def show_complete(self, success):
        if success:
            self.rescan_button.set_sensitive("True")
            self.main_info.set_text("OTA Update Complete")
        else:
            self.main_info.set_text("OTA Update Failed")
        self.bt_spinner.set_visible(False)
        self.sync_time_button.set_visible(True)
        self.dfu_progress_box.set_visible(False)
        self.ota_picked_box.set_visible(True)
        if self.conf.get_property("deploy_type") == "quick":
            self.auto_bbox_scan_pass.set_visible(True)
