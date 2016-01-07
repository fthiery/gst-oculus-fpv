# gst-oculus-fpv

NB: this is work in progress

This software uses gstreamer and OpenGL to to produce side-by-side video from a single video input (e.g. FPV quadcopters) for display on an OculusRift device. It also supports headtracking on PC, but currently not on raspberrypi. 

![screenshot](https://raw.githubusercontent.com/fthiery/gst-oculus-fpv/master/screenshot.jpg)

## Compiling glimagesink for rpi (Arch only)

Note that glimagesink needs to have been compiled for GLES/EGL/dispmanx for hardware acceleration to be enabled. See the following configure flags:

```
./configure CFLAGS=”-I/opt/vc/include -I /opt/vc/include/interface/vcos/pthreads -I /opt/vc/include/interface/vmcs_host/linux/” LDFLAGS=”-L/opt/vc/lib” –disable-gtk-doc –disable-opengl –enable-gles2 –enable-egl –disable-glx –disable-x11 –disable-wayland –enable-dispmanx –with-gles2-module-name=/opt/vc/lib/libGLESv2.so –with-egl-module-name=/opt/vc/lib/libEGL.so
```
NB: Raspbian 8 provides a properly compiled gst-plugins-bad and does not require recompiling

## Requirements

### Raspbian 8

* python3-gi
* gstreamer1.0-plugins-base gstreamer1.0-plugins-bad

### Arch Linux

Standard packages
* gstreamer gst-plugins-base gst-plugins-bad gst-plugins-ugly
* python-gobject

Aur packages
* optional: python-rift-git (will install hidapi-git openhmd-git oculus-udev python-rift-git fox)
