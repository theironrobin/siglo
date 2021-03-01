import gatt
import dbus
import time

#class AnyDeviceManager(gatt.DeviceManager):
#    def device_discovered(self, device):
#        print("Discovered [%s] %s" % (device.mac_address, device.alias()))

class InfiniTimeManager(gatt.DeviceManager):
    def __init__(self, adapter_name):
        self.connected = False
        super().__init__(adapter_name)

    def device_discovered(self, device):
        if device.alias() == "InfiniTime" and device.is_connected():
            self.connected = True
        else:
            print("No InfiniTime Found")
            time.sleep(1)
    
