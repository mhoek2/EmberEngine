#version 330

#define PI 3.1415926535897932384626433832795

uniform sampler2D sTexture;
uniform sampler2D sNormal;
uniform sampler2D sPhyiscal;

in vec4 var_Tangent;
in vec4 var_BiTangent;
in vec4 var_Normal;
in vec4 var_LightDir;
in vec4 var_ViewDir;
in vec2 vTexCoord;

out vec4 out_color;

uniform int in_renderMode;

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

vec3 CalcNormal( in vec3 vertexNormal, in vec2 frag_tex_coord )
{
	//return normalize(vertexNormal);
	//if ( normal_texture_set > -1 ) {
		//vec3 n = texture(sNormal, frag_tex_coord).rgb - vec3(0.5);
		vec3 biTangent = 1.0 * cross(vertexNormal, var_Tangent.xyz);
		vec3 n = texture(sNormal, frag_tex_coord * 4).rgb - vec3(0.5);
		//n = normalize(n * 2.0 - 1.0);

		n.xy *= 1.0;
		n.z = sqrt(clamp((0.25 - n.x * n.x) - n.y * n.y, 0.0, 1.0));
		n = n.x * var_Tangent.rgb + n.y * biTangent + n.z * vertexNormal;
		//n = n.x * var_Tangent.rgb + n.y * var_BiTangent.rgb + n.z * vertexNormal;

		return normalize(n);
	/*}
	
	else
		return normalize(vertexNormal);*/

}

void main(){
	vec4 diffuse;
	float attenuation;
	vec3 viewDir, lightColor, ambientColor;
	vec3 L, N, E;

	vec4 base = texture2D(sTexture, vTexCoord * 4);

	viewDir = var_ViewDir.xyz;
	E = normalize(viewDir);

	L = var_LightDir.xyz;
	float sqrLightDist = dot(L, L);
	L /= sqrt(sqrLightDist);

	lightColor = vec3(1.0, 1.0, 1.0);
	ambientColor = vec3(0.3, 0.3, 0.2);
	diffuse = base;
	attenuation = 1.0;

	N = CalcNormal( var_Normal.xyz, vTexCoord );	

	lightColor *= PI;

	//ambientColor = lightColor;
	//float surfNL = clamp(dot(var_Normal.xyz, L), 0.0, 1.0);
	//lightColor /= max( surfNL, 0.25 );
	//ambientColor = max( ambientColor - lightColor * surfNL, 0.0 );
	
	vec4 specular = vec4( 1.0 );
	float roughness = 0.99;
	float AO = 1.0;

	const vec4 specularScale = vec4( 1.0, 1.0, 1.0, 0.5 );

	// metallic roughness workflow
	vec4 ORMS = texture( sPhyiscal, vTexCoord * 4 ).brga;
	ORMS.xyzw *= specularScale.zwxy;

	specular.rgb = mix(vec3(0.08) * ORMS.w, diffuse.rgb, ORMS.z);
	diffuse.rgb *= vec3(1.0 - ORMS.z);

	roughness = mix(0.01, 1.0, ORMS.y);
	AO = min(ORMS.x, AO);


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

	out_color.rgb  = lightColor * reflectance * ( attenuation * NL );
	out_color.rgb += ambientColor * diffuse.rgb;

	if ( in_renderMode > 0 )
	{
		switch( in_renderMode )
		{
			case 1: out_color.rgb = base.rgb; break;
			case 2 : out_color.rgb = specular.rgb; break;		
			case 3 : out_color.rgb = vec3(roughness); break;
			case 4 : out_color.rgb = vec3(AO); break;
			case 5: out_color.rgb = ( var_Normal.rgb * 0.5 + 0.5 ); break;
			case 6: out_color.rgb = ( N.rgb * 0.5 + 0.5 ); break;
			case 7: out_color.rgb = var_Tangent.rgb; break;
			case 8: out_color.rgb = L.rgb; break;
			//case 9: out_color.rgb = E.rgb; break;s
			//case 9: out_color.rgb = E.rgb; break;s
			case 9: out_color.rgb = reflectance.rgb; break;
		}
	}

	out_color.a = diffuse.a;
}