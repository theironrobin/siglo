import dbus

BTCHAR_NEWALERT = "00002a46-0000-1000-8000-00805f9b34fb"

class NotificationService():
    def __init__(self,alertsvc):
        self.new_alert = next(
                c
                for c in alertsvc.characteristics
                if c.uuid == BTCHAR_NEWALERT
            )

        self.monitor_bus = dbus.SessionBus(private=True)
        try:
            dbus_monitor_iface = dbus.Interface(self.monitor_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus.Monitoring')
        except dbus.exceptions.DBusException as e:
            print("first" + (e))
            return
        try:
            dbus_monitor_iface.BecomeMonitor(["interface='org.freedesktop.Notifications', member='Notify'"], 0)
        except dbus.exceptions.DBusException as e:
            print("second" + str(e))

        self.monitor_bus.add_message_filter(self.notifications)

    def notifications(self, bus, message):
        alert_dict = {}
        for arg in message.get_args_list():
            if isinstance(arg, dbus.Dictionary):
                if arg["desktop-entry"] == "sm.puri.Chatty":
                    alert_dict["category"] = "SMS"
                    alert_dict["sender"] = message.get_args_list()[3]
                    alert_dict["message"] = message.get_args_list()[4]
        if len(alert_dict) > 0:
            try:
                self.send_notification(alert_dict)
            except :
               print("error")

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

        self.new_alert.write_value(msg)
