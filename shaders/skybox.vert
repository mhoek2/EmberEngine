#version 330 core

uniform mat4 uMMatrix;	// not required, keep for shader uniform location compat with general shader
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;
 
layout(location = 0) in vec3 aVertex;

out vec3 vTexCoord;

void main()
{
	//vec4 pos = uPMatrix * uVMatrix * vec4( aVertex, 1.0 );
	//gl_Position = vec4( pos.x, pos.y, pos.w, pos.w );
	//vTexCoord = vec3(aVertex.x, aVertex.y, -aVertex.z);

    vTexCoord = aVertex;
    gl_Position = ( uPMatrix * uVMatrix ) * vec4( -aVertex, 1.0 );
}