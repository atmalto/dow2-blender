#include "physics_scene_builder.h"

#include <stdio.h>
#include <string.h>

#include <Common/Base/hkBase.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Common/Base/Types/Geometry/hkGeometry.h>
#include <Common/Base/Types/Geometry/hkStridedVertices.h>

#include <Physics/Utilities/Serialize/hkpPhysicsData.h>
#include <Physics/Dynamics/World/hkpPhysicsSystem.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>
#include <Physics/Internal/PreProcess/ConvexHull/hkpGeometryUtility.h>
#include <Physics/Utilities/Dynamics/Inertia/hkpInertiaTensorComputer.h>

namespace
{
	char* duplicateString(const char* text)
	{
		const size_t length = strlen(text);
		char* copy = new char[length + 1];
		memcpy(copy, text, length + 1);
		return copy;
	}

	hkpMotion::MotionType getMotionType(const std::string& type)
	{
		if (type == "DYNAMIC" || type == "MOTION_DYNAMIC")
		{
			return hkpMotion::MOTION_DYNAMIC;
		}
		if (type == "KEYFRAMED" || type == "MOTION_KEYFRAMED")
		{
			return hkpMotion::MOTION_KEYFRAMED;
		}
		if (type == "SPHERE_INERTIA" || type == "MOTION_SPHERE_INERTIA")
		{
			return hkpMotion::MOTION_SPHERE_INERTIA;
		}
		if (type == "BOX_INERTIA" || type == "MOTION_BOX_INERTIA")
		{
			return hkpMotion::MOTION_BOX_INERTIA;
		}
		return hkpMotion::MOTION_FIXED;
	}

	hkpMaterial::ResponseType getResponseType(const std::string& type)
	{
		if (type == "RESPONSE_REPORTING")
		{
			return hkpMaterial::RESPONSE_REPORTING;
		}
		if (type == "RESPONSE_NONE")
		{
			return hkpMaterial::RESPONSE_NONE;
		}
		return hkpMaterial::RESPONSE_SIMPLE_CONTACT;
	}
}

PhysicsBuildResult::PhysicsBuildResult()
	: physicsData(0),
	  rootContainer(0)
{
}

PhysicsBuildResult::~PhysicsBuildResult()
{
	for (size_t i = 0; i < ownedStrings.size(); ++i)
	{
		delete[] ownedStrings[i];
	}
	ownedStrings.clear();
}

bool buildPhysicsScene(
	const std::vector<RawPhysicsSystem>& systems,
	PhysicsBuildResult& output)
{
	if (systems.empty())
	{
		fprintf(stderr, "Error: no physics systems were provided\n");
		return false;
	}

	output.physicsData = new hkpPhysicsData();

	for (size_t sysIdx = 0; sysIdx < systems.size(); ++sysIdx)
	{
		const RawPhysicsSystem& rawSystem = systems[sysIdx];
		printf(
			"Creating physics system %d: %s (%d bodies)\n",
			(int)sysIdx,
			rawSystem.name.c_str(),
			(int)rawSystem.rigidBodies.size());

		hkpPhysicsSystem* physicsSystem = new hkpPhysicsSystem();
		char* systemName = duplicateString(rawSystem.name.c_str());
		output.ownedStrings.push_back(systemName);
		physicsSystem->setName(systemName);

		for (size_t bodyIdx = 0; bodyIdx < rawSystem.rigidBodies.size(); ++bodyIdx)
		{
			const RawRigidBody& rawBody = rawSystem.rigidBodies[bodyIdx];
			printf(
				"  Creating rigid body %d: %s (%d vertices)\n",
				(int)bodyIdx,
				rawBody.name.c_str(),
				(int)rawBody.vertices.size());

			char* bodyName = duplicateString(rawBody.name.c_str());
			output.ownedStrings.push_back(bodyName);

			hkArray<hkVector4> vertices;
			vertices.setSize((int)rawBody.vertices.size());
			for (size_t vertexIdx = 0; vertexIdx < rawBody.vertices.size(); ++vertexIdx)
			{
				vertices[(int)vertexIdx].set(
					rawBody.vertices[vertexIdx].x,
					rawBody.vertices[vertexIdx].y,
					rawBody.vertices[vertexIdx].z);
			}

			hkStridedVertices stridedVertices;
			stridedVertices.m_numVertices = vertices.getSize();
			stridedVertices.m_striding = sizeof(hkVector4);
			stridedVertices.m_vertices = &vertices[0](0);

			hkGeometry geometry;
			hkArray<hkVector4> planeEquations;
			hkpGeometryUtility::createConvexGeometry(stridedVertices, geometry, planeEquations);

			printf(
				"    Convex hull: %d vertices, %d planes\n",
				geometry.m_vertices.getSize(),
				planeEquations.getSize());

			hkStridedVertices hullVertices;
			hullVertices.m_numVertices = geometry.m_vertices.getSize();
			hullVertices.m_striding = sizeof(hkVector4);
			hullVertices.m_vertices = &geometry.m_vertices[0](0);

			hkpConvexVerticesShape* shape = new hkpConvexVerticesShape(hullVertices, planeEquations, rawBody.shapeRadius);

			hkpRigidBodyCinfo info;
			info.m_shape = shape;
			info.m_position.set(rawBody.position[0], rawBody.position[1], rawBody.position[2]);
			info.m_rotation.set(rawBody.rotation[0], rawBody.rotation[1], rawBody.rotation[2], rawBody.rotation[3]);
			info.m_collisionFilterInfo = rawBody.collisionFilterInfo;
			info.m_collisionResponse = getResponseType(rawBody.responseType);
			info.m_processContactCallbackDelay = (hkUint16)rawBody.processContactCallbackDelay;
			info.m_friction = rawBody.friction;
			info.m_restitution = rawBody.restitution;
			info.m_motionType = getMotionType(rawBody.motionType);
			info.m_qualityType = (hkpCollidableQualityType)rawBody.qualityType;
			info.m_linearDamping = rawBody.linearDamping;
			info.m_angularDamping = rawBody.angularDamping;
			info.m_maxLinearVelocity = rawBody.maxLinearVelocity;
			info.m_maxAngularVelocity = rawBody.maxAngularVelocity;
			info.m_allowedPenetrationDepth = rawBody.allowedPenetrationDepth;

			if (info.m_motionType == hkpMotion::MOTION_FIXED)
			{
				info.m_mass = 0.0f;
				info.m_centerOfMass.setZero4();
			}
			else
			{
				hkpMassProperties massProperties;
				const hkReal targetMass = rawBody.mass > 0.0f ? rawBody.mass : 5.0f;
				hkpInertiaTensorComputer::computeShapeVolumeMassProperties(shape, targetMass, massProperties);
				info.m_mass = massProperties.m_mass;
				info.m_inertiaTensor = massProperties.m_inertiaTensor;
				if (rawBody.centerOfMassMode == "CUSTOM")
				{
					info.m_centerOfMass.set(rawBody.centerOfMassOverride[0], rawBody.centerOfMassOverride[1], rawBody.centerOfMassOverride[2]);
				}
				else if (rawBody.centerOfMassMode == "ZERO")
				{
					info.m_centerOfMass.setZero4();
				}
				else
				{
					info.m_centerOfMass = massProperties.m_centerOfMass;
				}
			}

			hkpRigidBody* rigidBody = new hkpRigidBody(info);
			rigidBody->setName(bodyName);
			rigidBody->m_spuCollisionCallback.m_eventFilter = (hkUint8)rawBody.eventFilter;
			rigidBody->m_spuCollisionCallback.m_userFilter = (hkUint8)rawBody.userFilter;
			hkpMotion* motion = rigidBody->getMotion();
			if (motion != HK_NULL)
			{
				motion->m_deactivationIntegrateCounter = (hkUint8)rawBody.deactivationIntegrateCounter;
				hkMotionState* motionState = motion->getMotionState();
				if (motionState != HK_NULL)
				{
					motionState->m_linearDamping = rawBody.linearDamping;
					motionState->m_angularDamping = rawBody.angularDamping;
					motionState->m_maxLinearVelocity = rawBody.maxLinearVelocity;
					motionState->m_maxAngularVelocity = rawBody.maxAngularVelocity;
					motionState->m_deactivationClass = (hkUint8)rawBody.deactivationClass;
				}
			}
			physicsSystem->addRigidBody(rigidBody);

			rigidBody->removeReference();
			shape->removeReference();
		}

		output.physicsData->addPhysicsSystem(physicsSystem);
		physicsSystem->removeReference();
	}

	printf("Creating root container...\n");
	output.rootContainer = new hkRootLevelContainer();
	output.rootContainer->m_namedVariants = hkAllocate<hkRootLevelContainer::NamedVariant>(1, HK_MEMORY_CLASS_SERIALIZE);
	output.rootContainer->m_numNamedVariants = 1;
	output.rootContainer->m_namedVariants[0].set("Physics Data", output.physicsData, &hkpPhysicsDataClass);
	return true;
}