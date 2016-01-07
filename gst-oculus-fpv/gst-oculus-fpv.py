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
pipeline_source = 'videotestsrc ! video/x-raw, format=(string)YUY2, width=(int)720, height=(int)480'
#pipeline_source = 'filesrc location=../sim.mp4 ! qtdemux ! avdec_h264 ! queue'

# as of gsteamer 1.6.2 glimagesink currently does not yet post key presses on the bus, so lets use xvimagesink to toggle recording using the "r" key for testing and "q" for quitting (ctrl+c also works)
#pipeline_preprocess_pattern = 'tee name=src ! queue name=qtimeoverlay ! timeoverlay name=timeoverlay font-desc="Arial {font_size}" silent=true ! glupload ! glcolorconvert ! glcolorscale ! videorate ! video/x-raw(memory:GLMemory), width=(int){display_width}, height=(int){display_height}, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, framerate=(fraction){render_fps}/1, format=(string)RGBA ! gltransformation name=gltransformation ! glshader location=oculus.frag ! gldownload ! queue ! videoconvert ! xvimagesink name=glimagesink'
pipeline_preprocess_pattern = 'tee name=src ! queue name=qtimeoverlay ! timeoverlay name=timeoverlay font-desc="Arial {font_size}" silent=true ! glupload ! glcolorconvert ! glcolorscale ! videorate ! video/x-raw(memory:GLMemory), width=(int){display_width}, height=(int){display_height}, pixel-aspect-ratio=(fraction)1/1, interlace-mode=(string)progressive, framerate=(fraction){render_fps}/1, format=(string)RGBA'

pipeline_headtracker = 'gltransformation name=gltransformation'
pipeline_sink = 'glshader name=glshader ! glimagesink name=glimagesink'

pipeline_encoder_pattern = 'src. ! queue ! videoconvert ! x264enc tune=zerolatency speed-preset=1 bitrate={bitrate_video} ! mp4mux ! filesink location=test.mp4'
#pipeline_encoder_pattern = 'src. ! queue ! vaapipostproc ! vaapiencode_h264 rate-control=2 bitrate={bitrate_video} ! h264parse ! mp4mux ! filesink location=test_vaapi.mp4'

shader_pattern = '''
#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;

const vec4 kappa = vec4(1.0,1.7,0.7,15.0);

const float screen_width = {display_width}.0;
const float screen_height = {display_height}.0;

const float scaleFactor = 0.9;

const vec2 leftCenter = vec2(0.25, 0.5);
const vec2 rightCenter = vec2(0.75, 0.5);

const float separation = -0.05;

const bool stereo_input = false;

// Scales input texture coordinates for distortion.
vec2 hmdWarp(vec2 LensCenter, vec2 texCoord, vec2 Scale, vec2 ScaleIn) {{
    vec2 theta = (texCoord - LensCenter) * ScaleIn; 
    float rSq = theta.x * theta.x + theta.y * theta.y;
    vec2 rvector = theta * (kappa.x + kappa.y * rSq + kappa.z * rSq * rSq + kappa.w * rSq * rSq * rSq);
    vec2 tc = LensCenter + Scale * rvector;
    return tc;
}}

bool validate(vec2 tc, int eye) {{
    if ( stereo_input ) {{
        //keep within bounds of texture 
        if ((eye == 1 && (tc.x < 0.0 || tc.x > 0.5)) ||   
            (eye == 0 && (tc.x < 0.5 || tc.x > 1.0)) ||
            tc.y < 0.0 || tc.y > 1.0) {{
            return false;
        }}
    }} else {{
        if ( tc.x < 0.0 || tc.x > 1.0 || 
             tc.y < 0.0 || tc.y > 1.0 ) {{
             return false;
        }}
    }}
    return true;
}}

void main() {{
    float as = float(screen_width / 2.0) / float(screen_height);
    vec2 Scale = vec2(0.5, as);
    vec2 ScaleIn = vec2(2.0 * scaleFactor, 1.0 / as * scaleFactor);

    vec2 texCoord = v_texcoord;
    
    vec2 tc = vec2(0);
    vec4 color = vec4(0);
    
    if ( texCoord.x < 0.5 ) {{
        texCoord.x += separation;
        texCoord = hmdWarp(leftCenter, texCoord, Scale, ScaleIn );
        
        if ( !stereo_input ) {{
            texCoord.x *= 2.0;
        }}
        
        color = texture2D(tex, texCoord);
        
        if ( !validate(texCoord, 0) ) {{
            color = vec4(0);
        }}
    }} else {{
        texCoord.x -= separation;
        texCoord = hmdWarp(rightCenter, texCoord, Scale, ScaleIn);
        
        if ( !stereo_input ) {{
            texCoord.x = (texCoord.x - 0.5) * 2.0;
        }}
        
        color = texture2D(tex, texCoord);
        
        if ( !validate(texCoord, 1) ) {{
            color = vec4(0);
        }}
    }}
    
    gl_FragColor = color;
}}
'''

config_default = {
    'headtracker_enable': True,
    'headtracker_fov': 70,
    'render_fps': 60,
    'font_size': 30,
    'bitrate_video': 4000,
    'display_width': 1280,
    'display_height': 800,
}

def save_config(config_dict, config_fpath):
    with open(config_fpath, 'w') as config_file:
        json.dump(config_dict, config_file, sort_keys=True, indent=4, separators=(',', ': '))

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

if config['headtracker_enable']:
    from rift import PyRift
    import math

class FpvPipeline:
    def __init__(self, mainloop=None):
        self.post_eos_actions = list()
        self.record = False
        self.mainloop = mainloop
        if config['headtracker_enable']:
            self.rift = PyRift()
            logger.debug('OpenHMD detection result:')
            logger.debug(self.rift.printDeviceInfo())

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
        self.update_shader()
        if config['headtracker_enable']:
            self.enable_frame_callback()
            self.enable_headtracker_fov()
        self.pipeline.set_state(Gst.State.PLAYING)

    def toggle_record(self):
        self.record = not self.record
        logger.info('Toggling record to state %s' %self.record)
        self.start()

    def stop(self):
        GObject.idle_add(self.send_eos)

    def exit(self):
        logger.info('Exiting cleanly')
        if self.mainloop:
            logger.debug('Stopping mainloop')
            self.add_post_eos_action(self.mainloop.quit)
        else:
            logger.warning('Exiting (sys.exit)')
            self.add_post_eos_action(sys.exit)
        self.stop()

    # Initializations

    def get_pipeline_description(self, record=False):
        pipeline_preprocess = pipeline_preprocess_pattern.format(**config)
        pipeline_encoder = pipeline_encoder_pattern.format(**config)

        if config['headtracker_enable']:
            elts = [pipeline_source, pipeline_preprocess, pipeline_headtracker, pipeline_sink]
        else:
            elts = [pipeline_source, pipeline_preprocess, pipeline_sink]

        p = ' ! '.join(elts)
        if record:
            p = "%s %s" %(p, pipeline_encoder)
        return p

    def activate_bus(self):
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        
        self.bus.connect('message', self._on_message)
        self.bus.connect('message::eos', self._on_eos)
        self.bus.connect('message::error', self._on_error)

    def enable_frame_callback(self):
        sink = self.pipeline.get_by_name('glimagesink')
        if sink:
            sink.connect("client-draw", self._on_frame)

    def enable_headtracker_fov(self):
        gltransformation = self.pipeline.get_by_name('gltransformation')
        gltransformation.set_property('fov', config['headtracker_fov'])
        gltransformation.set_property('pivot-z', 30)

    def update_headtracker_fov(self, rot_x, rot_y, rot_z):
        gltransformation = self.pipeline.get_by_name('gltransformation')
        gltransformation.set_property('rotation-x', rot_x)
        gltransformation.set_property('rotation-y', rot_y)
        gltransformation.set_property('rotation-z', rot_z)

    def update_shader(self):
        shader = shader_pattern.format(**config)
        glshader = self.pipeline.get_by_name('glshader')
        try:
            glshader.set_property("fragment", shader)
        except TypeError:
            glshader.set_property("location", "oculus.frag")

    def set_record_overlay(self):
        o = self.pipeline.get_by_name('timeoverlay')
        o.set_property('text', 'Rec')
        o.set_property('silent', False)

    # Event callbacks

    def _on_frame(self, src, glcontext, sample, *args):
      self.rift.poll()
      x, y, z, w = self.rift.rotation
      yaw = math.asin(2*x*y + 2*z*w)
      pitch = math.atan2(2*x*w - 2*y*z, 1 - 2*x*x - 2*z*z)
      roll = math.atan2(2*y*w - 2*x*z, 1 - 2*y*y - 2*z*z)
      #logger.debug("rotation quat: %f %f %f %f, yaw: %s pitch: %s roll: %s" % (x, y, z, w, yaw, pitch, roll))
      GObject.idle_add(self.update_headtracker_fov, pitch, -roll, yaw, priority=GObject.PRIORITY_HIGH)

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
            struct = message.get_structure()
            sname = struct.get_name()
            if sname == 'GstNavigationMessage':
                event = struct.get_value('event')
                estruct = event.get_structure()
                if estruct.get_value('event') == "key-release":
                    key = estruct.get_value('key')
                    self._on_key_release(key)
                #self.print_struct_content(estruct)
        else:
            #logger.debug("got unhandled message type {0}, structure {1}".format(t, message))
            pass

    def _on_key_release(self, key):
        logger.info('Key %s released' %key)
        if key == "r":
            self.toggle_record()
        elif key == "q":
            self.exit()

    # GStreamer helpers

    def parse_pipeline(self, pipeline):
        return Gst.parse_launch(pipeline)

    def is_running(self):
        if not hasattr(self, 'pipeline'):
            return False
        return self.pipeline.get_state(Gst.CLOCK_TIME_NONE)[1] == Gst.State.PLAYING

    def print_struct_content(self, struct):
        for i in range(struct.n_fields()):
            field_name = struct.nth_field_name(i)
            field_value = struct.get_value(field_name)
            print('%s = %s' %(field_name, field_value))

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


if __name__ == '__main__':
    logging.basicConfig(
        level=getattr(logging, "DEBUG"),
        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        stream=sys.stderr
    )

    ml = GObject.MainLoop()
    f = FpvPipeline(ml)
    GObject.idle_add(f.start)
    #GObject.timeout_add_seconds(3, f.toggle_record)
    #GObject.timeout_add_seconds(13, f.exit)

    try:
        ml.run()
    except KeyboardInterrupt:
        logger.info('Ctrl+C hit, stopping')
        f.exit()
