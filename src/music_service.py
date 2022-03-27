
import dbus
import platform
from dbus.mainloop.glib import DBusGMainLoop

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class MusicService(metaclass=Singleton):

    UUID_STATUS = '00000002-78fc-48fe-8e23-433b3a1942d0'
    UUID_EVENT = '00000001-78fc-48fe-8e23-433b3a1942d0'
    UUID_ARTIST = '00000003-78fc-48fe-8e23-433b3a1942d0'
    UUID_TRACK = '00000004-78fc-48fe-8e23-433b3a1942d0'
    UUID_ALBUM = '00000005-78fc-48fe-8e23-433b3a1942d0'
    UUID_POSITION = '00000006-78fc-48fe-8e23-433b3a1942d0'
    UUID_TOTAL_LENGTH = '00000007-78fc-48fe-8e23-433b3a1942d0'
    UUID_TRACK_NUMBER = '00000008-78fc-48fe-8e23-433b3a1942d0' #not implemented
    UUID_TRACK_TOTAL = '00000009-78fc-48fe-8e23-433b3a1942d0' #not implemented
    UUID_PLAYBACK_SPEED = '0000000a-78fc-48fe-8e23-433b3a1942d0' #not implemented
    UUID_REPEAT = '0000000b-78fc-48fe-8e23-433b3a1942d0' #not implemented
    UUID_SHUFFLE = '0000000c-78fc-48fe-8e23-433b3a1942d0' #not implemented

    EVENT_OPEN = (0xe0).to_bytes(1, byteorder='big')
    EVENT_PLAY = (0x00).to_bytes(1, byteorder='big')
    EVENT_PAUSE = (0x01).to_bytes(1, byteorder='big')
    EVENT_NEXT = (0x03).to_bytes(1, byteorder='big')
    EVENT_PREV = (0x04).to_bytes(1, byteorder='big')
    EVENT_VOLUP = (0x05).to_bytes(1, byteorder='big')
    EVENT_VOLDOWN = (0x06).to_bytes(1, byteorder='big')

    VOLUME_STEP = 0.1 #10%

    MPRIS_IFACE = 'org.mpris.MediaPlayer2.Player'

    def __init__(self):
        self.btsvc = None

        self.status_chrc = None
        self.event_chrc = None
        self.artist_chrc = None
        self.track_chrc = None
        self.album_chrc = None
        self.position_chrc = None
        self.total_length_chrc = None
        self.track_number_chrc = None
        self.track_total_chrc = None
        self.playback_speed_chrc = None
        self.repeat_chrc = None
        self.shuffle_chrc = None

        self.bus = None
        self.dbus_iface = None

        self.active_player = None
        self.active_player_name = None
        self.player_iface = None
        self.player_prop_iface = None

        self.monitor_bus = None
        self.dbus_monitor_iface = None

    def start_service(self, device, service):

        DBusGMainLoop(set_as_default=True)
        self.monitor_bus = dbus.SessionBus(private=True)
        self.dbus_monitor_iface = dbus.Interface(self.monitor_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus.Monitoring')
        self.dbus_monitor_iface.BecomeMonitor(["interface='org.freedesktop.DBus', member='NameOwnerChanged'"], 0)
        self.monitor_bus.add_message_filter(self.monitor_cb)

        self.btsvc = service

        self.status_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_STATUS)
        self.event_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_EVENT)
        self.artist_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_ARTIST)
        self.track_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_TRACK)
        self.album_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_ALBUM)
        self.position_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_POSITION)
        self.total_length_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_TOTAL_LENGTH)
        self.track_number_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_TRACK_NUMBER)
        self.track_total_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_TRACK_TOTAL)
        self.playback_speed_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_PLAYBACK_SPEED)
        self.repeat_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_REPEAT)
        self.shuffle_chrc = next(c for c in service.characteristics if c.uuid == self.UUID_SHUFFLE)

        self.event_chrc.enable_notifications()

        self.bus = dbus.SessionBus()
        self.dbus_iface = dbus.Interface(self.bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus')

        #if a player is already running, get it
        self.get_player()

    def monitor_cb(self, bus, msg):
        args = msg.get_args_list()

        if self.active_player:
            if self.active_player_name in args:
                #player was closed
                self.active_player = None
                self.player_iface = None
                self.player_prop_iface = None
                self.active_player_name = None

                if not self.get_player():
                    self.player_unavailable()
        else:
            for arg in args:
                if "org.mpris.MediaPlayer2" in arg:
                    self.get_player()
                    break

    def get_player(self):
        if self.active_player:
            return

        for proc in self.dbus_iface.ListNames():
            if "org.mpris.MediaPlayer2" in proc:
                try:
                    self.active_player = self.bus.get_object(proc,"/org/mpris/MediaPlayer2")
                except dbus.DBusException as e:
                    self.dbus_error(e)

                self.active_player_name = proc
                break

        if self.active_player:
            try:
                self.player_iface = dbus.Interface(self.active_player, dbus_interface=self.MPRIS_IFACE)
                self.player_prop_iface = dbus.Interface(self.active_player, dbus_interface='org.freedesktop.DBus.Properties')
                self.player_prop_iface.connect_to_signal("PropertiesChanged", self.active_player_properties_changed)
                self.player_iface.connect_to_signal("Seeked", self.send_position)
            except dbus.DBusException as e:
                self.dbus_error(e)

            self.player_available()
            return True
        else:
            self.player_unavailable()
            return False

    def player_unavailable(self):
        if not self.active_player:
            self.send_metadata(title="<start a player>",
                                artist="Host : " + platform.node(),
                                album="",
                                total_length=0)
            self.send_position(0)
            self.send_status(0)

    def player_available(self):
        #new player could already be playing music or idle in menu
        metadata = self.get_player_propertie('Metadata')
        if 'xesam:title' in metadata:
            self.send_metadata(metadata)
            self.send_position()
            self.send_status()
        else:
            self.send_metadata(title="<select a track>",
                               artist="Player: " + self.active_player_name.rsplit('.', 1)[1],
                               album="",
                               total_length=0)

            self.send_position(0)
            self.send_status(0)

    def active_player_properties_changed(self, iface, changed_prop, invalid):
        if 'Metadata' in changed_prop:
            metadata = changed_prop['Metadata']
            if 'xesam:title' in metadata:
                self.send_metadata(metadata)
                self.send_position()
                self.send_status()
            else: #end of a playlist
                self.send_metadata(title="<select a track>",
                                   artist="Player: " + self.active_player_name.rsplit('.', 1)[1],
                                   album="",
                                   total_length=0)
                self.send_position(0)
                self.send_status(0)
        elif 'PlaybackStatus' in changed_prop:
            self.send_status(changed_prop['PlaybackStatus'])

    def characteristic_value_updated(self, chrc, value):
        if self.active_player:
            if chrc == self.event_chrc:
                if value == self.EVENT_NEXT:
                    self.player_iface.Next()

                elif value == self.EVENT_PREV:
                    self.player_iface.Previous()

                elif value == self.EVENT_PLAY:
                    self.player_iface.Play()

                elif value == self.EVENT_PAUSE:
                    self.player_iface.Pause()

                elif value == self.EVENT_VOLDOWN:
                    curr_volume = self.get_player_propertie('Volume')
                    if curr_volume:
                        self.set_player_propertie('Volume', curr_volume - self.VOLUME_STEP)

                elif value == self.EVENT_VOLUP:
                    curr_volume = self.get_player_propertie('Volume')
                    if curr_volume:
                        self.set_player_propertie('Volume', curr_volume + self.VOLUME_STEP)

                elif value == self.EVENT_OPEN:
                    #the current position is lost when the music applet is closed, therefor restore it
                    self.send_position()
                else:
                    print("unknown event")

    def send_metadata(self, metadata=None , /, title="", artist="", album="", total_length=0):
        if metadata:
            try:
                self.track_chrc.write_value(bytes(metadata['xesam:title'], 'utf-8'))
            except KeyError:
                self.track_chrc.write_value(bytes('', 'utf-8'))

            try:
                self.artist_chrc.write_value(bytes(metadata['xesam:artist'][0], 'utf-8'))
            except KeyError:
                self.artist_chrc.write_value(bytes('', 'utf-8'))

            try:
                self.album_chrc.write_value(bytes(metadata['xesam:album'], 'utf-8'))
            except KeyError:
                self.album_chrc.write_value(bytes('', 'utf-8'))

            try:
                self.total_length_chrc.write_value((metadata['mpris:length']//(1000*1000)).to_bytes(4, byteorder='big'))
            except KeyError:
                self.total_length_chrc.write_value((0).to_bytes(4, byteorder='big'))
        else:
            self.track_chrc.write_value(bytes(title, 'utf-8'))
            self.artist_chrc.write_value(bytes(artist, 'utf-8'))
            self.album_chrc.write_value(bytes(album, 'utf-8'))
            self.total_length_chrc.write_value((total_length//(1000*1000)).to_bytes(4, byteorder='big'))

    def get_player_propertie(self, prop):
        result = None
        try:
            if self.player_prop_iface:
                result = self.player_prop_iface.Get(self.MPRIS_IFACE, prop)
        except dbus.DBusException as e:
           self.dbus_error(e)

        return result

    def set_player_propertie(self, prop, value):
        try:
            self.player_prop_iface.Set(self.MPRIS_IFACE, prop, value)
        except dbus.DBusException as e:
           self.dbus_error(e)

    def send_status(self, status=None):
        if status:
            if status == 'Playing':
                self.status_chrc.write_value([dbus.Byte(1)])
            else:
                self.status_chrc.write_value([dbus.Byte(0)])
        else:
            if self.get_player_propertie('PlaybackStatus') == 'Playing':
                self.status_chrc.write_value([dbus.Byte(1)])
            else:
                self.status_chrc.write_value([dbus.Byte(0)])

    def send_position(self, pos=None):
        if pos:
            self.position_chrc.write_value((pos//(1000*1000)).to_bytes(4, byteorder='big'))
        else:
            position = self.get_player_propertie('Position')
            if position:
                self.position_chrc.write_value((position//(1000*1000)).to_bytes(4, byteorder='big'))
            else:
                self.position_chrc.write_value((0//(1000*1000)).to_bytes(4, byteorder='big'))

    def dbus_error(self, error):
        print(error)
