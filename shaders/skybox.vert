#version 330 core

uniform mat4 uMMatrix;	// not required, keep for shader uniform location compat with general shader
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;
 
layout(location = 0) in vec3 aVertex;

out vec3 vTexCoord;

void main()
{
    vTexCoord = vec3(
        -aVertex.x,
        aVertex.y,
        -aVertex.z
    );

    gl_Position = ( uPMatrix * uVMatrix ) * vec4( -aVertex, 1.0 );
}