uniform mat4 uMMatrix;
uniform mat4 uVMatrix;
uniform mat4 uPMatrix;
       
attribute vec3 aVertex;
attribute vec3 aNormal;
attribute vec2 aTexCoord;
    
varying vec2 vTexCoord;
    
void main(){
    vTexCoord = aTexCoord;
    // Make GL think we are actually using the normal
    aNormal;
    gl_Position = (uPMatrix * uVMatrix * uMMatrix) * vec4(aVertex, 1.0);
}