// version added programmatically

#ifndef USE_INDIRECT
uniform mat4 uMMatrix;
#endif

uniform mat4 uVMatrix;
uniform mat4 uPMatrix;

layout(location = 0) in vec3 aVertex;

#ifdef USE_INDIRECT
    struct DrawBlock
    {
        mat4 model;        // 64 bytes
        int  material;
        int  pad0;
        int  pad1;
        int  pad2;
    };

    layout(std430, binding = 0) readonly buffer DrawBuffer
    {
        DrawBlock draw[];
    };
#endif

void main()
{
#ifdef USE_INDIRECT
    DrawBlock d = draw[gl_BaseInstance];
    mat4 uMMatrix = d.model;
#endif

    gl_Position = uPMatrix * uVMatrix * uMMatrix * vec4(aVertex, 1.0);
}