#!/bin/bash
# Copyright 2015, Florent Thiery 
CMD=gst-gtklaunch-1.0
#CMD=gst-launch-1.0
$CMD videotestsrc ! video/x-raw\,\ format\=\(string\)YUY2\,\ width\=\(int\)640\,\ height\=\(int\)360 ! queue ! glupload ! glcolorconvert ! glcolorscale ! video/x-raw\(memory:GLMemory\)\,\ width\=\(int\)1280\,\ height\=\(int\)800\,\ pixel-aspect-ratio\=\(fraction\)1/1\,\ interlace-mode\=\(string\)progressive\,\ framerate\=\(fraction\)30/1\,\ format\=\(string\)RGBA ! gltransformation ! glshader fragment="\"`cat oculus.frag`\"" ! glimagesink
