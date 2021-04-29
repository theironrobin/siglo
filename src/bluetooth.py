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
        manager = dbus.Interface(bus.get_object('org.bluez', '/'),
                'org.freedesktop.DBus.ObjectManager')
    except dbus.exceptions.DBusException:
        raise BluetoothDisabled

    for path, ifaces in manager.GetManagedObjects().items():
        if ifaces.get('org.bluez.Adapter1') is None:
            continue
        return path.split('/')[-1]
    raise NoAdapterFound


class InfiniTimeManager(gatt.DeviceManager):
    def __init__(self):
        self.conf = config()
        self.device_set = set()
        self.adapter_name = get_default_adapter()
        self.alias = None
        self.scan_result = False
        self.mac_address = None
        super().__init__(self.adapter_name)

    def get_scan_result(self):
        return self.scan_result

    def set_mac_address(self, mac_address):
        self.mac_address = mac_address

    def get_mac_address(self):
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
    def connect(self):
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
        self.disconnect()

    def services_resolved(self):
        super().services_resolved()
        serv = next(
            s for s in self.services if s.uuid == "00001805-0000-1000-8000-00805f9b34fb"
        )
        char = next(
            c
            for c in serv.characteristics
            if c.uuid == "00002a2b-0000-1000-8000-00805f9b34fb"
        )

        char.write_value(get_current_time())

class InfiniTimeNotify(gatt.Device):
    # Class constants
    UUID_SERVICE_ALERT_NOTIFICATION = "00001811-0000-1000-8000-00805f9b34fb"
    UUID_CHARACTERISTIC_ALERT_NOTIFICATION_NEW_ALERT = (
        "00002a46-0000-1000-8000-00805f9b34fb"
    )
    UUID_CHARACTERISTIC_ALERT_NOTIFICATION_CONTROL = (
        "00002a44-0000-1000-8000-00805f9b34fb"
    )
    UUID_CHARACTERISTIC_ALERT_NOTIFICATION_EVENT = (
        "00020001-78fc-48fe-8e23-433b3a1942d0"
    )

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        print("[%s] Disconnected" % (self.mac_address))

    def services_resolved(self):
        super().services_resolved()
        self.alert_serv = next(
            s for s in self.services if s.uuid == self.UUID_SERVICE_ALERT_NOTIFICATION
        )
        self.alert_char = next(
            c
            for c in self.alert_serv.characteristics
            if c.uuid == self.UUID_CHARACTERISTIC_ALERT_NOTIFICATION_NEW_ALERT
        )
        print("Ready to send notifications.")
        # alert_char.write_value(alert)


class BluetoothDisabled(Exception):
    pass

class NoAdapterFound(Exception):
    pass