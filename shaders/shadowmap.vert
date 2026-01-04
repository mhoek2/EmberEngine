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
    layout(std430, binding = 0) readonly buffer DrawBuffer { DrawBlock draw[]; };
#endif

void main()
{
#ifdef USE_INDIRECT
	DrawBlock d = draw[gl_BaseInstance + gl_InstanceID];
    mat4 uMMatrix = d.model;
#endif

    gl_Position = uPMatrix * uVMatrix * uMMatrix * vec4(aVertex, 1.0);
}