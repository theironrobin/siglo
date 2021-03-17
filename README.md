# siglo
GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

Dependancies
```
sudo pacman -S meson python-pip base-devel bluez bluez-utils
pip3 install gatt
pip3 install dbus-python
```

Build/Install
```
git clone https://github.com/alexr4535/siglo.git
cd siglo
mkdir build
meson build/
cd build
sudo ninja install
```

Make sure Bluetooth Adapter is enabled in Settings->Bluetooth, or:
```
sudo systemctl start bluetooth
```

Icons by svgrepo.com
