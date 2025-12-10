#version 330 core

uniform vec3 uSkyColor;
uniform vec3 uHorizonColor;
uniform vec3 uGroundColor;

uniform vec3 uSunsetColor;
uniform vec3 uNightColor;

uniform vec3 uSunDirection;
uniform vec3 uSunColor;

uniform float uNightBrightness;

in vec3 vTexCoord;
out vec4 out_color;

void main()
{
    vec3 dir = normalize(vTexCoord);

    // settings
    float horizon_offset            = 0.0;
    float sun_glow_size             = 512.0;
    float scattering_mask_offset    = 0.05;
    int global_night_color          = 0;

    float sunHeight = clamp(uSunDirection.y, -0.3, 0.8);

    // Day-night transition
    float dayFactor = smoothstep(-0.1, 0.3, sunHeight);

    // Sky gradient
    float t = dir.y * 0.5 + 0.5;

    // sunset influence on horizon color
    float horizonSunsetFactor = 1.0 - smoothstep(0.15, 0.5, uSunDirection.y);
    vec3 horizonColorFinal = mix(uHorizonColor, uSunsetColor, horizonSunsetFactor);

    vec3 sky = mix(horizonColorFinal, uSkyColor, t);

    if (dir.y < horizon_offset)
        sky = mix(uGroundColor, horizonColorFinal, t);

    // Apply night color
    if (global_night_color > 0)
        sky = mix(uNightColor, sky, dayFactor);

    // Sunset color blend for sun
    float sunsetFactor = 1.0 - smoothstep(0.1, 0.4, sunHeight);
    vec3 sunColorFinal = mix(uSunColor, uSunsetColor, sunsetFactor);

    // Sun glow
    float sunViewAlignment = max(dot(dir, normalize(uSunDirection)), 0.0);
    float sunGlow = pow(sunViewAlignment, sun_glow_size) * dayFactor;

    sky += sunColorFinal * sunGlow;

    // General brightness fade at night
    sky *= mix(uNightBrightness, 1.0, dayFactor);

    // Wide atmospheric scattering near sun (sunset only)
    float sunDot = max(dot(dir, normalize(uSunDirection)), 0.0);
    float scatter = pow(sunDot, 4.0);

    float scatterSunset = 1.0 - smoothstep(0.25, 0.6, sunHeight);
    float nightFade = smoothstep(-0.4, 0.0, sunHeight);
    float scatterVisibility = scatterSunset * nightFade;

    // vertical mask to avoid affecting the ground too much
    float verticalMask = smoothstep(horizon_offset, horizon_offset + scattering_mask_offset, dir.y);

    vec3 atmosphereScatter = uSunsetColor * scatter * scatterVisibility * verticalMask;
    sky += atmosphereScatter;

    // Darken / cool opposite the sun
    float backLit = max(dot(dir, -normalize(uSunDirection)), 0.0);
    float backFade = backLit * (1.0 - dayFactor);
    sky -= backFade * 0.2;
    sky = mix(sky, uNightColor, backFade * 0.3);

    // Horizon haze (horizontal fog)
    float horizonFog = exp(-abs(dir.y) * 12.0);
    vec3 fogColor = mix(uHorizonColor, uSunsetColor, horizonSunsetFactor);
    sky = mix(sky, fogColor, horizonFog * 0.25);

    out_color = vec4(sky, 1.0);
}
