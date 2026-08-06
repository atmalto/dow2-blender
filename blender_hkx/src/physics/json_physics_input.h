#ifndef DOW2_PHYSICS_JSON_INPUT_H
#define DOW2_PHYSICS_JSON_INPUT_H

#include <string>
#include <vector>

struct RawVertex
{
	float x;
	float y;
	float z;
};

struct RawRigidBody
{
	std::string name;
	std::vector<RawVertex> vertices;
	float position[3];
	float rotation[4];
	float friction;
	float restitution;
	std::string motionType;
	int qualityType;
	float allowedPenetrationDepth;
	int processContactCallbackDelay;
	int deactivationClass;
	int deactivationIntegrateCounter;
	float linearDamping;
	float angularDamping;
	float maxLinearVelocity;
	float maxAngularVelocity;
	unsigned int collisionFilterInfo;
	int eventFilter;
	int userFilter;
	float mass;
	std::string centerOfMassMode;
	float centerOfMassOverride[3];
	float shapeRadius;
	std::string responseType;
	bool deactivatorPresent;

	RawRigidBody()
		: friction(0.5f),
		  restitution(0.4f),
		  motionType("FIXED"),
		  qualityType(1),
		  allowedPenetrationDepth(0.0f),
		  processContactCallbackDelay(0xffff),
		  deactivationClass(1),
		  deactivationIntegrateCounter(255),
		  linearDamping(0.0f),
		  angularDamping(0.05f),
		  maxLinearVelocity(200.0f),
		  maxAngularVelocity(200.0f),
		  collisionFilterInfo(0),
		  eventFilter(0),
		  userFilter(0),
		  mass(0.0f),
		  centerOfMassMode("ZERO"),
		  shapeRadius(0.05f),
		  responseType("RESPONSE_SIMPLE_CONTACT"),
		  deactivatorPresent(false)
	{
		position[0] = position[1] = position[2] = 0.0f;
		rotation[0] = rotation[1] = rotation[2] = 0.0f;
		rotation[3] = 1.0f;
		centerOfMassOverride[0] = centerOfMassOverride[1] = centerOfMassOverride[2] = 0.0f;
	}
};

struct RawPhysicsSystem
{
	std::string name;
	std::vector<RawRigidBody> rigidBodies;
};

bool parsePhysicsJson(const char* filename, std::vector<RawPhysicsSystem>& systems);

#endif