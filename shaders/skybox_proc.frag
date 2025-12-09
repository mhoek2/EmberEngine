#version 330 core

uniform vec3 uSkyColor;
uniform vec3 uHorizonColor;
uniform vec3 uGroundColor;

uniform vec3 uSunDirection;
uniform vec3 uSunColor;

in vec3 vTexCoord;
out vec4 out_color;

void main()
{
    vec3 dir = normalize(vTexCoord);

    float horizon_offset = 0.0;
    float sun_glow_size = 512.0;

    float t = dir.y * 0.5 + 0.5;
    vec3 sky = mix( uHorizonColor, uSkyColor, t );

    // ground tint
    if ( dir.y < horizon_offset )
        sky = mix( uGroundColor, uHorizonColor, t );

    // sun glow
    float sunViewAlignment = max( dot (dir, normalize( uSunDirection ) ), 0.0 );
    float sunGlow = pow( sunViewAlignment, sun_glow_size );

    sky += uSunColor * sunGlow;

    out_color = vec4(sky, 1.0);
}