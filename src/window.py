import subprocess
import configparser
import threading
import urllib.request
import dbus
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

@Gtk.Template(resource_path="/com/github/alexr4535/siglo/window.ui")
class SigloWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "SigloWindow"
    # Navigation
    main_stack = Gtk.Template.Child()

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
    disconnect_button = Gtk.Template.Child()
    disconnect_stack = Gtk.Template.Child()
    header_stack_revealer = Gtk.Template.Child()

    # Flasher
    dfu_stack = Gtk.Template.Child()
    dfu_progress_bar = Gtk.Template.Child()
    dfu_progress_text = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.ble_dfu = None
        self.ota_file = None
        self.current_mac = None
        self.asset = None
        self.asset_download_url = None
        self.tag = None
        self.conf = config()
        super().__init__(**kwargs)
        GObject.threads_init()
        self.full_list = get_quick_deploy_list()
        GObject.signal_new(
            "flash-signal",
            self,
            GObject.SIGNAL_RUN_LAST,
            GObject.TYPE_PYOBJECT,
            (GObject.TYPE_PYOBJECT,),
        )

        try:
            self.bus = dbus.SessionBus()
            self.daemon_obj = self.bus.get_object('com.github.alexr4535.siglo.Daemon', '/com/github/alexr4535/siglo/Daemon')
            self.daemon_iface = dbus.Interface(self.daemon_obj,dbus_interface='com.github.alexr4535.siglo.Daemon')
            self.daemon_service_iface = dbus.Interface(self.daemon_obj,dbus_interface='com.github.alexr4535.siglo.Daemon.Service')
        except :
            print("Could not talk to Siglo Daemon, exiting.")
            self.quit()

        self.daemon_iface.connect_to_signal("ServicesResolved",self.services_resolved)

        if self.daemon_iface.IsConnected():
            self.current_mac = self.daemon_iface.GetConnectedDevice()
            self.services_resolved()
        else:
            self.do_scanning()

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
        spinner = Gtk.Spinner()
        spinner.start()
        stack = Gtk.Stack()
        stack.add_named(arrow,"arrow")
        stack.add_named(spinner,"spinner")
        grid.attach(stack, 4, 0, 1, 2)

        row.show_all()
        return row

    def scanning_complete(self):
        #self.main_stack.set_visible_child_name("nodevice")
        #self.destroy_manager()
        self.header_stack_revealer.set_reveal_child(True)
        try:
            devices = self.daemon_iface.GetDevices()
            if len(devices.values()) > 0:
                self.main_stack.set_visible_child_name("watches")
            else:
                self.main_stack.set_visible_child_name("nodevice")
            for mac in devices.keys():
                print("Found {}".format(mac))
                row = self.make_watch_row(devices[mac], mac)
                row.mac = mac
                row.alias = devices[mac]
                self.watches_listbox.add(row)
        except AttributeError as e:
            print(e)
            self.main_stack.set_visible_child_name("nodevice")
        self.populate_tagbox()

    def error_handler(self, error):
        print("ich bin der error handler")
        print(error)

    def do_scanning(self):
        self.main_stack.set_sensitive(True)
        print("Start scanning")
        self.main_stack.set_visible_child_name("scan")

        self.depopulate_listbox()
        self.daemon_iface.Scan(1.5, reply_handler=self.scanning_complete, error_handler=self.error_handler)

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

    def services_resolved(self):
        self.watch_firmware.set_text(self.daemon_service_iface.GetFirmwareVersion())
        self.watch_battery.set_text(str(int(self.daemon_service_iface.GetPowerLevel())) + " %")

        self.watch_name.set_text(self.daemon_iface.GetDevices()[self.current_mac])
        self.watch_address.set_text(self.current_mac)
        self.disconnect_stack.set_visible_child_name("disconnect_label")
        self.header_stack_revealer.set_reveal_child(False)
        self.main_stack.set_visible_child_name("watch")

    def connecting_complete(self):
        print("connecting complete")
        #Wait for the services to be resolved and continue in self.services_resolved

    @Gtk.Template.Callback()
    def on_watches_listbox_row_activated(self, widget, row):
        mac = row.mac
        self.current_mac = mac
        alias = row.alias

        row.get_children()[0].get_child_at(4,1).set_visible_child_name("spinner")

        self.current_mac = mac
        self.daemon_iface.Connect(mac,
                                  reply_handler=self.connecting_complete,
                                  error_handler=self.error_handler
                                  )

    @Gtk.Template.Callback()
    def on_disconnect_clicked(self,button):
        self.daemon_iface.Disconnect(reply_handler=self.do_scanning,error_handler=self.error_handler)
        self.main_stack.set_sensitive(False)
        self.disconnect_stack.set_visible_child_name("disconnect_spinner")

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
    def ota_file_selected(self, widget):
        filename = widget.get_filename()
        self.ota_file = filename
        self.main_info.set_text("File: " + filename.split("/")[-1])
        self.ota_picked_box.set_visible(True)
        self.ota_selection_box.set_visible(False)
        self.ota_picked_box.set_sensitive(True)

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

        self.daemon_iface.Disconnect()
        self.daemon_iface.Quit()
        self.start_flash()

    def start_flash(self):
        unpacker = Unpacker()
        try:
            binfile, datfile = unpacker.unpack_zipfile(self.ota_file)
        except Exception as e:
            print("ERR")
            print(e)
            pass

        dfu_manager = None
        try:
            dfu_manager = InfiniTimeManager()
        except (gatt.errors.NotReady, BluetoothDisabled):
            print("Bluetooth is disabled")
        except NoAdapterFound:
            print("No bluetooth adapter found")

        self.ble_dfu = InfiniTimeDFU(
            mac_address=self.current_mac,
            manager=dfu_manager,
            window=self,
            firmware_path=binfile,
            datfile_path=datfile,
            verbose=True,
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
        self.dfu_progress_box.set_visible(False)
        self.ota_picked_box.set_visible(True)
        if self.conf.get_property("deploy_type") == "quick":
            self.auto_bbox_scan_pass.set_visible(True)
