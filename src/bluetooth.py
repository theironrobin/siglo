from os import sync
import gatt
import datetime
import struct
from gi.repository import GObject, Gio
from .config import config


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
    """ https://stackoverflow.com/a/49017827 """
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
        self.alias = None
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
        if self.conf.get_property("paired"):
            self.device_set.add(self.conf.get_property("last_paired_device"))
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
            self.alias = device.alias()
            if self.conf.get_property("mode") == "singleton":
                self.mac_address = device.mac_address
                self.stop()
            if self.conf.get_property("mode") == "multi":
                self.device_set.add(device.mac_address)

    def scan_for_infinitime(self):
        self.start_discovery()
        self.set_timeout(4 * 1000)
        self.run()


class InfiniTimeDevice(gatt.Device):
    def __init__(self, mac_address, manager):
        self.conf = config()
        super().__init__(mac_address, manager)

    def connect(self, sync_time):
        self.sync_time = sync_time
        self.successful_connection = True
        super().connect()

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

    def characteristic_write_value_succeeded(self, characteristic):
        if not self.conf.get_property("paired"):
            self.disconnect()

    def services_resolved(self):
        super().services_resolved()
        self.serv = next(
            s for s in self.services if s.uuid == "00001805-0000-1000-8000-00805f9b34fb"
        )
        self.char = next(
            c
            for c in self.serv.characteristics
            if c.uuid == "00002a2b-0000-1000-8000-00805f9b34fb"
        )
        if self.sync_time:
            self.char.write_value(get_current_time())



class BluetoothDisabled(Exception):
    pass


class NoAdapterFound(Exception):
    pass