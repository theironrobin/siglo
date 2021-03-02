import gatt
import dbus
import time
import datetime
from gi.repository import GObject

def get_current_time():
    now = datetime.datetime.now()
    year_strip_0x = hex(now.year)[2:]
    lsb_raw = year_strip_0x[1:]
    if (len(lsb_raw) <= 1):
        hex_year_a = "0" + lsb_raw
    else:
        hex_year_a = lsb_raw
    split_by_lsb_raw = year_strip_0x.split(lsb_raw)
    msb_raw = split_by_lsb_raw[0]
    if (len(msb_raw) <= 1):
        hex_year_b = "0" + msb_raw
    else:
        hex_year_b = msb_raw

    month_strip_0x = hex(now.month)[2:]
    if (len(month_strip_0x) <=1 ):
        hex_month = "0" + month_strip_0x
    else:
        hex_month = month_strip_0x

    day_strip_0x = hex(now.day)[2:]
    if (len(day_strip_0x) <= 1):
        hex_day = "0" + day_strip_0x
    else:
        hex_day = day_strip_0x

    hour_strip_0x = hex(now.hour)[2:]
    if (len(hour_strip_0x) <= 1):
        hex_hour = "0" + hour_strip_0x
    else:
        hex_hour = hour_strip_0x

    minute_strip_0x = hex(now.minute)[2:]
    if (len(minute_strip_0x) <= 1):
        hex_minute = "0" + minute_strip_0x
    else:
        hex_minute = minute_strip_0x

    second_strip_0x = hex(now.second)[2:]
    if (len(second_strip_0x) <= 1):
        hex_second = "0" + second_strip_0x
    else:
        hex_second = second_strip_0x

    weekday_strip_0x = hex(now.weekday() + 1)[2:]
    if (len(weekday_strip_0x) <= 1):
        hex_weekday = "0" + weekday_strip_0x
    else:
        hex_weekday = weekday_strip_0x

    hexasecond = hex(int((now.microsecond * 256) / 1000000))
    hexasecond_strip_0x = hexasecond[2:]
    if (len(hexasecond_strip_0x) <= 1):
        hex_fractions = "0" + hexasecond_strip_0x
    else:
        hex_fractions = hexasecond_strip_0x
    hex_answer = hex_year_a + " " + hex_year_b + " " + hex_month + " " + hex_day + " " + hex_hour + " " + hex_minute + " " + hex_second + " " + hex_weekday + " " + hex_fractions
    print(hex_answer)
    return bytearray.fromhex(hex_answer)

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

