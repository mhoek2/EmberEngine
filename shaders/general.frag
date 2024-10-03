#version 330

uniform sampler2D sTexture;

in vec3 viewDir;
in vec2 vTexCoord;

out vec4 out_Color;

void main(){
    //gl_FragColor = texture2D(sTexture, vTexCoord);
    //gl_FragColor = vec4(1.0);
    out_Color = texture2D(sTexture, vTexCoord);;
    //out_Color = vec4(1.0);
}