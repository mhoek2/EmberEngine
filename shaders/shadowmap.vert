// version added programmatically

#extension GL_ARB_shading_language_include : require

#ifdef USE_INDIRECT
#include "common_structs.glsl"
#endif

#ifndef USE_INDIRECT
uniform mat4 uMMatrix;
#endif

uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

layout(location = 0) in vec3 aVertex;

#ifdef USE_INDIRECT
	layout(std430, binding = 0) readonly buffer ObjectBuffer	{ ObjectBlock object[]; };
	layout(std430, binding = 9) readonly buffer InstancesBuffer { InstancesBlock instance[]; };
#endif

void main()
{
#ifdef USE_INDIRECT
	ObjectBlock d = object[instance[gl_BaseInstance + gl_InstanceID].ObjectId];
    mat4 uMMatrix = d.model;
#endif

    gl_Position = uPMatrix * uVMatrix * uMMatrix * vec4(aVertex, 1.0);
}