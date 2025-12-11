#version 330 core

uniform mat4 uMMatrix;	// not required, keep for shader uniform location compat with general shader
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;
 
uniform bool uExtractCubemap;

layout(location = 0) in vec3 aVertex;

out vec3 vTexCoord;

void main()
{
    vTexCoord = aVertex;

    // for cubemap extraction (not realtime), flip the x handedness
    vTexCoord.x = uExtractCubemap ? -vTexCoord.x : vTexCoord.x;

    gl_Position = ( uPMatrix * uVMatrix ) * vec4( aVertex, 1.0 );
}