# siglo
GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

## Dependancies
### Arch Linux
```
sudo pacman -S meson python-pip base-devel bluez bluez-utils
pip3 install gatt
pip3 install dbus-python
```
### Ubuntu
```
sudo apt install meson python3-dbus gettext appstream-util libglib2.0-dev
pip3 install gatt
```

## Build/Install
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
echo "power on" | sudo bluetoothctl
```

## Donation
If this project helped you, you can give me a cup of coffee :)
<br/><br/>
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/ironrobin)

Icons by svgrepo.com
