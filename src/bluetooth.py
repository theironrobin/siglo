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

