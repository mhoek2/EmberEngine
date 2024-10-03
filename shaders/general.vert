#version 330

uniform mat4 uMMatrix;
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

uniform vec4 u_ViewOrigin;
uniform vec4 in_lightdir;
       
layout(location = 0) in vec3 aVertex;
layout(location = 1) in vec2 aTexCoord;    
layout(location = 2) in vec3 aNormal;

out vec2 vTexCoord;

out vec4 var_Normal;
out vec4 var_LightDir;
out vec4 var_ViewDir;
  
void main(){
    vTexCoord = aTexCoord;

	vec3 position = aVertex;
	vec3 normal = normalize(aNormal);

    gl_Position = (uPMatrix * uVMatrix * uMMatrix) * vec4(position, 1.0);

	position	= (uMMatrix * vec4(position, 1.0)).xyz;
	normal		= normalize(mat3(uMMatrix) * normal);
	
	vec3 L	= in_lightdir.xyz * 2.0 - vec3(1.0);
	L		= ( uMMatrix * vec4( L, 0.0 ) ).xyz;
	L		= normalize( ( L * 0.5 ) + vec3( 0.5 ) );
	
	vec3 viewDir = u_ViewOrigin.xyz - vec3(0.0, 1.0, 5.0);

	var_LightDir	= vec4(L, 0.0);	
	var_Normal		= vec4(normal, 0.0);
	var_ViewDir		= vec4(viewDir, 0.0);
}