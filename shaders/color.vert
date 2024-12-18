#version 330 core

uniform mat4 uMMatrix;
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

uniform vec4 uColor;

layout(location = 0) in vec3 aVertex;

out vec4 var_Color;

void main()
{
    gl_Position = ( uPMatrix * uVMatrix ) * vec4( aVertex, 1.0 );
	var_Color = uColor;
} 