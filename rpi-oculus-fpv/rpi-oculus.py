#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, Florent Thiery 

import logging
logger = logging.getLogger('FpvPipeline')

import gi
gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst

#source = "v4l2src ! video/x-raw, format=(string)YUY2, width=(int)640, height=(int)360 ! queue"
source = "videotestsrc ! video/x-raw, format=(string)YUY2, width=(int)720, height=(int)480 ! queue"

display = "tee name=src ! queue ! glupload ! glcolorconvert ! glcolorscale ! video/x-raw(memory:GLMemory), width=(int)1280, height=(int)800, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, framerate=(fraction)30/1, format=(string)RGBA ! gltransformation ! glshader location=oculus.frag ! glimagesink"

encoder = "src. ! queue ! videoconvert ! x264enc tune=zerolatency speed-preset=1 bitrate=4000 ! mp4mux ! filesink location=test.mp4"

def init():
    GObject.threads_init()
    Gst.init(None)
    #Gst.debug_set_active(True)
    #Gst.debug_set_colored(True)
    #Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)

class FpvPipeline:
    def __init__(self):
        self.next_actions = list()
        self.record = False

    def toggle_record(self):
        self.record = not self.record
        logger.info('Toggling record to state %s' %self.record)
        self.start()

    def start(self):
        if self.is_running():
            self.add_next_action(self.start)
            self.stop()
            return
        logger.info("Record: %s" %self.record)
        pipeline_desc = self.get_pipeline(self.record)
        logger.debug("Running %s" %pipeline_desc)
        self.pipeline = self.parse_pipeline(pipeline_desc)
        self.activate_bus()
        self.pipeline.set_state(Gst.State.PLAYING)

    def is_running(self):
        if not hasattr(self, 'pipeline'):
            return False
        return self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[1] == Gst.State.PLAYING

    def stop(self):
        self.send_eos()

    def get_pipeline(self, record=False):
        elts = [source, display]
        p = ' ! '.join(elts)
        if record:
            p = "%s %s" %(p, encoder)
        return p

    def parse_pipeline(self, pipeline):
        return Gst.parse_launch(pipeline)

    def send_eos(self, *args):
        logger.info("Sending EOS")
        event = Gst.Event.new_eos()
        Gst.Element.send_event(self.pipeline, event)

    def on_eos(self):
        logger.info('Got EOS')
        self.pipeline.set_state(Gst.State.NULL)
        self.run_next_action()

    def run_next_action(self):
        next_action = self.next_actions.pop(0)
        next_action()

    def add_next_action(self, action):
        self.next_actions.append(action)

    def activate_bus(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_message)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_string = "{0} {1}".format(err, debug)
            logger.info("Error: {0}".format(error_string))
        elif t == Gst.MessageType.EOS:
            self.on_eos()
        elif t == Gst.MessageType.ELEMENT:
            name = message.get_structure().get_name()
            res = message.get_structure()
            source = message.src.get_name()  # (str(message.src)).split(":")[2].split(" ")[0]
            #self.launch_event(name, {"source": source, "data": res})
            #self.launch_event('gst_element_message', {"source": source, "name": name, "data": res})
        else:
            logger.debug("got unhandled message type {0}, structure {1}".format(t, message))

if __name__ == '__main__':

    import logging
    import sys

    logging.basicConfig(
        level=getattr(logging, "DEBUG"),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    init()

    f = FpvPipeline()
    GObject.idle_add(f.start)
    GObject.timeout_add_seconds(10, f.toggle_record)
    GObject.timeout_add_seconds(20, f.toggle_record)
    ml = GObject.MainLoop()
    ml.run()
