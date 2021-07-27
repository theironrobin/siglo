
import dbus
from dbus.mainloop.glib import DBusGMainLoop

UUID_STATUS = '00000002-78fc-48fe-8e23-433b3a1942d0'
UUID_EVENT = '00000001-78fc-48fe-8e23-433b3a1942d0'
UUID_ARTIST = '00000003-78fc-48fe-8e23-433b3a1942d0'
UUID_TRACK = '00000004-78fc-48fe-8e23-433b3a1942d0'
UUID_ALBUM = '00000005-78fc-48fe-8e23-433b3a1942d0'
UUID_POSITION = '00000006-78fc-48fe-8e23-433b3a1942d0'
UUID_TOTAL_LENGTH = '00000007-78fc-48fe-8e23-433b3a1942d0'
UUID_TRACK_NUMBER = '00000008-78fc-48fe-8e23-433b3a1942d0'
UUID_TRACK_TOTAL = '00000009-78fc-48fe-8e23-433b3a1942d0'
UUID_PLAYBACK_SPEED = '0000000a-78fc-48fe-8e23-433b3a1942d0'
UUID_REPEAT = '0000000b-78fc-48fe-8e23-433b3a1942d0'
UUID_SHUFFLE = '0000000c-78fc-48fe-8e23-433b3a1942d0'

EVENT_OPEN = (0xe0).to_bytes(1, byteorder='big')
EVENT_PLAY = (0x00).to_bytes(1, byteorder='big')
EVENT_PAUSE = (0x01).to_bytes(1, byteorder='big')
EVENT_NEXT = (0x03).to_bytes(1, byteorder='big')
EVENT_PREV = (0x04).to_bytes(1, byteorder='big')
EVENT_VOLUP = (0x05).to_bytes(1, byteorder='big')
EVENT_VOLDOWN = (0x06).to_bytes(1, byteorder='big')

VOLUME_STEP = 0.1 #10%

btsvc = None

status_chrc = None
event_chrc = None
artist_chrc = None
track_chrc = None
album_chrc = None
position_chrc = None
total_length_chrc = None
track_number_chrc = None
track_total_chrc = None
playback_speed_chrc = None
repeat_chrc = None
shuffle_chrc = None

bus = None
dbus_iface = None

active_player = None
active_player_name = None
player_iface = None
player_prop_iface = None

monitor_bus = None
dbus_monitor_iface = None

def msg_cb(bus, msg):
    global active_player
    global player_iface
    global player_prop_iface
    global active_player_name

    args = msg.get_args_list()

    if active_player:
        if active_player_name in args:
            active_player = None
            player_iface = None
            player_prop_iface = None
            active_player_name = None

            player_unavailable()
    else:
        for arg in args:
            if "org.mpris.MediaPlayer2" in arg:
                get_player()

def player_unavailable():
    if not active_player:
        track_chrc.write_value(bytes('Start media player', 'utf-8'))
        artist_chrc.write_value(bytes('Host device', 'utf-8'))
        album_chrc.write_value(bytes('', 'utf-8'))
        status_chrc.write_value([dbus.Byte(0)])

def player_available():
    global active_player_name

    #player could already be playing music or idle in menu
    metadata = player_prop_iface.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
    if 'xesam:title' in metadata:
        track_chrc.write_value(bytes(metadata['xesam:title'], 'utf-8'))
        artist_chrc.write_value(bytes(metadata['xesam:artist'][0], 'utf-8'))
        album_chrc.write_value(bytes(metadata['xesam:album'], 'utf-8'))

        if player_prop_iface.Get('org.mpris.MediaPlayer2.Player', 'PlaybackStatus') == 'Playing':
            status_chrc.write_value([dbus.Byte(1)])
        else:
            status_chrc.write_value([dbus.Byte(0)])
    else:
        track_chrc.write_value(bytes('-', 'utf-8'))
        artist_chrc.write_value(bytes("player: " + active_player_name.rsplit('.', 1)[1], 'utf-8'))
        album_chrc.write_value(bytes('', 'utf-8'))
        status_chrc.write_value([dbus.Byte(0)])

def get_player():
    global active_player
    global player_iface
    global player_prop_iface
    global active_player_name

    if active_player:
        return

    for proc in dbus_iface.ListNames():
        if "org.mpris.MediaPlayer2" in proc:
            active_player = bus.get_object(proc,"/org/mpris/MediaPlayer2")
            active_player_name = proc
    if active_player:
        player_iface = dbus.Interface(active_player, dbus_interface='org.mpris.MediaPlayer2.Player')
        player_prop_iface = dbus.Interface(active_player, dbus_interface='org.freedesktop.DBus.Properties')
        player_prop_iface.connect_to_signal("PropertiesChanged", active_player_properties_changed_cb)
        player_available()
    else:
        player_unavailable()

def start_service( device, service):

    global monitor_bus
    global dbus_monitor_iface
    DBusGMainLoop(set_as_default=True)
    monitor_bus = dbus.SessionBus(private=True)
    dbus_monitor_iface = dbus.Interface(monitor_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus.Monitoring')
    dbus_monitor_iface.BecomeMonitor(["interface='org.freedesktop.DBus', member='NameOwnerChanged'"], 0)
    monitor_bus.add_message_filter(msg_cb)

    btsvc = service

    global status_chrc
    global event_chrc
    global artist_chrc
    global track_chrc
    global album_chrc
    global position_chrc
    global total_length_chrc
    global track_number_chrc
    global track_total_chrc
    global playback_speed_chrc
    global repeat_chrc
    global shuffle_chrc
    status_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_STATUS)
    event_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_EVENT)
    artist_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_ARTIST)
    track_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_TRACK)
    album_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_ALBUM)
    position_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_POSITION)
    total_length_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_TOTAL_LENGTH)
    track_number_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_TRACK_NUMBER)
    track_total_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_TRACK_TOTAL)
    playback_speed_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_PLAYBACK_SPEED)
    repeat_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_REPEAT)
    shuffle_chrc = next(c for c in btsvc.characteristics if c.uuid == UUID_SHUFFLE)

    event_chrc.enable_notifications()

    global bus
    bus = dbus.SessionBus()

    global dbus_iface
    dbus_iface = dbus.Interface(bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus'), dbus_interface='org.freedesktop.DBus')

    get_player()

def active_player_properties_changed_cb( iface, changed_prop, invalid):
    if 'Metadata' in changed_prop:
        metadata = changed_prop['Metadata']
        track_chrc.write_value(bytes(metadata['xesam:title'], 'utf-8'))
        artist_chrc.write_value(bytes(metadata['xesam:artist'][0], 'utf-8'))
        album_chrc.write_value(bytes(metadata['xesam:album'], 'utf-8'))
        #write_value(music_total_length_chrc[0], bytes(metadata['mpris:length']))
    elif 'PlaybackStatus' in changed_prop:
        if changed_prop['PlaybackStatus'] == 'Playing':
            status_chrc.write_value([dbus.Byte(1)])
        else:
            status_chrc.write_value([dbus.Byte(0)])

def characteristic_value_updated( chrc, value):
    global player_iface
    global player_prop_iface
    global active_player

    if chrc == event_chrc:
        if value == EVENT_NEXT:
            player_iface.Next()

        elif value == EVENT_PREV:
            player_iface.Previous()

        elif value == EVENT_PLAY:
            player_iface.Play()

        elif value == EVENT_PAUSE:
            player_iface.Pause()

        elif value == EVENT_VOLDOWN:
            curr_volume = player_prop_iface.Get('org.mpris.MediaPlayer2.Player', 'Volume')
            player_prop_iface.Set('org.mpris.MediaPlayer2.Player', 'Volume', curr_volume - VOLUME_STEP)

        elif value == EVENT_VOLUP:
            curr_volume = player_prop_iface.Get('org.mpris.MediaPlayer2.Player', 'Volume')
            player_prop_iface.Set('org.mpris.MediaPlayer2.Player', 'Volume', curr_volume + VOLUME_STEP)

        elif value == EVENT_OPEN:
            pass
        else:
            print("unknown event")
