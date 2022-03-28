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

def portal_cb(response, results):
    if response != 0:
        print("Background request cancelled")
        sys.exit(512)
    else:
        if not results['background']:
            print("Background request denied")
            sys.exit(513)
        #if not results['autostart']:
        #    print("Autostart request denied")

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

    #request to run in the background
    bus = dbus.SessionBus()
    portal_obj = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
    background_iface = dbus.Interface(portal_obj, dbus_interface='org.freedesktop.portal.Background')
    obj_path = background_iface.RequestBackground("", dbus.Dictionary({
                                                      "reason":"Pinetime service daemon",
                                                      "autostart":False,
                                                      "dbus-activatable":True,
                                                      "commandline":["siglo", "--daemon"]
                                                        }, signature='sv', variant_level=1))
    request_iface = dbus.Interface(bus.get_object('org.freedesktop.portal.Desktop', obj_path),
                                    dbus_interface='org.freedesktop.portal.Request')
    request_iface.connect_to_signal("Response", portal_cb)

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
        try:
            self.manager = InfiniTimeManager()
            self.manager.daemon = self
        except (gatt.errors.NotReady, BluetoothDisabled):
            print("Bluetooth is disabled")
        except NoAdapterFound:
            print("No bluetooth adapter found")

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
                self.ScanResponse("Bluetooth is disabled")
            except NoAdapterFound:
                print("No bluetooth adapter found")
                self.ScanResponse("No bluetooth adapter found")
        if not self.manager:
            self.ScanResponse("Can't create mananger")
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
        #self.manager.run()
        self.device = InfiniTimeDevice(self.manager, mac_address)
        self.device.connect()

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
            #self.manager.stop()
            self.device.disconnect()
        except Exception as e:
            print(e)

    @dbus.service.signal(
        dbus_interface=UID,
        signature=''
    )
    def ServicesResolved(self):
        pass

