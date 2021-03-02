import gatt
import dbus
import time
from gi.repository import GObject

class InfiniTimeManager(gatt.DeviceManager):
    def __init__(self, adapter_name):
        self.scan_result = False
        self.mac_address = None
        super().__init__(adapter_name)

    def get_scan_result(self):
        return self.scan_result

    def get_mac_address(self):
        return self.mac_address

    def set_timeout(self, timeout):
        GObject.timeout_add(timeout, self.stop)

    def device_discovered(self, device):
        if device.alias() == "InfiniTime":
            self.scan_result = True
            self.mac_address = device.mac_address
            self.stop()

    def scan_for_infinitime(self):
        self.start_discovery()
        self.set_timeout(5 * 1000)
        self.run()

class InfiniTimeDevice(gatt.Device):
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

        print("[%s] Resolved services" % (self.mac_address))
        for service in self.services:
            print("[%s]  Service [%s]" % (self.mac_address, service.uuid))
            for characteristic in service.characteristics:
                if characteristic.uuid == "00002a2b-0000-1000-8000-00805f9b34fb":
                    print("Current Time")
                    value = get_current_time()
                    characteristic.write_value(value)
                print("[%s]    Characteristic [%s]" % (self.mac_address, characteristic.uuid))

