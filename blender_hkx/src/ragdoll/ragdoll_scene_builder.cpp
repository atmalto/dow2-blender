#include "ragdoll_scene_builder.h"

#include <stdio.h>
#include <string.h>

#include <Animation/Animation/Mapper/hkaSkeletonMapper.h>
#include <Animation/Animation/Mapper/hkaSkeletonMapperData.h>
#include <Animation/Animation/Rig/hkaBone.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>
#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>
#include <Common/Base/hkBase.h>
#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/Capsule/hkpCapsuleShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Dynamics/Constraint/Bilateral/LimitedHinge/hkpLimitedHingeConstraintData.h>
#include <Physics/Dynamics/Constraint/Bilateral/Ragdoll/hkpRagdollConstraintData.h>
#include <Physics/Dynamics/Constraint/Motor/Position/hkpPositionConstraintMotor.h>
#include <Physics/Dynamics/Constraint/hkpConstraintInstance.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/Entity/hkpRigidBodyCinfo.h>
#include <Physics/Dynamics/World/hkpPhysicsSystem.h>
#include <Physics/Utilities/Dynamics/Inertia/hkpInertiaTensorComputer.h>
#include <Physics/Utilities/Serialize/hkpPhysicsData.h>

using namespace ragdoll_io;

namespace
{
	char* duplicateString(const std::string& value, std::vector<char*>& storage)
	{
		char* copy = new char[value.length() + 1];
		strcpy(copy, value.c_str());
		storage.push_back(copy);
		return copy;
	}

	hkaSkeleton* createSkeleton(const RawSkeleton& raw, std::vector<char*>& storage)
	{
		const int numBones = static_cast<int>(raw.bones.size());
		hkaSkeleton* skeleton = new hkaSkeleton();
		skeleton->m_name = duplicateString(raw.name, storage);

		skeleton->m_parentIndices = hkAllocate<hkInt16>(numBones, HK_MEMORY_CLASS_ANIMATION);
		skeleton->m_numParentIndices = numBones;
		for (int index = 0; index < numBones; ++index)
		{
			skeleton->m_parentIndices[index] = static_cast<hkInt16>(raw.parentIndices[index]);
		}

		skeleton->m_bones = hkAllocate<hkaBone*>(numBones, HK_MEMORY_CLASS_ANIMATION);
		skeleton->m_numBones = numBones;
		for (int index = 0; index < numBones; ++index)
		{
			hkaBone* bone = new hkaBone();
			bone->m_name = duplicateString(raw.bones[index], storage);
			bone->m_lockTranslation = (index > 0);
			skeleton->m_bones[index] = bone;
		}

		skeleton->m_referencePose = hkAllocate<hkQsTransform>(numBones, HK_MEMORY_CLASS_ANIMATION);
		skeleton->m_numReferencePose = numBones;
		for (int index = 0; index < numBones; ++index)
		{
			const RawTransform& transform = raw.referencePose[index];
			skeleton->m_referencePose[index].setTranslation(hkVector4(transform.pos[0], transform.pos[1], transform.pos[2]));
			skeleton->m_referencePose[index].setRotation(hkQuaternion(transform.rot[0], transform.rot[1], transform.rot[2], transform.rot[3]));
			skeleton->m_referencePose[index].setScale(hkVector4(transform.scale[0], transform.scale[1], transform.scale[2]));
		}

		skeleton->m_floatSlots = HK_NULL;
		skeleton->m_numFloatSlots = 0;
		return skeleton;
	}

	hkaSkeletonMapper* createSkeletonMapper(
		const hkaSkeleton* skeletonA,
		const hkaSkeleton* skeletonB,
		const std::vector<RawBoneMapping>& mappings,
		bool ragdollToAnimation)
	{
		hkaSkeletonMapperData mapperData;
		mapperData.m_skeletonA = skeletonA;
		mapperData.m_skeletonB = skeletonB;
		mapperData.m_keepUnmappedLocal = true;

		const int numMappings = static_cast<int>(mappings.size());
		if (numMappings > 0)
		{
			mapperData.m_simpleMappings.setSize(numMappings);
			for (int index = 0; index < numMappings; ++index)
			{
				const RawBoneMapping& raw = mappings[index];
				hkaSkeletonMapperData::SimpleMapping& mapping = mapperData.m_simpleMappings[index];
				mapping.m_boneA = static_cast<hkInt16>(ragdollToAnimation ? raw.ragdollBone : raw.animBone);
				mapping.m_boneB = static_cast<hkInt16>(ragdollToAnimation ? raw.animBone : raw.ragdollBone);
				mapping.m_aFromBTransform.setTranslation(hkVector4(raw.transform.pos[0], raw.transform.pos[1], raw.transform.pos[2]));
				mapping.m_aFromBTransform.setRotation(hkQuaternion(raw.transform.rot[0], raw.transform.rot[1], raw.transform.rot[2], raw.transform.rot[3]));
				mapping.m_aFromBTransform.setScale(hkVector4(raw.transform.scale[0], raw.transform.scale[1], raw.transform.scale[2]));
			}
		}

		return new hkaSkeletonMapper(mapperData);
	}

	hkpShape* createShape(const RawRigidBody& raw)
	{
		if (raw.shapeType == "sphere")
		{
			return new hkpSphereShape(raw.radius);
		}

		if (raw.shapeType == "box")
		{
			return new hkpBoxShape(hkVector4(raw.halfExtents[0], raw.halfExtents[1], raw.halfExtents[2]), 0.0f);
		}

		return new hkpCapsuleShape(
			hkVector4(raw.vertexA[0], raw.vertexA[1], raw.vertexA[2]),
			hkVector4(raw.vertexB[0], raw.vertexB[1], raw.vertexB[2]),
			raw.radius);
	}

	hkpRigidBody* createRigidBody(const RawRigidBody& raw, std::vector<char*>& storage, hkpShape*& shapeOut)
	{
		shapeOut = createShape(raw);

		hkpRigidBodyCinfo info;
		info.m_shape = shapeOut;
		if (raw.motionType == "MOTION_DYNAMIC")
		{
			info.m_motionType = hkpMotion::MOTION_DYNAMIC;
		}
		else if (raw.motionType == "MOTION_SPHERE_INERTIA")
		{
			info.m_motionType = hkpMotion::MOTION_SPHERE_INERTIA;
		}
		else if (raw.motionType == "MOTION_KEYFRAMED")
		{
			info.m_motionType = hkpMotion::MOTION_KEYFRAMED;
		}
		else
		{
			info.m_motionType = hkpMotion::MOTION_BOX_INERTIA;
		}

		info.m_position.set(raw.position[0], raw.position[1], raw.position[2]);
		info.m_rotation.set(raw.rotation[0], raw.rotation[1], raw.rotation[2], raw.rotation[3]);
		hkpMassProperties massProperties;
		const hkReal targetMass = raw.mass > 0.0f ? raw.mass : 5.0f;
		hkpInertiaTensorComputer::computeShapeVolumeMassProperties(shapeOut, targetMass, massProperties);
		info.m_mass = massProperties.m_mass;
		info.m_inertiaTensor = massProperties.m_inertiaTensor;
		info.m_centerOfMass.setZero4();
		info.m_friction = raw.friction;
		info.m_restitution = raw.restitution;
		info.m_linearDamping = raw.linearDamping;
		info.m_angularDamping = raw.angularDamping;
		info.m_collisionFilterInfo = raw.collisionFilterInfo;
		info.m_qualityType = static_cast<hkpCollidableQualityType>(raw.qualityType);

		hkpRigidBody* rigidBody = new hkpRigidBody(info);
		rigidBody->setCenterOfMassLocal(hkVector4::getZero());
		rigidBody->setPositionAndRotation(
			hkVector4(raw.position[0], raw.position[1], raw.position[2]),
			hkQuaternion(raw.rotation[0], raw.rotation[1], raw.rotation[2], raw.rotation[3]));
		rigidBody->setName(duplicateString(raw.name, storage));
		return rigidBody;
	}

	hkpConstraintInstance* createRagdollConstraint(
		const RawConstraint& raw,
		hkpRigidBody* bodyA,
		hkpRigidBody* bodyB,
		hkpPositionConstraintMotor* motor,
		std::vector<char*>& storage)
	{
		hkpRagdollConstraintData* data = new hkpRagdollConstraintData();
		data->setInBodySpace(
			hkVector4(raw.pivotA[0], raw.pivotA[1], raw.pivotA[2]),
			hkVector4(raw.pivotB[0], raw.pivotB[1], raw.pivotB[2]),
			hkVector4(raw.planeAxisA[0], raw.planeAxisA[1], raw.planeAxisA[2]),
			hkVector4(raw.planeAxisB[0], raw.planeAxisB[1], raw.planeAxisB[2]),
			hkVector4(raw.twistAxisA[0], raw.twistAxisA[1], raw.twistAxisA[2]),
			hkVector4(raw.twistAxisB[0], raw.twistAxisB[1], raw.twistAxisB[2]));

		data->setTwistMinAngularLimit(raw.twistMin);
		data->setTwistMaxAngularLimit(raw.twistMax);
		data->setConeAngularLimit(raw.coneAngle);
		data->setPlaneMinAngularLimit(raw.planeMin);
		data->setPlaneMaxAngularLimit(raw.planeMax);
		data->setMaxFrictionTorque(raw.frictionTorque);
		if (motor)
		{
			data->setTwistMotor(motor);
			data->setConeMotor(motor);
			data->setPlaneMotor(motor);
		}

		hkpConstraintInstance* instance = new hkpConstraintInstance(bodyA, bodyB, data);
		instance->setName(duplicateString(raw.name, storage));
		return instance;
	}

	hkpConstraintInstance* createLimitedHingeConstraint(
		const RawConstraint& raw,
		hkpRigidBody* bodyA,
		hkpRigidBody* bodyB,
		std::vector<char*>& storage)
	{
		hkpLimitedHingeConstraintData* data = new hkpLimitedHingeConstraintData();
		data->setInBodySpace(
			hkVector4(raw.pivotA[0], raw.pivotA[1], raw.pivotA[2]),
			hkVector4(raw.pivotB[0], raw.pivotB[1], raw.pivotB[2]),
			hkVector4(raw.twistAxisA[0], raw.twistAxisA[1], raw.twistAxisA[2]),
			hkVector4(raw.twistAxisB[0], raw.twistAxisB[1], raw.twistAxisB[2]),
			hkVector4(raw.planeAxisA[0], raw.planeAxisA[1], raw.planeAxisA[2]),
			hkVector4(raw.planeAxisB[0], raw.planeAxisB[1], raw.planeAxisB[2]));
		data->setMinAngularLimit(raw.hingeMin);
		data->setMaxAngularLimit(raw.hingeMax);
		data->setMaxFrictionTorque(raw.frictionTorque);

		hkpConstraintInstance* instance = new hkpConstraintInstance(bodyA, bodyB, data);
		instance->setName(duplicateString(raw.name, storage));
		return instance;
	}

	bool isLimitedHingeConstraint(const RawConstraint& raw)
	{
		return raw.constraintType == "limited_hinge"
			|| raw.constraintType == "limitedhinge"
			|| raw.constraintType == "hinge_limits"
			|| raw.constraintType == "hkLimitedHingeConstraintData";
	}
}

RagdollBuildResult::RagdollBuildResult()
	: animationContainer(0),
	  animationSkeleton(0),
	  ragdollSkeleton(0),
	  ragdollToAnimationMapper(0),
	  animationToRagdollMapper(0),
	  ragdollInstance(0),
	  physicsSystem(0),
	  physicsData(0),
	  sharedMotor(0)
{
}

bool buildRagdollScene(const ragdoll_io::RawRagdollData& rawData, RagdollBuildResult& result)
{
	printf("Creating animation skeleton...\n");
	result.animationSkeleton = createSkeleton(rawData.animSkeleton, result.stringStorage);

	printf("Creating ragdoll skeleton...\n");
	result.ragdollSkeleton = createSkeleton(rawData.ragdollSkeleton, result.stringStorage);

	printf("Creating skeleton mappers...\n");
	result.ragdollToAnimationMapper = createSkeletonMapper(
		result.ragdollSkeleton,
		result.animationSkeleton,
		rawData.boneMappings,
		true);
	result.animationToRagdollMapper = createSkeletonMapper(
		result.animationSkeleton,
		result.ragdollSkeleton,
		rawData.boneMappings,
		false);

	printf("Creating rigid bodies...\n");
	result.rigidBodies.resize(rawData.rigidBodies.size());
	result.shapes.resize(rawData.rigidBodies.size());
	for (size_t index = 0; index < rawData.rigidBodies.size(); ++index)
	{
		result.rigidBodies[index] = createRigidBody(rawData.rigidBodies[index], result.stringStorage, result.shapes[index]);
	}

	printf("Creating shared motor...\n");
	result.sharedMotor = new hkpPositionConstraintMotor();
	result.sharedMotor->m_minForce = -1000000.0f;
	result.sharedMotor->m_maxForce = 100.0f;
	result.sharedMotor->m_tau = 0.8f;
	result.sharedMotor->m_damping = 1.0f;
	result.sharedMotor->m_proportionalRecoveryVelocity = 5.0f;
	result.sharedMotor->m_constantRecoveryVelocity = 0.2f;

	printf("Creating constraints...\n");
	result.constraints.resize(rawData.constraints.size(), static_cast<hkpConstraintInstance*>(0));
	for (size_t index = 0; index < rawData.constraints.size(); ++index)
	{
		const RawConstraint& constraint = rawData.constraints[index];
		if (constraint.bodyAIndex < 0
			|| constraint.bodyBIndex < 0
			|| constraint.bodyAIndex >= static_cast<int>(result.rigidBodies.size())
			|| constraint.bodyBIndex >= static_cast<int>(result.rigidBodies.size()))
		{
			fprintf(stderr, "Warning: skipping constraint %u due to invalid body indices (%d, %d)\n",
				static_cast<unsigned>(index),
				constraint.bodyAIndex,
				constraint.bodyBIndex);
			continue;
		}

		if (isLimitedHingeConstraint(constraint))
		{
			result.constraints[index] = createLimitedHingeConstraint(
				constraint,
				result.rigidBodies[constraint.bodyAIndex],
				result.rigidBodies[constraint.bodyBIndex],
				result.stringStorage);
		}
		else
		{
			result.constraints[index] = createRagdollConstraint(
				constraint,
				result.rigidBodies[constraint.bodyAIndex],
				result.rigidBodies[constraint.bodyBIndex],
				result.sharedMotor,
				result.stringStorage);
		}
	}

	hkArray<hkpRigidBody*> bodyArray;
	bodyArray.setSize(static_cast<int>(result.rigidBodies.size()));
	for (int index = 0; index < bodyArray.getSize(); ++index)
	{
		bodyArray[index] = result.rigidBodies[index];
	}

	hkArray<hkpConstraintInstance*> constraintArray;
	for (size_t index = 0; index < result.constraints.size(); ++index)
	{
		if (result.constraints[index] != HK_NULL)
		{
			constraintArray.pushBack(result.constraints[index]);
		}
	}

	printf("Creating ragdoll instance...\n");
	result.ragdollInstance = new hkaRagdollInstance(bodyArray, constraintArray, result.ragdollSkeleton);

	printf("Creating animation container...\n");
	result.animationContainer = new hkaAnimationContainer();
	result.animationContainer->m_skeletons = hkAllocate<hkaSkeleton*>(2, HK_MEMORY_CLASS_ANIM_DATA);
	result.animationContainer->m_numSkeletons = 2;
	result.animationContainer->m_skeletons[0] = result.animationSkeleton;
	result.animationContainer->m_skeletons[1] = result.ragdollSkeleton;
	result.animationContainer->m_animations = HK_NULL;
	result.animationContainer->m_numAnimations = 0;
	result.animationContainer->m_bindings = HK_NULL;
	result.animationContainer->m_numBindings = 0;
	result.animationContainer->m_attachments = HK_NULL;
	result.animationContainer->m_numAttachments = 0;
	result.animationContainer->m_skins = HK_NULL;
	result.animationContainer->m_numSkins = 0;

	printf("Creating physics system...\n");
	result.physicsSystem = new hkpPhysicsSystem();
	result.physicsSystem->setName("Ragdoll System");
	for (size_t index = 0; index < result.rigidBodies.size(); ++index)
	{
		if (result.rigidBodies[index] != HK_NULL)
		{
			result.physicsSystem->addRigidBody(result.rigidBodies[index]);
		}
	}
	for (size_t index = 0; index < result.constraints.size(); ++index)
	{
		if (result.constraints[index] != HK_NULL)
		{
			result.physicsSystem->addConstraint(result.constraints[index]);
		}
	}

	result.physicsData = new hkpPhysicsData();
	result.physicsData->addPhysicsSystem(result.physicsSystem);
	return true;
}