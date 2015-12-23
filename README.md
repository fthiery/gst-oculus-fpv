# rpi-oculus-fpv

NB: this is work in progress

Use a raspberrypi to produce side-by-side video from FPV video (ex: quadcopters). Currently designed for Oculus Rift DK1 and other dedicated HMDs that have a single input and require side by side rendering.

## Compiling glimagesink for rpi

Note that glimagesink needs to have been compiled for GLES/EGL/dispmanx for hardware acceleration to be enabled. See the following configure flags:

```
./configure CFLAGS=”-I/opt/vc/include -I /opt/vc/include/interface/vcos/pthreads -I /opt/vc/include/interface/vmcs_host/linux/” LDFLAGS=”-L/opt/vc/lib” –disable-gtk-doc –disable-opengl –enable-gles2 –enable-egl –disable-glx –disable-x11 –disable-wayland –enable-dispmanx –with-gles2-module-name=/opt/vc/lib/libGLESv2.so –with-egl-module-name=/opt/vc/lib/libEGL.so
```
