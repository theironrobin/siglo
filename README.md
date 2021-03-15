# siglo
GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

Dependancies
```
sudo pacman -S meson python-pip base-devel
pip3 install gatt
pip3 install dbus-python
pip3 install bleson
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
Give python3 necessary permissions to access the Bluetooth LE adapter
```
sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f `which python3`)
```

Make sure Bluetooth Adapter is enabled in Settings->Bluetooth 
or you can do this if you have bluez-utils:
```
echo "power on" | sudo bluetoothctl
```

Icons by svgrepo.com
