#version 460

in vec2 fragTexCoord;
out vec4 out_color;

uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

uniform vec4 u_ViewOrigin;

uniform float ufogDensity;
uniform float ufogHeight;
uniform float ufogFalloff;

uniform vec4 in_lightcolor;

uniform sampler2D sColorTexture;
uniform sampler2D sDepthTexture;

vec3 reconstructViewPos(vec2 uv, float depth)
{
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 view = inverse(uPMatrix) * clip;
    return view.xyz / view.w;
}

float computeHeightFog(
    vec3 worldPos,
    vec3 cameraPos,
    float density,
    float height,
    float falloff
) {
    vec3 ray = worldPos - cameraPos;
    float rayLength = length(ray);
    vec3 rayDir = ray / rayLength;

    float y0 = cameraPos.y;
    float y1 = worldPos.y;

    float fog = 0.0;

    if (abs(y1 - y0) < 0.001) {
        // ray is almost horizontal
        fog = density * rayLength * exp(-(y0 - height) * falloff);
    } else {
        float dy = y1 - y0;
        float k = falloff;

        float exp0 = exp(-(y0 - height) * k);
        float exp1 = exp(-(y1 - height) * k);

        fog = density * (exp0 - exp1) * rayLength / (dy * k);
    }

    return 1.0 - exp(-fog);
}

void main()
{
    vec3 sceneColor = texture(sColorTexture, fragTexCoord).rgb;
    float depth     = texture(sDepthTexture, fragTexCoord).r;
    
    vec3 viewPos    = reconstructViewPos(fragTexCoord, depth);
    vec3 worldPos   = (inverse(uVMatrix) * vec4(viewPos, 1.0)).xyz;
    vec3 cameraPos  = u_ViewOrigin.xyz;
    vec3 fogColor   = in_lightcolor.rgb;

    float fog = clamp( computeHeightFog(
        worldPos,
        cameraPos,
        ufogDensity,
        ufogHeight,
        ufogFalloff
    ), 0.0, 1.0);

    out_color = vec4(mix(sceneColor, fogColor, fog), 1.0);
}
