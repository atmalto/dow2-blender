#ifndef DOW2_PHYSICS_SCENE_BUILDER_H
#define DOW2_PHYSICS_SCENE_BUILDER_H

#include <vector>

#include "json_physics_input.h"

class hkRootLevelContainer;
class hkpPhysicsData;

struct PhysicsBuildResult
{
	hkpPhysicsData* physicsData;
	hkRootLevelContainer* rootContainer;
	std::vector<char*> ownedStrings;

	PhysicsBuildResult();
	~PhysicsBuildResult();

private:
	PhysicsBuildResult(const PhysicsBuildResult&);
	PhysicsBuildResult& operator=(const PhysicsBuildResult&);
};

bool buildPhysicsScene(
	const std::vector<RawPhysicsSystem>& systems,
	PhysicsBuildResult& output);

#endif