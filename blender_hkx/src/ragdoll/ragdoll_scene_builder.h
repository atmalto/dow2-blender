#ifndef DOW2_RAGDOLL_WORKSPACE_RAGDOLL_SCENE_BUILDER_H
#define DOW2_RAGDOLL_WORKSPACE_RAGDOLL_SCENE_BUILDER_H

#include "json_ragdoll_input.h"

#include <vector>

class hkaAnimationContainer;
class hkaRagdollInstance;
class hkaSkeleton;
class hkaSkeletonMapper;
class hkpConstraintInstance;
class hkpPhysicsData;
class hkpPhysicsSystem;
class hkpPositionConstraintMotor;
class hkpRigidBody;
class hkpShape;

struct RagdollBuildResult
{
	hkaAnimationContainer* animationContainer;
	hkaSkeleton* animationSkeleton;
	hkaSkeleton* ragdollSkeleton;
	hkaSkeletonMapper* ragdollToAnimationMapper;
	hkaSkeletonMapper* animationToRagdollMapper;
	hkaRagdollInstance* ragdollInstance;
	hkpPhysicsSystem* physicsSystem;
	hkpPhysicsData* physicsData;
	hkpPositionConstraintMotor* sharedMotor;
	std::vector<hkpRigidBody*> rigidBodies;
	std::vector<hkpConstraintInstance*> constraints;
	std::vector<hkpShape*> shapes;
	std::vector<char*> stringStorage;

	RagdollBuildResult();
};

bool buildRagdollScene(const ragdoll_io::RawRagdollData& rawData, RagdollBuildResult& result);

#endif