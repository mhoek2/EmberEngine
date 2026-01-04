struct DrawBlock
{
	mat4 model;        // 64 bytes
	int  material;     // 4 bytes
	int  meshNodeMatrixId;
	int  gameObjectMatrixId;
	int  pad2;
};

struct MeshNodeBlock
{
	mat4 model;        // 64 bytes
	int  num_indices;     // 4 bytes
	int  firstIndex;
	int  baseVertex;
	int  pad2;
};

struct BatchBlock
{
	int instanceCount;
	int baseInstance;
	int meshNodeMatrixId;
	int pad1;
};

struct ModelBlock
{
    uint nodeOffset;    // start index in MeshNodeBuffer
    uint nodeCount;     // how many nodes per model
	int  pad0;
	int  pad1;
};

struct GameObjectBlock
{
	mat4 model;        // 64 bytes
	int  model_index;     // 4 bytes
	int  enabled;
	int  pad1;
	int  pad2;
};

struct InstancesBlock
{
	uint gameObjectId;
	uint meshNodeMatrixId;
	uint pad0;
	uint pad1;
};

struct IndirectBlock
{
	uint count;    
	uint instanceCount;    
	uint firstIndex;    
	int baseVertex;    
	uint baseInstance;    

};