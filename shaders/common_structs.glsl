struct ObjectBlock
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
	int  material;
	vec4 min_aabb;
	vec4 max_aabb;
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

struct PhysicBlock
{
	mat4 visual_model;	// 64 bytes
};

struct GameObjectBlock
{
	mat4 model;			// 64 bytes
	int  model_index;	// 4 bytes
	int  enabled;
	int  physic_visual; // wheter to compose using physic visual model
	int  pad2;
};

struct InstancesBlock
{
	uint ObjectId;
	uint pad0;
	uint pad1;
	uint pad2;
};

struct IndirectBlock
{
	uint count;    
	uint instanceCount;    
	uint firstIndex;    
	int baseVertex;    
	uint baseInstance;
};