# siglo

GTK app to sync InfiniTime watch with PinePhone

'siglo' means century in Spanish

## Requirements
Gtk >= 3.30

## Download and Install
[Download the latest stable version from Flathub](https://flathub.org/apps/details/com.github.alexr4535.siglo) (Warning: SMS Notifications currently broken in flatpak https://github.com/alexr4535/siglo/issues/80).

### Alpine
Works for Alpine and other Alpine-based distribution, such as [postmarketOS](https://postmarketos.org/).

```sh
sudo apk add gettext glib-dev meson py3-dbus py3-pip python3 
pip3 install gatt pyxdg
```

### Arch Linux

```sh
sudo pacman -S --needed meson python-pip base-devel bluez bluez-utils dbus-python python-gobject
pip3 install gatt pyxdg
```

### Fedora

```
sudo dnf install meson glib2-devel
pip3 install gatt
```

### Ubuntu

```sh
sudo apt install libgtk-3-dev python3-pip meson python3-dbus gtk-update-icon-cache desktop-file-utils gettext appstream-util libglib2.0-dev
pip3 install gatt pyxdg requests black
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

### Mocked Testing with Docker

While you won't get bluetooth connectivity, you can get some high-level vetting in a container, which
will open the way forward to better CI testing on GitHub.

The [`Dockerfile`](Dockerfile) contains all required dependencies, in addition to
[`xvfb`](https://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml) which allows us to make sure
the app can execute.

```sh
sudo docker build . --tag siglo; and sudo docker run --name siglo --volume (pwd):/siglo --rm -it siglo:latest
```

Once the container is running, you can launch the app:

```sh
/etc/init.d/dbus start && dbus-run-session xvfb-run -a -s "-screen 0 1024x768x24" siglo
```

## Building and installing Flatpak app

### Building and installing on target architecture

```sh
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk//40 org.gnome.Platform//40

flatpak-builder --user --install --repo=repo --force-clean build-dir/ com.github.alexr4535.siglo.json
```

### Cross-compiling for PinePhone

Example cross-compiling for PinePhone on an `x86_64` Fedora machine:

```sh
sudo dnf install qemu-system-arm qemu-user-static
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.gnome.Sdk/aarch64/40 org.gnome.Platform/aarch64/40

flatpak-builder --arch=aarch64 --repo=repo --force-clean build-dir com.github.alexr4535.siglo.json
flatpak build-bundle --arch=aarch64 ./repo/ siglo.flatpak com.github.alexr4535.siglo
```

Transfer the `siglo.flatpak` file on the PinePhone and install it with the following command:

```sh
sudo flatpak install ./siglo.flatpak
```

##

If this project helped you, you can buy me a cup of coffee :)
<br/><br/>
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/ironrobin)
<br/><br/>
DOGE address: DLDNfkXoJeueb2GRx4scnmRc12SX1H22VW

Icons by svgrepo.com
