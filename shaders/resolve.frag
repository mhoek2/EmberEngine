#version 330 core

out vec4 out_color;

in vec2 fragTexCoord;

uniform sampler2DMS msaa_texture;
uniform int samples;

void main() {
    out_color = vec4(0.0);

    for ( int i = 0; i < samples; ++i )
        out_color += texelFetch( msaa_texture, ivec2( fragTexCoord * vec2( 1500, 1000 ) ), i );

    out_color /= float( samples );
}