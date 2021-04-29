import time
import gatt

import gi.repository.GLib as glib
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from .bluetooth import InfiniTimeManager, NoAdapterFound
from .config import config

def start():
    try:
        print("hello")
        conf = config()
        global manager 
        manager = InfiniTimeManager()
        global mac_address 
        mac_address = conf.get_property("last_paired_device")

        DBusGMainLoop(set_as_default=True)

        bus = dbus.SessionBus()
        bus.add_match_string_non_blocking(
            "eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'"
        )
        bus.add_message_filter(notifications)

        mainloop = glib.MainLoop()
        mainloop.run()
    except gatt.errors.NotReady:
        print("[WARN ] Bluetooth is disabled")
    except NoAdapterFound:
        print("[WARN ] No Bluetooth adapter found")

def notifications(bus, message):
    alert_dict = {}
    for arg in message.get_args_list():
        if isinstance(arg, dbus.Dictionary):
            if arg["desktop-entry"] == "sm.puri.Chatty":
                alert_dict["category"] = "SMS"
                alert_dict["sender"] = message.get_args_list()[3]
                alert_dict["message"] = message.get_args_list()[4]
    alert_dict_empty = not alert_dict
    if not alert_dict_empty:
            device = InfiniTimeNotify(
                manager=manager, mac_address=mac_address
            )
            device.connect()

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

    def __init__(self, mac_address, manager, alert):
        self.alert = alert
        super().__init__(mac_address, manager)

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
        alert_serv = next(
            s for s in self.services if s.uuid == self.UUID_SERVICE_ALERT_NOTIFICATION
        )
        alert_char = next(
            c
            for c in alert_serv.characteristics
            if c.uuid == self.UUID_CHARACTERISTIC_ALERT_NOTIFICATION_NEW_ALERT
        )
        print("goodbye")
        # alert_char.write_value(alert)