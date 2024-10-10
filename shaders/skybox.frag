#version 330 core

uniform samplerCube sEnvironment;

in vec3 vTexCoord;

out vec4 out_color;

void main()
{
	out_color = texture( sEnvironment, vTexCoord );
	//out_color = vec4(1.0, 0.0, 0.0, 1.0);
}