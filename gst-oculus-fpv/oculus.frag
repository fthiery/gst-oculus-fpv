#version 100
#ifdef GL_ES
precision mediump float;
#endif
varying vec2 v_texcoord;
uniform sampler2D tex;

const vec4 kappa = vec4(1.0,1.7,0.7,15.0);

const float screen_width = 1280.0;
const float screen_height = 800.0;

const float scaleFactor = 0.9;

const vec2 leftCenter = vec2(0.25, 0.5);
const vec2 rightCenter = vec2(0.75, 0.5);

const float separation = -0.05;

const bool stereo_input = false;

// Scales input texture coordinates for distortion.
vec2 hmdWarp(vec2 LensCenter, vec2 texCoord, vec2 Scale, vec2 ScaleIn) {
    vec2 theta = (texCoord - LensCenter) * ScaleIn; 
    float rSq = theta.x * theta.x + theta.y * theta.y;
    vec2 rvector = theta * (kappa.x + kappa.y * rSq + kappa.z * rSq * rSq + kappa.w * rSq * rSq * rSq);
    vec2 tc = LensCenter + Scale * rvector;
    return tc;
}

bool validate(vec2 tc, int eye) {
    if ( stereo_input ) {
        //keep within bounds of texture 
        if ((eye == 1 && (tc.x < 0.0 || tc.x > 0.5)) ||   
            (eye == 0 && (tc.x < 0.5 || tc.x > 1.0)) ||
            tc.y < 0.0 || tc.y > 1.0) {
            return false;
        }
    } else {
        if ( tc.x < 0.0 || tc.x > 1.0 || 
             tc.y < 0.0 || tc.y > 1.0 ) {
             return false;
        }
    }
    return true;
}

void main() {
    float as = float(screen_width / 2.0) / float(screen_height);
    vec2 Scale = vec2(0.5, as);
    vec2 ScaleIn = vec2(2.0 * scaleFactor, 1.0 / as * scaleFactor);

    vec2 texCoord = v_texcoord;
    
    vec2 tc = vec2(0);
    vec4 color = vec4(0);
    
    if ( texCoord.x < 0.5 ) {
        texCoord.x += separation;
        texCoord = hmdWarp(leftCenter, texCoord, Scale, ScaleIn );
        
        if ( !stereo_input ) {
            texCoord.x *= 2.0;
        }
        
        color = texture2D(tex, texCoord);
        
        if ( !validate(texCoord, 0) ) {
            color = vec4(0);
        }
    } else {
        texCoord.x -= separation;
        texCoord = hmdWarp(rightCenter, texCoord, Scale, ScaleIn);
        
        if ( !stereo_input ) {
            texCoord.x = (texCoord.x - 0.5) * 2.0;
        }
        
        color = texture2D(tex, texCoord);
        
        if ( !validate(texCoord, 1) ) {
            color = vec4(0);
        }
    }
    
    gl_FragColor = color;
}
