// version added programmicly

#extension GL_ARB_shading_language_include : require

#ifdef USE_INDIRECT
#include "common_structs.glsl"
#endif

#ifndef USE_INDIRECT
uniform mat4 uMMatrix;
#endif
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;
#ifdef USE_SHADOWMAP
uniform mat4 uLightPMatrix;
uniform mat4 uLightVMatrix;
#endif
uniform vec4 u_ViewOrigin;

uniform vec4 in_lightdir;
uniform vec4 in_lightcolor;
uniform vec4 in_ambientcolor;

uniform float in_roughnessOverride;
uniform float in_metallicOverride;
#ifndef USE_INDIRECT
uniform int u_MaterialIndex;
#endif

layout(location = 0) in vec3 aVertex;
layout(location = 1) in vec2 aTexCoord;    
layout(location = 2) in vec3 aNormal;
layout(location = 3) in vec3 aTangent;
layout(location = 4) in vec3 aBiTangent;

out vec2 vTexCoord;
out float var_roughnessOverride;
out float var_metallicOverride;

out vec4 var_Tangent;
out vec4 var_BiTangent;
out vec4 var_Normal;
out vec4 var_LightDir;
out vec4 var_ViewDir;

#ifdef USE_SHADOWMAP
	out vec4 var_LightSpacePos;
#endif

out vec4 var_LightColor;
out vec4 var_AmbientColor;
flat out int var_material_index;

#ifdef USE_INDIRECT
	layout(std430, binding = 9) readonly buffer InstancesBuffer { InstancesBlock instance[]; };
	layout(std430, binding = 13) readonly buffer ObjectBuffer { ObjectBlock object[]; };
#endif

void main(){
    vTexCoord = aTexCoord;

	vec3 position = aVertex;
	vec3 normal = normalize(aNormal);

#ifdef USE_INDIRECT
	ObjectBlock d = object[instance[gl_BaseInstance + gl_InstanceID].ObjectId];
	mat4 uMMatrix = d.model;
#endif

    gl_Position = (uPMatrix * uVMatrix * uMMatrix) * vec4(position, 1.0);

	position	= (uMMatrix * vec4(position, 1.0)).xyz;
	normal		= normalize(mat3(uMMatrix) * normal);
	
	vec3 tangent	= normalize(mat3(uMMatrix) * aTangent);
	vec3 bitangent	= normalize(mat3(uMMatrix) * aBiTangent);

	vec3 L = normalize(in_lightdir.xyz);

	vec3 viewDir = u_ViewOrigin.xyz - position;

	var_LightDir	= vec4(L, 0.0);	
	var_Normal		= vec4(normal, 0.0);
	var_Tangent		= vec4(tangent, 0.0 );
	var_BiTangent   = vec4(bitangent, 0.0 );
	var_ViewDir		= vec4(viewDir, 0.0);

	var_LightColor		= in_lightcolor;
	var_AmbientColor	= in_ambientcolor;

	var_roughnessOverride = in_roughnessOverride;
	var_metallicOverride = in_metallicOverride;

#ifdef USE_SHADOWMAP
	vec4 worldPos = uMMatrix * vec4(aVertex, 1.0);
	var_LightSpacePos = uLightPMatrix * uLightVMatrix * worldPos;
#endif

#ifdef USE_INDIRECT
	var_material_index = int(d.material);
#else
	var_material_index = u_MaterialIndex;
#endif
}