import gatt

import gi.repository.GLib as glib
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from .bluetooth import InfiniTimeManager, InfiniTimeDevice, NoAdapterFound
from .config import config


class daemon:
    def __init__(self):
        self.conf = config()
        self.manager = InfiniTimeManager()
        self.device = InfiniTimeDevice(manager=self.manager, mac_address=self.conf.get_property("last_paired_device"))
        self.device.connect()

    def scan_for_notifications(self):
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        bus.add_match_string_non_blocking(
            "eavesdrop=true, interface='org.freedesktop.Notifications', member='Notify'"
        )
        bus.add_message_filter(self.notifications)
        mainloop = glib.MainLoop()
        mainloop.run()

    def notifications(self, bus, message):
        alert_dict = {}
        for arg in message.get_args_list():
            if isinstance(arg, dbus.Dictionary):
                if "desktop-entry" in arg.keys() and arg["desktop-entry"] == "sm.puri.Chatty":
                    alert_dict["category"] = "SMS"
                    alert_dict["sender"] = message.get_args_list()[3].split("New message from ")[1]
                    alert_dict["message"] = message.get_args_list()[4]
                else:
                    alert_dict["category"] = message.get_args_list()[0]
                    alert_dict["sender"] = message.get_args_list()[3]
                    alert_dict["message"] = message.get_args_list()[4]
        alert_dict_empty = not alert_dict
        if len(alert_dict) > 0:
            self.device.send_notification(alert_dict)
