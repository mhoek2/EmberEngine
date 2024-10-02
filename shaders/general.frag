uniform sampler2D sTexture;
varying vec2 vTexCoord;

void main(){
    gl_FragColor = texture2D(sTexture, vTexCoord);
    //gl_FragColor = vec4(1.0);
}