#ifndef DOW2_RAGDOLL_WORKSPACE_JSON_RAGDOLL_INPUT_H
#define DOW2_RAGDOLL_WORKSPACE_JSON_RAGDOLL_INPUT_H

#include <string>
#include <vector>

namespace ragdoll_io
{
	struct RawTransform
	{
		float pos[3];
		float rot[4];
		float scale[3];
	};

	struct RawSkeleton
	{
		std::string name;
		std::vector<std::string> bones;
		std::vector<int> parentIndices;
		std::vector<RawTransform> referencePose;
	};

	struct RawBoneMapping
	{
		int ragdollBone;
		int animBone;
		RawTransform transform;
	};

	struct RawRigidBody
	{
		std::string name;
		int boneIndex;
		std::string shapeType;
		float radius;
		float vertexA[3];
		float vertexB[3];
		float halfExtents[3];
		float mass;
		float friction;
		float restitution;
		std::string motionType;
		float position[4];
		float rotation[4];
		float linearDamping;
		float angularDamping;
		int collisionFilterInfo;
		int qualityType;
		// Optional local-space offset of the collision shape from the body origin.
		// Non-zero for bodies whose primitive is offset from the joint (shipped as
		// a convex-translate wrapper). Keeps the joint frame + mass centre at the
		// body origin while placing the collision shape at the offset.
		float shapeOffset[3];
	};

	struct RawConstraint
	{
		std::string name;
		std::string constraintType;
		int bodyAIndex;
		int bodyBIndex;
		float pivotA[3];
		float pivotB[3];
		float twistAxisA[3];
		float twistAxisB[3];
		float planeAxisA[3];
		float planeAxisB[3];
		float twistMin;
		float twistMax;
		float coneAngle;
		float planeMin;
		float planeMax;
		float hingeMin;
		float hingeMax;
		float frictionTorque;
	};

	struct RawRagdollData
	{
		RawSkeleton animSkeleton;
		RawSkeleton ragdollSkeleton;
		std::vector<RawBoneMapping> boneMappings;
		std::vector<RawRigidBody> rigidBodies;
		std::vector<RawConstraint> constraints;
	};

	bool parseJSON(const char* filename, RawRagdollData& data);
}

#endif