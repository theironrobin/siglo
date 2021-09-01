from os import sync
import gatt
import datetime
import struct
from gi.repository import GObject, Gio
from .config import config

BTSVC_TIME = "00001805-0000-1000-8000-00805f9b34fb"
BTSVC_INFO = "0000180a-0000-1000-8000-00805f9b34fb"
BTSVC_BATT = "0000180f-0000-1000-8000-00805f9b34fb"
BTSVC_ALERT = "00001811-0000-1000-8000-00805f9b34fb"
BTCHAR_FIRMWARE = "00002a26-0000-1000-8000-00805f9b34fb"
BTCHAR_CURRENTTIME = "00002a2b-0000-1000-8000-00805f9b34fb"
BTCHAR_NEWALERT = "00002a46-0000-1000-8000-00805f9b34fb"
BTCHAR_BATTLEVEL = "00002a19-0000-1000-8000-00805f9b34fb"


def get_current_time():
    now = datetime.datetime.now()

    # https://www.bluetooth.com/wp-content/uploads/Sitecore-Media-Library/Gatt/Xml/Characteristics/org.bluetooth.characteristic.current_time.xml
    return bytearray(
        struct.pack(
            "HBBBBBBBB",
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
            now.weekday() + 1,  # numbered 1-7
            int(now.microsecond / 1e6 * 256),  # 1/256th of a second
            0b0001,  # adjust reason
        )
    )


def get_default_adapter():
    """https://stackoverflow.com/a/49017827"""
    import dbus

    bus = dbus.SystemBus()
    try:
        manager = dbus.Interface(
            bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager"
        )
    except dbus.exceptions.DBusException:
        raise BluetoothDisabled

    for path, ifaces in manager.GetManagedObjects().items():
        if ifaces.get("org.bluez.Adapter1") is None:
            continue
        return path.split("/")[-1]
    raise NoAdapterFound


class InfiniTimeManager(gatt.DeviceManager):
    def __init__(self):
        self.conf = config()
        self.device_set = set()
        self.aliases = dict()
        if not self.conf.get_property("paired"):
            self.scan_result = False
            self.adapter_name = get_default_adapter()
            self.conf.set_property("adapter", self.adapter_name)
        else:
            self.scan_result = True
            self.adapter_name = self.conf.get_property("adapter")
        self.mac_address = None
        super().__init__(self.adapter_name)

    def get_scan_result(self):
        if self.conf.get_property("paired"):
            self.scan_result = True
        return self.scan_result

    def get_device_set(self):
        return self.device_set

    def get_adapter_name(self):
        if self.conf.get_property("paired"):
            return self.conf.get_property("adapter")
        return get_default_adapter()

    def set_mac_address(self, mac_address):
        self.mac_address = mac_address

    def get_mac_address(self):
        if self.conf.get_property("paired"):
            self.mac_address = self.conf.get_property("last_paired_device")
        return self.mac_address

    def set_timeout(self, timeout):
        GObject.timeout_add(timeout, self.stop)

    def device_discovered(self, device):
        if device.alias() in ("InfiniTime", "Pinetime-JF", "PineTime"):
            self.scan_result = True
            self.aliases[device.mac_address] = device.alias()
            self.device_set.add(device.mac_address)

    def scan_for_infinitime(self):
        self.start_discovery()
        self.set_timeout(1.5 * 1000)
        self.run()


class InfiniTimeDevice(gatt.Device):
    def __init__(self, mac_address, manager):
        self.conf = config()
        self.mac = mac_address
        self.manager = manager
        super().__init__(mac_address, manager)

    def connect(self):
        self.successful_connection = True
        super().connect()

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))
        self.conf.set_property("last_paired_device", self.mac)

    def connect_failed(self, error):
        super().connect_failed(error)
        self.successful_connection = False
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def characteristic_write_value_succeeded(self, characteristic):
        if not self.conf.get_property("paired"):
            self.disconnect()

    def services_resolved(self):
        super().services_resolved()
        infosvc = None
        timesvc = None
        battsvc = None
        alertsvc = None
        for svc in self.services:
            if svc.uuid == BTSVC_INFO:
                infosvc = svc
            elif svc.uuid == BTSVC_TIME:
                timesvc = svc
            elif svc.uuid == BTSVC_BATT:
                battsvc = svc
            elif svc.uuid == BTSVC_ALERT:
                alertsvc = svc

        if timesvc:
            currenttime = next(
                c
                for c in timesvc.characteristics
                if c.uuid == BTCHAR_CURRENTTIME
            )

            # Update watch time on connection
            currenttime.write_value(get_current_time())

        self.firmware = b"n/a"
        if infosvc:
            info_firmware = next(
                c
                for c in infosvc.characteristics
                if c.uuid == BTCHAR_FIRMWARE
            )
        
            # Get device firmware
            self.firmware = info_firmware.read_value()

        if alertsvc:
            self.new_alert = next(
                c
                for c in alertsvc.characteristics
                if c.uuid == BTCHAR_NEWALERT
            )
        
        self.battery = -1
        if battsvc:
            battery_level = next(
                c
                for c in battsvc.characteristics
                if c.uuid == BTCHAR_BATTLEVEL
            )
        
            # Get device firmware
            self.battery = int(battery_level.read_value()[0])

        self.services_done()

    def send_notification(self, alert_dict):
        message = alert_dict["message"]
        alert_category = "0"  # simple alert
        alert_number = "0"  # 0-255
        title = alert_dict["sender"]
        msg = (
            str.encode(alert_category)
            + str.encode(alert_number)
            + str.encode("\0")
            + str.encode(title)
            + str.encode("\0")
            + str.encode(message)
        )

        # arr = bytearray(message, "utf-8")
        # self.new_alert_characteristic.write_value(arr)
        self.new_alert.write_value(msg)


class BluetoothDisabled(Exception):
    pass


class NoAdapterFound(Exception):
    pass
