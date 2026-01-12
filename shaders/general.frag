// version added programmicly

#ifdef USE_BINDLESS_TEXTURES
#extension GL_ARB_bindless_texture : enable
#extension GL_NV_uniform_buffer_std430_layout : enable
#extension GL_NV_gpu_shader5 : enable
#endif

precision highp float;

#define PI 3.1415926535897932384626433832795

uniform samplerCube sEnvironment;
uniform sampler2D sBRDF;
#ifdef USE_SHADOWMAP
uniform sampler2D sShadowMap;
uniform int ushadowmapEnabled;
#endif

in vec2 vTexCoord;
in float var_roughnessOverride;
in float var_metallicOverride;

in vec4 var_Tangent;
in vec4 var_BiTangent;
in vec4 var_Normal;
in vec4 var_LightDir;
in vec4 var_ViewDir;
#ifdef USE_SHADOWMAP
	in vec4 var_LightSpacePos;
#endif

in vec4 var_LightColor;
in vec4 var_AmbientColor;

flat in int var_material_index;

out vec4 out_color;

uniform vec4 u_ViewOrigin;
uniform int in_renderMode;

#define LIGHT_TYPE_DIRECTIONAL	0
#define LIGHT_TYPE_SPOT			1
#define LIGHT_TYPE_AREA			2

struct Light
{
	vec4	origin;
	vec4	color;
	vec4	rotation;
};

#ifdef USE_INDIRECT
layout( std140, binding = 0  ) uniform Lights
#else
layout( std140 ) uniform Lights
#endif
{
	int u_num_lights;
	Light u_lights[64];
};

#ifdef USE_BINDLESS_TEXTURES
	struct Material
	{
		uint64_t sTexture;
		uint64_t sNormal;
		uint64_t sPhysical;
		uint64_t sEmissive;
		uint64_t sOpacity;
		int      hasNormalMap;
		uint     padding;      // pad to 16 bytes alignment (std430 rules)
	};

	layout( std430, binding = 1 ) buffer Materials
	{
		Material u_materials[2096];
	};

	vec4 SampleAlbedo( Material mat, vec2 uv ) {
		sampler2D s = sampler2D( mat.sTexture );
		return texture( s, uv );
	}
	vec4 SampleNormal( Material mat, vec2 uv ) {
		sampler2D s = sampler2D( mat.sNormal );
		return texture( s, uv );
	}
	vec4 SamplePhysical( Material mat, vec2 uv ) {
		sampler2D s = sampler2D( mat.sPhysical );
		return texture( s, uv );
	}
	vec4 SampleEmissive( Material mat, vec2 uv ) {
		sampler2D s = sampler2D( mat.sEmissive );
		return texture( s, uv );
	}
	vec4 SampleOpacity( Material mat, vec2 uv ) {
		sampler2D s = sampler2D( mat.sOpacity );
		return texture( s, uv );
	}
#else
uniform sampler2D sTexture;
uniform sampler2D sNormal;
uniform sampler2D sPhysical;
uniform sampler2D sEmissive;
uniform sampler2D sOpacity;

	struct Material
	{
		vec4	data_0;
	};
	layout( std140 ) uniform Materials
	{
		Material u_materials[2096];
	};

	vec4 SampleAlbedo( Material mat, vec2 uv ) {
		return texture(sTexture, uv);
	}
	vec4 SampleNormal( Material mat, vec2 uv ) {
		return texture(sNormal, uv);
	}
	vec4 SamplePhysical( Material mat, vec2 uv ) {
		return texture(sPhysical, uv);
	}
	vec4 SampleEmissive( Material mat, vec2 uv ) {
		return texture(sEmissive, uv);
	}
	vec4 SampleOpacity( Material mat, vec2 uv ) {
		return texture(sOpacity, uv);
	}
#endif



vec3 Diffuse_Lambert(in vec3 DiffuseColor)
{
	return DiffuseColor * (1.0 / PI);
}

vec3 CalcDiffuse( in vec3 diffuse, in float NE, in float NL,
	in float LH, in float roughness )
{
	return Diffuse_Lambert(diffuse);
}

vec3 F_Schlick( in vec3 SpecularColor, in float VH )
{
	float Fc = pow(1 - VH, 5);
	return clamp(50.0 * SpecularColor.g, 0.0, 1.0) * Fc + (1 - Fc) * SpecularColor; //hacky way to decide if reflectivity is too low (< 2%)
}

float D_GGX( in float NH, in float a )
{
	float a2 = a * a;
	float d = (NH * a2 - NH) * NH + 1;
	return a2 / (PI * d * d);
}

// Appoximation of joint Smith term for GGX
// [Heitz 2014, "Understanding the Masking-Shadowing Function in Microfacet-Based BRDFs"]
float V_SmithJointApprox( in float a, in float NV, in float NL )
{
	float Vis_SmithV = NL * (NV * (1 - a) + a);
	float Vis_SmithL = NV * (NL * (1 - a) + a);
	return 0.5 * (1.0 / (Vis_SmithV + Vis_SmithL));
}

vec3 CalcSpecular( in vec3 specular, in float NH, in float NL,
	in float NE, float LH, in float VH, in float roughness )
{
	vec3  F = F_Schlick(specular, VH);
	float D = D_GGX(NH, roughness);
	float V = V_SmithJointApprox(roughness, NE, NL);

	return D * F * V;
}

vec3 CalcNormal( in Material mat, in vec3 vertexNormal, in vec2 frag_tex_coord )
{
#ifdef USE_BINDLESS_TEXTURES
	int hasNormalMap = mat.hasNormalMap;
#else
	int hasNormalMap = int( mat.data_0[0] );
#endif
	if ( hasNormalMap > 0  ) {
		vec3 biTangent = 1.0 * cross(vertexNormal, var_Tangent.xyz);
		vec3 n = SampleNormal(mat, frag_tex_coord).rgb - vec3(0.5);

		n.xy *= 1.0;
		n.z = sqrt(clamp((0.25 - n.x * n.x) - n.y * n.y, 0.0, 1.0));
		n = n.x * var_Tangent.rgb + n.y * biTangent + n.z * vertexNormal;

		return normalize(n);
	}
	
	return normalize(vertexNormal);
}

vec3 CalcIBLContribution( in float roughness, in vec3 N, in vec3 E,
	in float NE, in vec3 specular )
{
	vec3 R = reflect(-E, N);
	R.y *= -1.0f;
	
	vec3 cubeLightColor = textureLod(sEnvironment, R, roughness * 6).rgb * 1.0;
	vec2 EnvBRDF = texture(sBRDF, vec2(NE, 1.0 - roughness)).rg;

	return cubeLightColor * (specular.rgb * EnvBRDF.x + EnvBRDF.y);
}

float CalcLightAttenuation(float normDist)
{
	// zero light at 1.0, approximating q3 style
	float attenuation = 0.5 * normDist - 0.5;
	return clamp(attenuation, 0.0, 1.0);
}

vec3 CalcDynamicLightContribution(
	in float roughness,
	in vec3 N,
	in vec3 E,
	in vec3 viewOrigin,
	in vec3 viewDir,
	in float NE,
	in vec3 diffuse,
	in vec3 specular,
	in vec3 vertexNormal
)
{
	vec3 outColor = vec3(0.0);
	vec3 position = viewOrigin - viewDir;

    // Hard-coded spot cone
    const float innerCos = 0.90;
    const float outerCos = 0.70;

    for ( int i = 0; i < u_num_lights; i++ )
    {
        Light light = u_lights[i];

        vec3 L;
        float attenuation = 1.0;
        float radius = light.origin.w;
        int light_type = int(light.color.w);
        float light_intensity = light.rotation.w;

        if ( light_type == LIGHT_TYPE_DIRECTIONAL )
        {
            L = normalize(light.origin.xyz); 
            attenuation = 1.0; // no distance attenuation
        }
		
        // Spot and area lights are position-based
        else
        {
            L = light.origin.xyz - position;
            float sqrLightDist = dot(L, L);
            L /= sqrt(sqrLightDist);

            attenuation = CalcLightAttenuation(radius * radius / sqrLightDist);

            if ( light_type == LIGHT_TYPE_SPOT )
            {
                // rotation.xyz contains forward direction for the spot
                vec3 spotDir = normalize(light.rotation.xyz);

                float cosAngle = dot(L, spotDir);

                // hard-coded cone
                float spotFactor = clamp((cosAngle - outerCos) / (innerCos - outerCos), 0.0, 1.0);

                attenuation *= spotFactor;
            }
        }

		vec3 H = normalize(L + E);
		float NL = clamp(dot(N, L), 0.0, 1.0);
		float LH = clamp(dot(L, H), 0.0, 1.0);
		float NH = clamp(dot(N, H), 0.0, 1.0);
		float VH = clamp(dot(E, H), 0.0, 1.0);

		vec3 reflectance = diffuse + CalcSpecular(specular, NH, NL, NE, LH, VH, roughness);

		outColor += light.color.rgb * reflectance * attenuation * NL * light_intensity;
	}
	return outColor;
}

#ifdef USE_SHADOWMAP
	float ComputeShadow(in vec4 lightSpacePos)
	{
		vec3 projCoords = lightSpacePos.xyz / lightSpacePos.w;
		projCoords = projCoords * 0.5 + 0.5;

		float closestDepth = texture(sShadowMap, projCoords.xy).r;
		float currentDepth = projCoords.z;

		return (currentDepth > closestDepth) ? 0.0 : 1.0;
	}
#endif

void main()
{
	Material mat = u_materials[var_material_index];

	vec4 diffuse;
	float attenuation;
	vec3 viewDir, lightColor, ambientColor;
	vec3 L, N, E;

	vec4 base = SampleAlbedo(mat, vTexCoord);
	vec4 env = texture(sEnvironment, vec3(1.0, 0.0, 1.0) );

	viewDir = var_ViewDir.xyz;
	E = normalize(viewDir);

	L = var_LightDir.xyz;
	float sqrLightDist = dot(L, L);
	L /= sqrt(sqrLightDist);

	lightColor = var_LightColor.rgb;
	ambientColor = var_AmbientColor.rgb;
	diffuse = base;
	attenuation = 1.0;

	N = CalcNormal( mat, var_Normal.xyz, vTexCoord );	

	lightColor *= PI;

	/*ambientColor = lightColor;
	float surfNL = clamp(dot(var_Normal.xyz, L), 0.0, 1.0);
	lightColor /= max( surfNL, 0.25 );
	ambientColor = max( ambientColor - lightColor * surfNL, 0.0 );*/
	
	vec4 specular = vec4( 1.0 );
	float roughness = 0.99;
	float AO = 1.0;

	const vec4 specularScale = vec4( 1.0, 1.0, 1.0, 0.5 );

	// metallic roughness workflow
	//vec4 ORMS = SamplePhysical( mat, vTexCoord ).brga;
	vec4 ORMS = SamplePhysical( mat, vTexCoord ).rgba;
	ORMS.xyzw *= specularScale.zwxy;
	specular.rgb = mix(vec3(0.08) * ORMS.w, diffuse.rgb, ORMS.z);
	diffuse.rgb *= vec3(1.0 - ORMS.z);

	roughness = mix(0.01, 1.0, ORMS.y);
	AO = min(ORMS.x, AO);

	if ( var_roughnessOverride > 0.0 ) {
		roughness = var_roughnessOverride;
	}

	if ( var_metallicOverride > 0.0 ) {
		specular.rgb = vec3(var_metallicOverride);
	}

	ambientColor *= AO;

	vec3  H  = normalize( L + E );
	float NE = abs( dot( N, E ) ) + 1e-5;
	float NL = clamp( dot( N, L ), 0.0, 1.0 );
	float LH = clamp( dot( L, H ), 0.0, 1.0 );

	vec3  Fd = CalcDiffuse( diffuse.rgb, NE, NL, LH, roughness );
	vec3  Fs = vec3( 0.0 );

	float NH = clamp( dot( N, H ), 0.0, 1.0 );
	float VH = clamp( dot( E, H ), 0.0, 1.0 );
	Fs = CalcSpecular( specular.rgb, NH, NL, NE, LH, VH, roughness );

	vec3 emissiveColor = SampleEmissive( mat, vTexCoord ).rgb;

	vec3 reflectance = Fd + Fs;

#ifdef USE_SHADOWMAP
	float shadow = 1.0;

	if (ushadowmapEnabled != 0) {
		shadow = ComputeShadow( var_LightSpacePos );
	}

	out_color.rgb  = lightColor * reflectance * ( attenuation * NL * shadow );
#else
	const float shadow = 1.0;
	out_color.rgb  = lightColor * reflectance * ( attenuation * NL );
#endif

	out_color.rgb += ambientColor * diffuse.rgb;
	out_color.rgb += emissiveColor;

	vec3 light_contrib = CalcDynamicLightContribution( roughness, N, E, u_ViewOrigin.xyz, viewDir, NE, diffuse.rgb, specular.rgb, var_Normal.xyz );
	out_color.rgb += light_contrib;
	out_color.rgb += CalcIBLContribution( roughness, N, E, NE, specular.rgb * AO );

	out_color.a = diffuse.a;

	float opacity = SampleOpacity( mat, vTexCoord ).r;
	out_color.a *= opacity;

	if ( in_renderMode > 0 )
	{
		switch( in_renderMode )
		{
			case 1 : out_color.rgb = diffuse.rgb; break;
			case 2 : out_color.rgb = specular.rgb; break;		
			case 3 : out_color.rgb = vec3(roughness); break;
			case 4 : out_color.rgb = vec3(AO); break;			// Ambient Occlusion		
			case 5 : out_color.rgb = ( var_Normal.rgb * 0.5 + 0.5 ); break;		// Normals
			case 6 : out_color.rgb = ( N * 0.5 + 0.5 ); break;					// Normals + Normalmap
			case 7 : out_color.rgb = L; break;					// Lightdir
			case 8 : out_color.rgb = E; break;					// ViewDir
			case 9: out_color.rgb = var_Tangent.rgb; break;
			case 10 : out_color.rgb = lightColor; break;
			case 11 : out_color.rgb = ambientColor; break;
			case 12 : out_color.rgb = reflectance; break;
			case 13 : out_color.rgb = vec3(attenuation); break;
			case 14 : out_color.rgb = H; break;
			case 15 : out_color.rgb = Fd; break;
			case 16 : out_color.rgb = Fs; break;				
			case 17 : out_color.rgb = vec3(NE); break;
			case 18 : out_color.rgb = vec3(NL); break;
			case 19 : out_color.rgb = vec3(LH); break;
			case 20 : out_color.rgb = vec3(NH); break;
			case 21 : out_color.rgb = vec3(VH); break;
			case 22 : out_color.rgb = CalcIBLContribution( roughness, N, E, NE, specular.rgb * AO ); break;
			case 23 : out_color.rgb = emissiveColor; break;
			case 24 : out_color.rgb = vec3(opacity); break;
			case 25 : out_color.rgb = vec3(light_contrib); break;
			case 26 : out_color.rgb = vec3(u_ViewOrigin.xyz); break;
			case 27 : out_color.rgb = vec3(shadow); break;

		}
	}

	// debug
	//out_color.rgb = vec3(u_lights[0].color);
	//out_color = vec4(u_lights[0].radius, 0.0, 0.0, 1.0);
}