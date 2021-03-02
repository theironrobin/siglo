# siglo
GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

Dependancies
```
sudo pacman -S meson python-pip base-devel
pip3 install gatt
pip3 install dbus-python
```

Build
```
git clone https://github.com/alexr4535/siglo.git
cd siglo
mkdir build
meson build/
cd build
sudo ninja install
```

Make sure Bluetooth Adapter is enabled before running
e.g.,
```
echo "power on" | sudo bluetoothctl
```

Icons by svgrepo.com
