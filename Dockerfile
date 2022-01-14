FROM ubuntu:21.04

ENV DEBIAN_FRONTEND="noninteractive" TZ=" America/Los_Angeles"

# xvfb is used to mock out the display for testing and is not required for real builds
RUN apt update && apt install -y \
    libgtk-3-dev python3-pip meson python3-dbus gtk-update-icon-cache desktop-file-utils gettext appstream-util libglib2.0-dev && \
    apt install -y xvfb && \
    rm -rf /var/lib/apt/lists/* && apt clean

RUN pip3 install gatt requests black

COPY . /siglo

WORKDIR /siglo

RUN pwd && ls && mkdir -p ./build && \
    meson --reconfigure ./build/ && \
    cd ./build && ninja install

CMD ["/bin/bash"]

# Once the container is running, you should have all the dependencies you need
# Start system dbus, then kickoff the app. For more details, you can see GTK's setup:
# https://gitlab.gnome.org/GNOME/gtk/-/blob/fb052c8d2546706b49e5adb87bc88ad600f31752/.gitlab-ci.yml#L122
#
# /etc/init.d/dbus start && dbus-run-session xvfb-run -a -s "-screen 0 1024x768x24" siglo
