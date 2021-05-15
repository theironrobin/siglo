from array import array
import gatt
import os
from .util import *
import math
from struct import unpack

class InfiniTimeDFU(gatt.Device):
    # Class constants
    UUID_DFU_SERVICE = "00001530-1212-efde-1523-785feabcd123"
    UUID_CTRL_POINT = "00001531-1212-efde-1523-785feabcd123"
    UUID_PACKET = "00001532-1212-efde-1523-785feabcd123"
    UUID_VERSION = "00001534-1212-efde-1523-785feabcd123"

    def __init__(self, mac_address, manager, window, firmware_path, datfile_path, verbose):
        self.firmware_path = firmware_path
        self.datfile_path = datfile_path
        self.target_mac = mac_address
        self.window = window
        self.verbose = verbose
        self.current_step = 0
        self.pkt_receipt_interval = 10
        self.pkt_payload_size = 20
        self.size_per_receipt = self.pkt_payload_size * self.pkt_receipt_interval
        self.done = False
        self.packet_recipt_count = 0
        self.total_receipt_size = 0
        self.update_in_progress = False
        self.caffeinator = Caffeinator()

        super().__init__(mac_address, manager)

    def connect(self):
        self.successful_connection = True
        super().connect()

    def input_setup(self):
        """Bin: read binfile into bin_array"""
        print(
            "preparing "
            + os.path.split(self.firmware_path)[1]
            + " for "
            + self.target_mac
        )

        if self.firmware_path == None:
            raise Exception("input invalid")

        name, extent = os.path.splitext(self.firmware_path)

        if extent == ".bin":
            self.bin_array = array("B", open(self.firmware_path, "rb").read())

            self.image_size = len(self.bin_array)
            print("Binary image size: %d" % self.image_size)
            print(
                "Binary CRC32: %d" % crc32_unsigned(array_to_hex_string(self.bin_array))
            )
            return
        raise Exception("input invalid")

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        self.successful_connection = False
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))
        self.window.show_complete(success=(not self.update_in_progress))

    def characteristic_enable_notifications_succeeded(self, characteristic):
        if self.verbose and characteristic.uuid == self.UUID_CTRL_POINT:
            print("Notification Enable succeeded for Control Point Characteristic")
        self.step_one()

    def characteristic_write_value_succeeded(self, characteristic):
        if self.verbose and characteristic.uuid == self.UUID_CTRL_POINT:
            print(
                "Characteristic value was written successfully for Control Point Characteristic"
            )
        if self.verbose and characteristic.uuid == self.UUID_PACKET:
            print(
                "Characteristic value was written successfully for Packet Characteristic"
            )
        if self.current_step == 1:
            self.step_two()
        elif self.current_step == 3:
            self.step_four()
        elif self.current_step == 5:
            self.step_six()
        elif self.current_step == 6:
            print("Begin DFU")
            self.caffeinator.caffeinate()
            self.step_seven()

    def characteristic_write_value_failed(self, characteristic, error):
        print("[WARN ] write value failed", str(error))
        self.update_in_progress = True
        self.disconnect()

    def characteristic_value_updated(self, characteristic, value):
        if self.verbose:
            if characteristic.uuid == self.UUID_CTRL_POINT:
                print(
                    "Characteristic value was updated for Control Point Characteristic"
                )
            if characteristic.uuid == self.UUID_PACKET:
                print("Characteristic value was updated for Packet Characteristic")
            print("New value is:", value)

        hexval = array_to_hex_string(value)

        if hexval[:4] == "1001":
            # Response::StartDFU
            if hexval[4:] == "01":
                self.step_three()
            else:
                print("[WARN ] StartDFU failed")
                self.disconnect()
        elif hexval[:4] == "1002":
            # Response::InitDFUParameters
            if hexval[4:] == "01":
                self.step_five()
            else:
                print("[WARN ] InitDFUParameters failed")
                self.disconnect()
        elif hexval[:2] == "11":
            # PacketReceiptNotification
            self.packet_recipt_count += 1
            self.total_receipt_size += self.size_per_receipt
            # verify that the returned size correspond to what was sent
            ack_size = unpack('<I', value[1:])[0]
            if ack_size != self.total_receipt_size:
                print("[WARN ] PacketReceiptNotification failed")
                print("        acknowledged {} : expected {}".format(ack_size, self.total_receipt_size))
                self.disconnect()
            self.window.update_progress_bar()
            if self.verbose:
                print("[INFO ] receipt count", str(self.packet_recipt_count))
                print("[INFO ] receipt size", self.total_receipt_size, "out of", self.image_size)
                print("[INFO ] progress:", (self.total_receipt_size / self.image_size)*100, "%")
            if self.done != True:
                self.i += self.pkt_payload_size
                self.step_seven()
        elif hexval[:4] == "1003":
            # Response::ReceiveFirmwareImage::NoError
            if hexval[4:] == "01":
                self.step_eight()
            else:
                print("[WARN ] ReceiveFirmwareImage failed")
                self.disconnect()
        elif hexval[:4] == "1004":
            # Response::ValidateFirmware
            if hexval[4:] == "01":
                self.step_nine()
            else:
                print("[WARN ] ValidateFirmware failed")
                self.disconnect()

    def services_resolved(self):
        super().services_resolved()
        self.update_in_progress = True

        print("[%s] Resolved services" % (self.mac_address))
        ble_dfu_serv = next(s for s in self.services if s.uuid == self.UUID_DFU_SERVICE)
        self.ctrl_point_char = next(
            c for c in ble_dfu_serv.characteristics if c.uuid == self.UUID_CTRL_POINT
        )
        self.packet_char = next(
            c for c in ble_dfu_serv.characteristics if c.uuid == self.UUID_PACKET
        )

        if self.verbose:
            print("[INFO ] Enabling notifications for Control Point Characteristic")
        self.ctrl_point_char.enable_notifications()

    def step_one(self):
        self.current_step = 1
        if self.verbose:
            print(
                "[INFO ] Sending ('Start DFU' (0x01), 'Application' (0x04)) to DFU Control Point"
            )
        self.ctrl_point_char.write_value(bytearray.fromhex("01 04"))

    def step_two(self):
        self.current_step = 2
        if self.verbose:
            print("[INFO ] Sending Image size to the DFU Packet characteristic")
        x = len(self.bin_array)
        hex_size_array_lsb = uint32_to_bytes_le(x)
        zero_pad_array_le(hex_size_array_lsb, 8)
        self.packet_char.write_value(bytearray(hex_size_array_lsb))
        print("[INFO ] Waiting for Image Size notification")

    def step_three(self):
        self.current_step = 3
        if self.verbose:
            print("[INFO ] Sending 'INIT DFU' + Init Packet Command")
        self.ctrl_point_char.write_value(bytearray.fromhex("02 00"))

    def step_four(self):
        self.current_step = 4
        if self.verbose:
            print("[INFO ] Sending the Init image (DAT)")
        self.packet_char.write_value(bytearray(self.get_init_bin_array()))
        if self.verbose:
            print("[INFO ] Send 'INIT DFU' + Init Packet Complete Command")
        self.ctrl_point_char.write_value(bytearray.fromhex("02 01"))
        print("[INFO ] Waiting for INIT DFU notification")

    def step_five(self):
        self.current_step = 5
        if self.verbose:
            print("Setting pkt receipt notification interval")
        self.ctrl_point_char.write_value(bytearray.fromhex("08 0A"))

    def step_six(self):
        self.current_step = 6
        if self.verbose:
            print(
                "[INFO ] Send 'RECEIVE FIRMWARE IMAGE' command to set DFU in firmware receive state"
            )
        self.ctrl_point_char.write_value(bytearray.fromhex("03"))
        self.segment_count = 0
        self.i = 0
        self.segment_total = int(
            math.ceil(self.image_size / float(self.pkt_payload_size))
        )

    def step_seven(self):
        self.current_step = 7
        # Send bin_array contents as as series of packets (burst mode).
        # Each segment is pkt_payload_size bytes long.
        # For every pkt_receipt_interval sends, wait for notification.
        segment = self.bin_array[self.i : self.i + self.pkt_payload_size]
        self.packet_char.write_value(segment)
        self.segment_count += 1
        if self.segment_count == self.segment_total:
            self.done = True
        elif (self.segment_count % self.pkt_receipt_interval) != 0:
            self.i += self.pkt_payload_size
            self.step_seven()
        else:
            if self.verbose:
                print("[INFO ] Waiting for Packet Receipt Notifiation")

    def step_eight(self):
        self.current_step = 8
        print("[INFO ] Sending Validate command")
        self.ctrl_point_char.write_value(bytearray.fromhex("04"))

    def step_nine(self):
        self.current_step = 9
        print("[INFO ] Activate and reset")
        self.ctrl_point_char.write_value(bytearray.fromhex("05"))
        self.update_in_progress = False
        self.disconnect()
        self.caffeinator.decaffeinate()

    def get_init_bin_array(self):
        # Open the DAT file and create array of its contents
        init_bin_array = array("B", open(self.datfile_path, "rb").read())
        return init_bin_array

class Caffeinator():
    def __init__(self):
        try:
            from gi.repository import Gio
            self.gio = Gio

            self.gnome_session = self.safe_lookup(
                "org.gnome.desktop.session",
                "GNOME session not found, you're on your own for idle timeouts"
            )
            if self.gnome_session:
                self.idle_delay = self.gnome_session.get_uint("idle-delay")

            self.gnome_power = self.safe_lookup(
                "org.gnome.settings-daemon.plugins.power",
                "GNOME power settings not found, you're on your own for system sleep"
            )
            if self.gnome_power:
                self.sleep_inactive_battery_timeout = self.gnome_power.get_int("sleep-inactive-battery-timeout")
                self.sleep_inactive_ac_timeout = self.gnome_power.get_int("sleep-inactive-ac-timeout")
                self.idle_dim = self.gnome_power.get_boolean("idle-dim")
        except ImportError:
            print("[INFO ] GIO not found, disabling caffeine")
        except AttributeError:
            print("[INFO ] Unable to load GIO schemas, disabling caffeine")

    # Look up a Gio Settings schema without crashing if it doesn't exist
    def safe_lookup(self, path, failmsg=None):
        try:
            exists = self.gio.SettingsSchema.lookup(path)
        except AttributeError:
            # SettingsSchema is new, if it doesn't exist
            # then fall back to legacy schema lookup
            exists = (path in self.gio.Settings.list_schemas())

        if exists:
            return self.gio.Settings.new(path)
        else:
            if failmsg:
                print("[INFO ] {}".format(failmsg))
            return None

    def caffeinate(self):
        if self.gnome_session:
            print("[INFO ] Disabling GNOME idle timeout")
            self.gnome_session.set_uint("idle-delay", 0)
        if self.gnome_power:
            print("[INFO ] Disabling GNOME inactivity sleeping")
            self.gnome_power.set_int("sleep-inactive-battery-timeout", 0)
            self.gnome_power.set_int("sleep-inactive-ac-timeout", 0)
            self.gnome_power.set_boolean("idle-dim", False)

    def decaffeinate(self):
        if self.gnome_session:
            print("[INFO ] Restoring GNOME idle timeout")
            self.gnome_session.set_uint("idle-delay", self.idle_delay)
        if self.gnome_power:
            print("[INFO ] Restoring GNOME inactivity sleeping")
            self.gnome_power.set_int("sleep-inactive-battery-timeout", self.sleep_inactive_battery_timeout)
            self.gnome_power.set_int("sleep-inactive-ac-timeout", self.sleep_inactive_ac_timeout)
            self.gnome_power.set_boolean("idle-dim", self.idle_dim)
