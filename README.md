# siglo
GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

## Dependencies
### Arch Linux
```
sudo pacman -S --needed meson python-pip base-devel bluez bluez-utils dbus-python
pip3 install gatt pyxdg
```
### Fedora
```
sudo dnf install meson glib2-devel
pip3 install gatt
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

## Building and installing Flatpak app

### Building and installing on target architecture

```
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk//3.38 org.gnome.Platform//3.38

flatpak-builder --repo=repo --force-clean build-dir/ org.gnome.siglo.json
flatpak build-bundle ./repo/ siglo.flatpak org.gnome.siglo
flatpak install --user ./siglo.flatpak
```

### Cross-compiling for PinePhone

Example cross-compiling for PinePhone on an `x86_64` Fedora machine:

```
sudo dnf install qemu-system-arm qemu-user-static
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk/aarch64/3.38 org.gnome.Platform/aarch64/3.38

flatpak-builder --arch=aarch64 --repo=repo --force-clean build-dir org.gnome.siglo.json
flatpak build-bundle --arch=aarch64 ./repo/ siglo.flatpak org.gnome.siglo
```

Transfer the `siglo.flatpak` file on the PinePhone and install it with the following command:

```
sudo flatpak install ./siglo.flatpak
```

##
If this project helped you, you can buy me a cup of coffee :)
<br/><br/>
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/ironrobin)
<br/><br/>
DOGE address: DLDNfkXoJeueb2GRx4scnmRc12SX1H22VW

Icons by svgrepo.com
