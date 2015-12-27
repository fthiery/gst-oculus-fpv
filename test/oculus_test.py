#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, Florent Thiery 

from rift import PyRift
import math

foo = PyRift()

while True:
  foo.poll()
  x, y, z, w = foo.rotation
  yaw = math.asin(2*x*y + 2*z*w)
  pitch = math.atan2(2*x*w - 2*y*z, 1 - 2*x*x - 2*z*z)
  roll = math.atan2(2*y*w - 2*x*z, 1 - 2*y*y - 2*z*z)
  print("rotation quat: %f %f %f %f, yaw: %s pitch: %s roll: %s" % (x, y, z, w, yaw, pitch, roll))
