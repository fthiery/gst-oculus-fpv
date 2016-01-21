# gst-oculus-fpv

This software uses gstreamer and OpenGL to to produce side-by-side video from a single video input (e.g. FPV quadcopters) for display on an OculusRift device. It also supports headtracking for a partial field of view over the video texture. 

![screenshot](https://raw.githubusercontent.com/fthiery/gst-oculus-fpv/master/screenshot.jpg)

[Video demo on YouTube](https://www.youtube.com/watch?v=mgGwPvxkLoo)

## Requirements

### Hardware

* Oculus Rift DK1 (probably works with DK2 too)
* Tested on Intel graphics, runs @140 fps on i5-3570K and @100 fps with headtracking enabled

### Arch Linux

Standard packages
* gstreamer gst-plugins-base gst-plugins-bad gst-plugins-ugly
* python-gobject

Aur packages
* optional for the headtracking: python-rift-git (will install hidapi-git openhmd-git oculus-udev python-rift-git fox)
