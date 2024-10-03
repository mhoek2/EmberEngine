#version 330

#define PI 3.1415926535897932384626433832795

uniform sampler2D sTexture;

in vec4 var_Normal;
in vec4 var_LightDir;
in vec4 var_ViewDir;
in vec2 vTexCoord;

out vec4 out_Color;


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




void main(){
	vec4 diffuse;
	float attenuation;
	vec3 viewDir, lightColor, ambientColor;
	vec3 L, N, E;

	vec4 base = texture2D(sTexture, vTexCoord);

	viewDir = var_ViewDir.xyz;
	E = normalize(viewDir);

	L = var_LightDir.xyz;
	float sqrLightDist = dot(L, L);
	L /= sqrt(sqrLightDist);

	lightColor = vec3(1.0, 0.0, 0.0);
	ambientColor = vec3(0.5, 0.5, 0.5);
	diffuse = base;
	attenuation = 1.0;

	lightColor *= PI;

	vec4 specular = vec4( 0.9 );
	float roughness = 0.5;
	float AO = 1.0;

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

	vec3 reflectance = Fd + Fs;

	out_Color.rgb  = lightColor * reflectance * ( attenuation * NL );
	out_Color.rgb += ambientColor * diffuse.rgb;
	
	out_Color.rgb = var_Normal.rgb;

	out_Color.a = diffuse.a;
}