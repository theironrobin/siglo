import dbus
from dbus.mainloop.glib import DBusGMainLoop

class Singleton(type):
    __instances__ = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances__:
            cls.__instances__[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instances__[cls]

class NotificationService(metaclass=Singleton):

    def __init__(self):
        self.btsvc = None
        self.monitor_bus = None
        self.device = None

    def start_service(self, device, service):

        DBusGMainLoop(set_as_default=True)
        self.monitor_bus = dbus.SessionBus(private=True)
        try:
            self.dbus_monitor_iface = dbus.Interface(self.monitor_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus.Monitoring')
            self.dbus_monitor_iface.BecomeMonitor(["interface='org.freedesktop.Notifications', member='Notify'"], 0)
        except dbus.exceptions.DBusException as e:
            print(e)
            return
        self.monitor_bus.add_message_filter(self.notifications)
        self.device = device


    def notifications(self, bus, message):
        alert_dict = {}
        for arg in message.get_args_list():
            if isinstance(arg, dbus.Dictionary):
                if "desktop-entry" in arg.keys() and arg["desktop-entry"] == "sm.puri.Chatty":
                    alert_dict["category"] = "SMS"
                    try:
                        alert_dict["sender"] = message.get_args_list()[3].split("New message from ")[1]
                        alert_dict["message"] = message.get_args_list()[4]
                    except IndexError:
                        continue
                else:
                    try:
                        alert_dict["category"] = message.get_args_list()[0]
                        alert_dict["sender"] = message.get_args_list()[3]
                        alert_dict["message"] = message.get_args_list()[4]
                    except IndexError:
                        continue
        if len(alert_dict) > 0:
            self.device.send_notification(alert_dict)
