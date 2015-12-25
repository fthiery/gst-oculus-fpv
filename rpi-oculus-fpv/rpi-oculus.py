#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, Florent Thiery 

import sys
import logging
logger = logging.getLogger('FpvPipeline')

import json

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
GObject.threads_init()
Gst.init(None)
Gst.debug_set_active(True)
Gst.debug_set_colored(True)
Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)
#Gst.debug_set_threshold_for_name("glimage*", 5)

#source = "v4l2src ! video/x-raw, format=(string)YUY2, width=(int)640, height=(int)360, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, colorimetry=(string)1:4:7:1, framerate=(fraction)30/1"
source = 'videotestsrc ! video/x-raw, format=(string)YUY2, width=(int)720, height=(int)480'

display_pattern = 'tee name=src ! queue name=qtimeoverlay ! timeoverlay name=timeoverlay font-desc="Arial {font_size}" silent=true ! glupload ! glcolorconvert ! glcolorscale ! videorate ! video/x-raw(memory:GLMemory), width=(int){display_width}, height=(int){display_height}, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, framerate=(fraction){render_fps}/1, format=(string)RGBA ! gltransformation name=gltransformation ! glshader location=oculus.frag ! glimagesink name=glimagesink'

encoder_pattern = 'src. ! queue ! videoconvert ! x264enc tune=zerolatency speed-preset=1 bitrate={bitrate_video} ! mp4mux ! filesink location=test.mp4'

config_default = {
    'headtracker_enable': True,
    'render_fps': 60,
    'font_size': 30,
    'bitrate_video': 4000,
    'display_width': 1280,
    'display_height': 800,
}

def save_config(json_text, config_fpath):
    with open(config_fpath, 'w') as config_file:
        json.dump(json_text, config_file, sort_keys=True, indent=4, separators=(',', ': '))

def read_config(config_fpath):
    with open(config_fpath, 'r') as config_file:
        return json.load(config_file)

try:
    config_fpath = 'config.json'
    config = read_config(config_fpath)
    for k in config_default.keys():
        changed = False
        if not config.get(k):
            config[k] = config_default[k]
            changed = True
        if changed:
            save_config(config, config_fpath)
            print('Config updated')
except Exception as e:
    print('Error while parsing configuration file, using defaults (%s)' %e)
    config = config_default


class FpvPipeline:
    def __init__(self):
        self.post_eos_actions = list()
        self.record = False

    def start(self):
        if self.is_running():
            self.add_post_eos_action(self.start)
            self.stop()
            return
        logger.info("Record: %s" %self.record)
        pipeline_desc = self.get_pipeline_description(self.record)
        logger.debug("Running %s" %pipeline_desc)
        self.pipeline = self.parse_pipeline(pipeline_desc)
        if self.record:
            self.set_record_overlay()
        self.activate_bus()
        if config['headtracker_enable']:
            self.activate_frame_callback()
        self.pipeline.set_state(Gst.State.PLAYING)

    def toggle_record(self):
        self.record = not self.record
        logger.info('Toggling record to state %s' %self.record)
        self.start()

    def stop(self):
        self.send_eos()

    def exit(self):
        logger.info('Exiting cleanly')
        self.add_post_eos_action(sys.exit)
        self.stop()

    def get_pipeline_description(self, record=False):
        display = display_pattern.format(**config)
        encoder = encoder_pattern.format(**config)
        elts = [source, display]
        p = ' ! '.join(elts)
        if record:
            p = "%s %s" %(p, encoder)
        return p

    def parse_pipeline(self, pipeline):
        return Gst.parse_launch(pipeline)

    def activate_bus(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        
        #self.bus.connect('message', self._on_message)
        self.bus.connect('message::eos', self._on_eos)
        self.bus.connect('message::error', self._on_error)

    def activate_frame_callback(self):
        sink = self.pipeline.get_by_name('glimagesink')
        sink.connect("client-draw", self._on_draw)

    def _on_draw(self, src, glcontext, sample, *args):
        #print('Frame')
        pass

    def _on_eos(self, bus, message):
        logger.info("Got EOS")
        self.pipeline.set_state(Gst.State.NULL)
        self.run_post_eos_actions()

    def _on_error(self, bus, message):
        err, debug = message.parse_error()
        error_string = "{0} {1}".format(err, debug)
        logger.error("Error: {0}".format(error_string))

    def _on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ELEMENT:
            name = message.get_structure().get_name()
            res = message.get_structure()
            source = message.src.get_name()  # (str(message.src)).split(":")[2].split(" ")[0]
            #self.launch_event(name, {"source": source, "data": res})
            #self.launch_event('gst_element_message', {"source": source, "name": name, "data": res})
        else:
            logger.debug("got unhandled message type {0}, structure {1}".format(t, message))

    def send_eos(self, *args):
        if hasattr(self, "pipeline") and self.is_running():
            logger.info("Sending EOS")
            event = Gst.Event.new_eos()
            Gst.Element.send_event(self.pipeline, event)
        else:
            logger.info("No pipeline or pipeline not running, skipping EOS emission")
            self.run_post_eos_actions()

    def run_post_eos_actions(self):
        for action in self.post_eos_actions:
            logger.debug('Calling %s' %action)
            action()
        self.post_eos_actions = list()

    def add_post_eos_action(self, action):
        if callable(action):
            self.post_eos_actions.append(action)
        else:
            logger.error('Action %s not callable' %action)

    def set_record_overlay(self):
        o = self.pipeline.get_by_name('timeoverlay')
        o.set_property('text', 'Rec')
        o.set_property('silent', False)

    def is_running(self):
        if not hasattr(self, 'pipeline'):
            return False
        return self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[1] == Gst.State.PLAYING

if __name__ == '__main__':

    import signal

    logging.basicConfig(
        level=getattr(logging, "DEBUG"),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    f = FpvPipeline()
    GObject.idle_add(f.start)
    #GObject.timeout_add_seconds(3, f.toggle_record)
    #GObject.timeout_add_seconds(13, f.exit)

    def signal_handler(signal, frame):
        print('You pressed Ctrl+C!')
        f.exit()
    GObject.idle_add(signal.signal, signal.SIGINT, signal_handler)

    ml = GObject.MainLoop()
    ml.run()
