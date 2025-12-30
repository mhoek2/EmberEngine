#version 460

in vec2 fragTexCoord;
out vec4 out_color;

uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

uniform vec4 u_ViewOrigin;

uniform float ufogDensity;
uniform float ufogHeight;
uniform float ufogFalloff;
uniform int ufogLightsContrib;

uniform vec4 in_lightcolor;

uniform sampler2D sColorTexture;
uniform sampler2D sDepthTexture;

#define LIGHT_TYPE_DIRECTIONAL	0
#define LIGHT_TYPE_SPOT			1
#define LIGHT_TYPE_AREA			2

struct Light
{
	vec4	origin;
	vec4	color;
	vec4	rotation;
};

layout( std140 ) uniform Lights
{
	int u_num_lights;
	Light u_lights[64];
};

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

vec3 computeFogLightTint(vec3 fogPos)
{
    vec3 tint = vec3(0.0);

    for (int i = 0; i < u_num_lights; i++)
    {
        Light light = u_lights[i];
        vec3 lightPos = light.origin.xyz;
        vec3 lightColor = light.color.rgb;

        float dist = length(fogPos - lightPos);

        float attenuation = 1.0 / (dist * dist + 1.0); 
        tint += lightColor * attenuation;
    }

    return tint;
}

vec3 computeFogLightTintRadius(vec3 fogPos)
{
    vec3 tint = vec3(0.0);

    for (int i = 0; i < u_num_lights; i++)
    {
        Light light = u_lights[i];
        vec3 lightPos = light.origin.xyz;
        vec3 lightColor = light.color.rgb;
        float radius = 1.0;

        float dist = length(fogPos - lightPos);

        if (dist < radius)
        {
            float attenuation = 1.0 - (dist / radius);
            tint += lightColor * attenuation;
        }
    }

    return tint;
}

void main()
{
    vec3 sceneColor = texture(sColorTexture, fragTexCoord).rgb;
    float depth     = texture(sDepthTexture, fragTexCoord).r;
    
    vec3 viewPos    = reconstructViewPos(fragTexCoord, depth);
    vec3 worldPos   = (inverse(uVMatrix) * vec4(viewPos, 1.0)).xyz;
    vec3 cameraPos  = u_ViewOrigin.xyz;
    vec3 fogColor   = in_lightcolor.rgb;

    // additive
    if(ufogLightsContrib == 1)
    {
        fogColor += computeFogLightTint(worldPos);
    }

    // additive clamped
    else if(ufogLightsContrib == 2)
    {
        vec3 lightTint   = computeFogLightTintRadius(worldPos);
        fogColor = max(fogColor, fogColor + lightTint);    
    }

    float fog = clamp( computeHeightFog(
        worldPos,
        cameraPos,
        ufogDensity,
        ufogHeight,
        ufogFalloff
    ), 0.0, 1.0);

    fogColor = clamp(fogColor, 0.0, 1.0);
    out_color = vec4(mix(sceneColor, fogColor, fog), 1.0);
}
