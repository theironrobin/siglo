from array import array
from enum import Enum
from time import sleep, time
import gatt
import os
from .util import *
import math
import json
from struct import unpack

class InfiniTimeFS(gatt.Device):
    # Class constants
    UUID_FS_SERVICE = "0000febb-0000-1000-8000-00805f9b34fb"
    UUID_FS_VERSION = "adaf0100-4669-6c65-5472-616e73666572"
    UUID_TRANSFER = "adaf0200-4669-6c65-5472-616e73666572"

    ERR_OK          = 0     # No error
    ERR_IO          = -5    # Error during device operation
    ERR_CORRUPT     = -84   # Corrupted
    ERR_NOENT       = -2    # No directory entry
    ERR_EXIST       = -17   # Entry already exists
    ERR_NOTDIR      = -20   # Entry is not a dir
    ERR_ISDIR       = -21   # Entry is a dir
    ERR_NOTEMPTY    = -39   # Dir is not empty
    ERR_BADF        = -9    # Bad file number
    ERR_FBIG        = -27   # File too large
    ERR_INVAL       = -22   # Invalid parameter
    ERR_NOSPC       = -28   # No space left on device
    ERR_NOMEM       = -12   # No more memory available
    ERR_NOATTR      = -61   # No data/attr available
    ERR_NAMETOOLONG = -36   # File name too long

    INFINITIME_MTU = 256
    PAYLOAD_SIZE = 192

    def __init__(self, mac_address, manager, window, resource_files, manifest, version, verbose):
        self.resource_files = resource_files
        self.resources = {}
        self.manifest = manifest
        self.target_mac = mac_address
        self.window = window
        self.version = version
        self.verbose = verbose
        self.current_step = 0
        self.pkt_receipt_interval = 10
        self.done = False
        self.packet_receipt_size = 0
        self.total_receipt_size = 0
        self.total_file_size = 0
        self.total_files = 0
        self.files_transferred = 0
        self.operation_in_progress = False
        self.caffeinator = Caffeinator()
        self.success = False
        self.device_files = {}
        self.resource_dirs = set()
        self.files_to_delete = set()

        super().__init__(mac_address, manager)

    def connect(self):
        self.successful_connection = True
        super().connect()

    def parse_resource(self, resource):
        filename = resource["filename"]
        _, extent = os.path.splitext(filename)

        print("preparing %s" % filename)

        if extent != ".bin":
            raise Exception("input invalid - can only load .bin files")

        file_path = None
        for resource_file in self.resource_files:
            if self.verbose:
                print("Checking if %s matches %s" % (resource_file, filename))
            if resource_file.endswith(filename):
                file_path = resource_file
        
        if file_path is None:
            raise Exception("File in manifest not found in asset file")
        
        self.resource_files.remove(file_path)
        
        data = array("B", open(file_path, "rb").read())

        size = len(data)
        print("%s - Binary image size: %d" % (filename, size))
        print(
            "%s - Binary CRC32: %d" % (filename, crc32_unsigned(array_to_hex_string(data)))
        )
    
        directory, _ = os.path.split(resource["path"])
        self.resource_dirs.add(directory)

        self.resources[filename] = {
            "path": resource["path"],
            "data": data,
            "size": size,
        }
        self.total_file_size += size
        self.total_files += 1

    def parse_obsolete_file(self, file):
        path = file["path"]

        if file["since"] == self.version:
            # If since version is the one we're updating to, we can delete
            self.files_to_delete.add(path)
            return

        # Else check if since is older than version we're updating to
        since = file["since"].split(".")
        version_parts = self.version.split(".")

        for i in range(2):
            if version_parts[i] > since[i]:
                self.files_to_delete.add(path)
                break
            

    def input_setup(self):
        """Bin: read binfile into bin array"""
        print(
            "preparing "
            + self.version
            + " resources for "
            + self.target_mac
        )

        if self.resources == None or self.manifest == None:
            raise Exception("input invalid")
        
        print ("Reading manifest %s" % self.manifest)
        self.manifest = json.load(open(self.manifest))
        print(json.dumps(self.manifest, indent=2))

        for resource in self.manifest["resources"]:
            self.parse_resource(resource)
        for file in self.manifest["obsolete_files"]:
            self.parse_obsolete_file(file)

    def connect_succeeded(self):
        super().connect_succeeded()
        print("[%s] Connected" % (self.mac_address))

    def connect_failed(self, error):
        super().connect_failed(error)
        self.successful_connection = False
        print("[%s] Connection failed: %s" % (self.mac_address, str(error)))

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        if not self.success:
            self.on_failure()
        print("[%s] Disconnected" % (self.mac_address))

    def characteristic_enable_notifications_succeeded(self, characteristic):
        if self.verbose and characteristic.uuid == self.UUID_TRANSFER:
            print("Notification Enable succeeded for Transfer Characteristic")
        self.list_dir("/")

    def characteristic_write_value_succeeded(self, characteristic):
        if self.verbose and characteristic.uuid == self.UUID_TRANSFER:
            print(
                "Characteristic value was written successfully for Transfer Characteristic"
            )

    def characteristic_write_value_failed(self, characteristic, error):
        print("[WARN ] write value failed", str(error))
        if str(error) == "In Progress":
            print("Retrying last command")
            sleep(0.05)
            self.retry_command()
        else:
            self.operation_in_progress = False
            self.disconnect()

    def characteristic_value_updated(self, characteristic, value):
        try:
            if self.verbose:
                if characteristic.uuid == self.UUID_TRANSFER:
                    print(
                        "Characteristic value was updated for Transfer Characteristic"
                    )
                print("Response:", value.hex())
            command = value[0:1]
            status = int.from_bytes(value[1:2], byteorder="little", signed=True)

            if status < 0:
                self.print_error(status)

            if command == b'\x11':
                self.read_file_response(status, value)
            elif command == b'\x21':
                self.write_file_response(status, value)
            elif command == b'\x31':
                self.delete_file_response(status, value)
            elif command == b'\x41':
                self.make_dir_response(status, value)
            elif command == b'\x51':
                self.list_dir_response(status, value)
            elif command == b'\x61':
                self.move_file_response(status, value)
            else:
                raise Exception("Unknown command in response: %i" % command)
        except Exception as e:
            self.disconnect()
            raise e

    def services_resolved(self):
        super().services_resolved()
        try:
            ble_fs_serv = next(s for s in self.services if s.uuid == self.UUID_FS_SERVICE)
            self.transfer_char = next(
                c for c in ble_fs_serv.characteristics if c.uuid == self.UUID_TRANSFER
            )

            if self.verbose:
                print("[INFO ] Enabling notifications for Transfer Characteristic")
            self.transfer_char.enable_notifications()
        except Exception as e:
            self.disconnect()
            raise e

    def delete_obsolete_files(self):
        if self.files_to_delete:
            file = self.files_to_delete.pop()
            print("Deleting obsolete file: ", file)
            self.delete_file(file)
        else:
            print("All obsolete files deleted")
            self.create_dirs_for_upload()

    def create_dirs_for_upload(self):
        if self.resource_dirs:
            d = self.resource_dirs.pop()
            print("Creating dir on device: ", d)
            self.make_dir(d)
        else:
            print("Directories created")
            self.upload_resources()

    def upload_resources(self):
        print("Upload resources")
        _, resource = self.resources.popitem()
        self.write_file(resource)

    def print_error(self, error):
        if error == self.ERR_IO:
            msg = "I/O error"
        elif error == self.ERR_CORRUPT:
            msg = "Corrupted"
        elif error == self.ERR_NOENT:
            msg = "File or directory not found"
        elif error == self.ERR_EXIST:
            msg = "Entry already exists"
        elif error == self.ERR_NOTDIR:
            msg = "Entry is not a directory"
        elif error == self.ERR_ISDIR:
            msg = "Entry is a directory"
        elif error == self.ERR_NOTEMPTY:
            msg = "Directory is not empty"
        elif error == self.ERR_BADF:
            msg = "Bad file number"
        elif error == self.ERR_FBIG:
            msg = "File too large"
        elif error == self.ERR_INVAL:
            msg = "Invalid parameter"
        elif error == self.ERR_NOSPC:
            msg = "No space left on device"
        elif error == self.ERR_NOMEM:
            msg = "No more memory available"
        elif error == self.ERR_NOATTR:
            msg = "No data/attr available"
        elif error == self.ERR_NAMETOOLONG:
            msg = "Name too long"
        else:
            msg = "Unknown status: %i" % error
        print("Error: %s" % msg)

    def read_file_response(self, status, value):
        if self.verbose:
            print("Read file response received")
        offset = int.from_bytes(value[4:8], byteorder="little")
        file_size = int.from_bytes(value[8:12], byteorder="little")
        packet_size = int.from_bytes(value[12:16], byteorder="little")
        data = value[16:(16 + packet_size)]
        if self.verbose:
            print("offset: %i, file_size: %i, packet_size: %i, data: %s" % (
                offset, file_size, packet_size, data.hex()
            ))
        self.downloading_resource["size"] = file_size
        self.downloading_resource["data"].extend(data)
        self.total_receipt_size += packet_size

    def write_file_response(self, status, value):
        if self.verbose:
            print("Write file response received")
        offset = int.from_bytes(value[4:8], byteorder="little")
        # time = int.from_bytes(value[8:16], "little") # Not used yet by InfiniTime
        size_available = int.from_bytes(value[16:], byteorder="little")
        if self.verbose:
            print("offset: %i, size_available: %i" % (
                offset, size_available
            ))
        if offset == self.uploading_resource["size"]:
            print("Upload of %s complete" % self.uploading_resource["path"])
            self.uploading_resource = None
            self.files_transferred += 1
            self.total_receipt_size += self.packet_receipt_size
            self.packet_receipt_size = 0
            self.update_progress_bar()
            if self.resources:
                self.upload_resources()
            else:
                # Done
                print("All files uploaded successfully")
                self.operation_in_progress = False
                self.success = True
                self.on_success()
                self.disconnect()
                self.caffeinator.decaffeinate()
        else:
            self.total_receipt_size += self.packet_receipt_size
            self.file_receipt_size += self.packet_receipt_size
            print("Transferred %i bytes, %i remaining" % (self.file_receipt_size, self.uploading_resource["size"] - self.file_receipt_size))
            self.update_progress_bar()
            self.write_file_content(offset + self.packet_receipt_size)

    def delete_file_response(self, status, value):
        if self.verbose:
            print("Delete file/dir response received")
        if status < 0:
            if status != self.ERR_NOENT:
                self.operation_in_progress = False
                self.on_failure()
                self.disconnect()
        self.delete_obsolete_files()

    def make_dir_response(self, status, value):
        if self.verbose:
            print("Create directory response received")
        # time = int.from_bytes(value[10:18], "little") # Not used yet by InfiniTime
        if status < 0:
            if status != self.ERR_EXIST:
                self.operation_in_progress = False
                self.on_failure()
                self.disconnect()

        self.create_dirs_for_upload()
            
    def list_dir_response(self, status, value):
        if self.verbose:
            print("List dir response received")
        path_length = int.from_bytes(value[2:4], byteorder="little")
        entry_number = int.from_bytes(value[4:8], byteorder="little")
        total_entries = int.from_bytes(value[8:12], byteorder="little")
        flags = value[12:16]
        is_dir = flags[0] & 1
        time = int.from_bytes(value[16:24], byteorder="little") # Not used yet by InfiniTime
        file_size = int.from_bytes(value[24:28], byteorder="little")
        file_path = str(value[28:(28 + path_length)], encoding="utf-8")
        if self.verbose:
            print("entry: %i, total: %i, is_dir: %s, file_size: %i, path: %s" % (
                entry_number, total_entries, is_dir, file_size, file_path
            ))
        if file_path and file_path != "." and file_path != "..":
            # Store local copy of dir structure from device
            dirpath, file = os.path.split(file_path)
            current_dir = self.device_files
            if dirpath:
                dirs = dirpath.split("/")
                for d in dirs:
                    if not d in current_dir:
                        self.device_files[d] = {}
                    current_dir = current_dir[d]
            if not file in current_dir:
                if is_dir:
                    current_dir[file] = {}
                else:
                    current_dir[file] = file_size
        
        if entry_number == total_entries:
            # All file listings read
            self.operation_in_progress = False
            print("Device fs: ", self.device_files)
            self.caffeinator.decaffeinate()
            # Filter out resource dirs that already exist - just assuming for now that dirs aren't nested
            self.resource_dirs = {d for d in self.resource_dirs if d[1:] not in self.device_files}
            self.delete_obsolete_files()

    def move_file_response(self, status, value):
        if self.verbose:
            print("Move file/dir response received")

    def read_file(self, path, offset = 0):
        self.downloading_resource = {
            "path": path,
            "data": None,
            "size": None,
        }
        try:
            self.operation_in_progress = True
            utf8_path = path.encode()
            packet = bytearray.fromhex("10 00")
            packet.extend(uint16_to_bytes_le(len(path)))
            packet.extend(uint32_to_bytes_le(offset))
            packet.extend(uint32_to_bytes_le(self.PAYLOAD_SIZE))
            packet.extend(utf8_path)

            if self.verbose:
                print("Read file header command: %s" % packet.hex())
            self.caffeinator.caffeinate()
            self.total_receipt_size = 0
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e
    
    def read_file_content(self, offset):
        try:
            data_len = min(self.downloading_resource["size"] - offset, self.PAYLOAD_SIZE)
            self.packet_receipt_size = data_len
            packet = bytearray.fromhex("12 01 00 00")
            packet.extend(uint32_to_bytes_le(offset))
            packet.extend(uint32_to_bytes_le(data_len))

            if self.verbose:
                print("Write file data command: %s" % packet.hex())
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e

    def write_file(self, resource, offset = 0):
        self.uploading_resource = resource
        try:
            utf8_path = resource["path"].encode()
            packet = bytearray.fromhex("20 00")
            packet.extend(uint16_to_bytes_le(len(utf8_path)))
            packet.extend(uint32_to_bytes_le(offset))
            packet.extend(uint64_to_bytes_le(int(time())))
            packet.extend(uint32_to_bytes_le(resource["size"]))
            packet.extend(utf8_path)

            if self.verbose:
                print("Write file header command: %s" % packet.hex())
            self.caffeinator.caffeinate()
            self.file_receipt_size = 0
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e
    
    def write_file_content(self, offset):
        try:
            data_len = min(len(self.uploading_resource["data"]) - offset, self.PAYLOAD_SIZE)
            data = self.uploading_resource["data"][offset:(offset + data_len)]
            packet = bytearray.fromhex("22 01 00 00")
            packet.extend(uint32_to_bytes_le(offset))
            packet.extend(uint32_to_bytes_le(data_len))
            packet.extend(data)

            self.retry_command = lambda: self.write_file_content(offset)

            if self.verbose:
                print("Write file data command: %s" % packet.hex())
                print("  offset: %i, data size: %i, length: %i" % (offset, data_len, len(data)))
                print("  data: %s" % str(data))
            self.packet_receipt_size = data_len
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e
        
    def delete_file(self, path):
        try:
            utf8_path = path.encode()
            packet = bytearray.fromhex("30 00")
            packet.extend(uint16_to_bytes_le(len(utf8_path)))
            packet.extend(utf8_path)

            if self.verbose:
                print("Delete file/dir command: %s" % packet.hex())
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e

    def make_dir(self, path):
        try:
            utf8_path = path.encode()
            packet = bytearray.fromhex("40 00")
            packet.extend(uint16_to_bytes_le(len(utf8_path)))
            packet.extend(bytearray.fromhex("00 00 00 00"))
            packet.extend(uint64_to_bytes_le(int(time())))
            packet.extend(utf8_path)

            if self.verbose:
                print("Make dir command: %s" % packet.hex())
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e

    def list_dir(self, path):
        try:
            utf8_path = path.encode()
            packet = bytearray.fromhex("50 00")
            packet.extend(uint16_to_bytes_le(len(utf8_path)))
            packet.extend(utf8_path)

            if self.verbose:
                print("List dir command: %s" % packet.hex())
            self.caffeinator.caffeinate()
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e
        
    def move_file(self, old_path, new_path):
        try:
            utf8_old_path = old_path.encode()
            utf8_new_path = new_path.encode()
            packet = bytearray.fromhex("60 00")
            packet.extend(uint16_to_bytes_le(len(utf8_old_path)))
            packet.extend(uint16_to_bytes_le(len(utf8_new_path)))
            packet.extend(utf8_old_path)
            packet.extend(b'\00')
            packet.extend(utf8_new_path)

            if self.verbose:
                print("Move file/dir command: %s" % packet.hex())
            self.transfer_char.write_value(packet)
        except Exception as e:
            self.disconnect()
            raise e
    
    def update_progress_bar(self):
        self.window.update_progress_bar(self.get_prog_text(), self.total_receipt_size / self.total_file_size)

    def get_prog_text(self):
        return "%i / %i bytes received (%i of %i files complete)" % (
            self.total_receipt_size,
            self.total_file_size,
            self.files_transferred,
            self.total_files)

class Caffeinator():
    def __init__(self):
        try:
            from gi.repository import Gio
            self.gio = Gio

            self.gnome_session = self.safe_lookup(
                "org.gnome.desktop.session",
                "GNOME session not found, you're on your own for idle timeouts"
            )
            if self.gnome_session:
                self.idle_delay = self.gnome_session.get_uint("idle-delay")

            self.gnome_power = self.safe_lookup(
                "org.gnome.settings-daemon.plugins.power",
                "GNOME power settings not found, you're on your own for system sleep"
            )
            if self.gnome_power:
                self.sleep_inactive_battery_timeout = self.gnome_power.get_int("sleep-inactive-battery-timeout")
                self.sleep_inactive_ac_timeout = self.gnome_power.get_int("sleep-inactive-ac-timeout")
                self.idle_dim = self.gnome_power.get_boolean("idle-dim")
        except ImportError:
            print("[INFO ] GIO not found, disabling caffeine")
        except AttributeError:
            print("[INFO ] Unable to load GIO schemas, disabling caffeine")

    # Look up a Gio Settings schema without crashing if it doesn't exist
    def safe_lookup(self, path, failmsg=None):
        try:
            exists = self.gio.SettingsSchema.lookup(path)
        except AttributeError:
            # SettingsSchema is new, if it doesn't exist
            # then fall back to legacy schema lookup
            exists = (path in self.gio.Settings.list_schemas())

        if exists:
            return self.gio.Settings.new(path)
        else:
            if failmsg:
                print("[INFO ] {}".format(failmsg))
            return None

    def caffeinate(self):
        if self.gnome_session:
            print("[INFO ] Disabling GNOME idle timeout")
            self.gnome_session.set_uint("idle-delay", 0)
        if self.gnome_power:
            print("[INFO ] Disabling GNOME inactivity sleeping")
            self.gnome_power.set_int("sleep-inactive-battery-timeout", 0)
            self.gnome_power.set_int("sleep-inactive-ac-timeout", 0)
            self.gnome_power.set_boolean("idle-dim", False)

    def decaffeinate(self):
        if self.gnome_session:
            print("[INFO ] Restoring GNOME idle timeout")
            self.gnome_session.set_uint("idle-delay", self.idle_delay)
        if self.gnome_power:
            print("[INFO ] Restoring GNOME inactivity sleeping")
            self.gnome_power.set_int("sleep-inactive-battery-timeout", self.sleep_inactive_battery_timeout)
            self.gnome_power.set_int("sleep-inactive-ac-timeout", self.sleep_inactive_ac_timeout)
            self.gnome_power.set_boolean("idle-dim", self.idle_dim)
