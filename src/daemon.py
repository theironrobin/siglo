import gatt

import gi.repository.GLib as glib
import dbus
import dbus.service
import sys
from dbus.mainloop.glib import DBusGMainLoop
from .bluetooth import InfiniTimeManager, InfiniTimeDevice, NoAdapterFound
from .config import config

UID         =  'com.github.alexr4535.siglo.Daemon'
UID_AS_PATH = '/com/github/alexr4535/siglo/Daemon'

def main():
    DBusGMainLoop(set_as_default=True)

    #claim bus name
    try:
        bus_name = dbus.service.BusName(
            UID, bus=dbus.SessionBus(), do_not_queue=True
        )
    except dbus.exceptions.NameExistsException:
        print(f'Service with id {UID} is already running')
        exit(1)

    loop = glib.MainLoop()
    siglo_daemon = daemon(bus_name)
    siglo_daemon.main_loop = loop

    try:
        loop.run()
    except KeyboardInterrupt:
        print('KeyboardInterrupt received')
    except Exception as e:
        print('Unhandled exception: `{}`'.format(str(e)))
    finally:
        loop.quit()

class daemon(dbus.service.Object):
    def __init__(self, bus_name):
        super().__init__(
            bus_name, UID_AS_PATH
        )
        self.conf = config()
        self.main_loop = None
        self.background_permission_granted = False
        self.manager = None

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='d', out_signature=''
    )
    def Scan(self,timeout_sec):
        print("Start scanning")
        if not self.manager:
            # create manager if not present yet
            try:
                self.manager = InfiniTimeManager()
                self.manager.daemon = self
            except (gatt.errors.NotReady, BluetoothDisabled):
                print("Bluetooth is disabled")
                self.Error("scan","no_bluetooth")
            except NoAdapterFound:
                print("No bluetooth adapter found")
                self.Error("scan","no_adapter")
        if not self.manager:
            return

        self.manager.scan_result = False
        try:
            self.manager.scan_for_infinitime(timeout_sec)
            #self.ScanTimeout()
        except (gatt.errors.NotReady, gatt.errors.Failed) as e:
            print(e)

    def destroy_manager(self):
        if self.manager:
            self.manager.stop()
            self.manager = None

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='', out_signature='s'
    )
    def GetConnectedDevice(self):
        try:
            return self.device.mac
        except:
            return ''

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='', out_signature='a{sv}'
    )
    def GetDevices(self):
        try:
            return self.manager.aliases
        except:
            return {}

    @dbus.service.method(
        dbus_interface=UID+".Service",
        in_signature='', out_signature='d'
    )
    def GetPowerLevel(self):
        try:
            return self.device.battery
        except:
            return -1.0

    @dbus.service.method(
        dbus_interface=UID+".Service",
        in_signature='', out_signature='s'
    )
    def GetFirmwareVersion(self):
        try:
            return bytes(self.device.firmware).decode()
        except:
            return "n/a"

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='', out_signature='b'
    )
    def IsConnected(self):
        try:
            return self.device.is_connected
        except:
            return False

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='s', out_signature=''
    )
    def Connect(self, mac_address: str):
        try:
            self.device = InfiniTimeDevice(self.manager, mac_address)
            self.device.connect()
        except:
            self.Error("connect","error while trying to connect")
            raise dbus.exceptions.DBusException("Error connecting")



    @dbus.service.method(
        dbus_interface=UID,
        in_signature='', out_signature=''
    )
    def Quit(self):
        self.destroy_manager()
        self.main_loop.quit()

    @dbus.service.method(
        dbus_interface=UID,
        in_signature='', out_signature=''
    )
    def Disconnect(self):
        try:
            self.device.disconnect()
            self.destroy_manager()
        except Exception as e:
            print(e)

    @dbus.service.signal(
        dbus_interface=UID,
        signature=''
    )
    def ServicesResolved(self):
        pass

    @dbus.service.method(
        dbus_interface=UID+".Permission",
        in_signature='', out_signature=''
    )
    def RequestBackgroundPermission(self):
        if self.background_permission_granted:
            self.BackgroundPermissionGranted(True)
        else:
            bus = dbus.SessionBus()
            portal_obj = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
            background_iface = dbus.Interface(portal_obj, dbus_interface='org.freedesktop.portal.Background')

            obj_path = background_iface.RequestBackground("", dbus.Dictionary({
                                                              "reason":"Pinetime service daemon",
                                                              "autostart":False,
                                                              "dbus-activatable":True, #used on autostart
                                                              "commandline":["siglo", "--daemon"] #used on autostart
                                                                }, signature='sv', variant_level=1))

            request_iface = dbus.Interface(bus.get_object('org.freedesktop.portal.Desktop', obj_path),
                                            dbus_interface='org.freedesktop.portal.Request')
            request_iface.connect_to_signal("Response", self.request_cb)

    @dbus.service.signal(
        dbus_interface=UID+".Permission",
        signature='b'
    )
    def BackgroundPermissionGranted(self, response):
        return response

    def request_cb(self, response, result):
        if response != 0:
            print("Background request denied")
            self.BackgroundPermissionGranted(False)
            self.Quit()

        else:
            self.BackgroundPermissionGranted(True)
            self.background_permission_granted = True

        # else:
        #     if not results['background']:
        #         print("Background request denied")
        #     if not results['autostart']:
        #         print("Autostart request denied")

    @dbus.service.signal(
        dbus_interface=UID,
        signature='ss'
    )
    def Error(self,source, response):
        print("Error from %s: %s" % (source,response))
        return
