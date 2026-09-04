#include "hkx_451r_reader.h"

#include <stdio.h>
#include <string.h>

#include <vector>

#include <Animation/Animation/Mapper/hkaSkeletonMapper.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>
#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/Math/QsTransform/hkQsTransform.h>
#include <Common/Serialize/Util/hkLoader.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/Capsule/hkpCapsuleShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTranslate/hkpConvexTranslateShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTransform/hkpConvexTransformShape.h>
#include <Physics/Collide/Shape/Misc/Transform/hkpTransformShape.h>
#include <Physics/Collide/Shape/hkpShape.h>
#include <Physics/Dynamics/Constraint/Bilateral/LimitedHinge/hkpLimitedHingeConstraintData.h>
#include <Physics/Dynamics/Constraint/Bilateral/Ragdoll/hkpRagdollConstraintData.h>
#include <Physics/Dynamics/Constraint/hkpConstraintData.h>
#include <Physics/Dynamics/Constraint/hkpConstraintInstance.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/Motion/hkpMotion.h>

using namespace ragdoll_io;

namespace
{
	const float kPi = 3.14159265f;

	void* findObjectByTypeName(const hkRootLevelContainer* rootContainer, const char* typeName)
	{
		if (rootContainer == HK_NULL || typeName == HK_NULL)
		{
			return HK_NULL;
		}

		void* object = rootContainer->findObjectByType(typeName);
		if (object != HK_NULL)
		{
			return object;
		}

		for (int index = 0; index < rootContainer->m_numNamedVariants; ++index)
		{
			const hkRootLevelContainer::NamedVariant& variant = rootContainer->m_namedVariants[index];
			const char* variantTypeName = variant.getTypeName();
			if (variantTypeName != HK_NULL && strcmp(variantTypeName, typeName) == 0)
			{
				return variant.getObject();
			}
		}

		return HK_NULL;
	}

	const char* safeName(const char* value, const char* fallback)
	{
		return value != HK_NULL && value[0] != '\0' ? value : fallback;
	}

	void setIdentityTransform(RawTransform& transform)
	{
		transform.pos[0] = transform.pos[1] = transform.pos[2] = 0.0f;
		transform.rot[0] = transform.rot[1] = transform.rot[2] = 0.0f;
		transform.rot[3] = 1.0f;
		transform.scale[0] = transform.scale[1] = transform.scale[2] = 1.0f;
	}

	void storeVector3(const hkVector4& source, float destination[3])
	{
		destination[0] = source(0);
		destination[1] = source(1);
		destination[2] = source(2);
	}

	void storeQuaternion(const hkQuaternion& source, float destination[4])
	{
		const hkVector4& imag = source.getImag();
		destination[0] = imag(0);
		destination[1] = imag(1);
		destination[2] = imag(2);
		destination[3] = source.getReal();
	}

	void storeTransform(const hkQsTransform& source, RawTransform& destination)
	{
		storeVector3(source.getTranslation(), destination.pos);
		storeQuaternion(source.getRotation(), destination.rot);
		storeVector3(source.getScale(), destination.scale);
	}

	void storeRotationColumns(const hkTransform& transform, float twistAxis[3], float planeAxis[3])
	{
		storeVector3(transform.getRotation().getColumn(0), twistAxis);
		storeVector3(transform.getRotation().getColumn(1), planeAxis);
	}

	const char* getMotionTypeName(hkpMotion::MotionType motionType)
	{
		switch (motionType)
		{
		case hkpMotion::MOTION_DYNAMIC:
			return "MOTION_DYNAMIC";
		case hkpMotion::MOTION_SPHERE_INERTIA:
			return "MOTION_SPHERE_INERTIA";
		case hkpMotion::MOTION_STABILIZED_SPHERE_INERTIA:
			return "MOTION_STABILIZED_SPHERE_INERTIA";
		case hkpMotion::MOTION_BOX_INERTIA:
			return "MOTION_BOX_INERTIA";
		case hkpMotion::MOTION_STABILIZED_BOX_INERTIA:
			return "MOTION_STABILIZED_BOX_INERTIA";
		case hkpMotion::MOTION_KEYFRAMED:
			return "MOTION_KEYFRAMED";
		case hkpMotion::MOTION_FIXED:
			return "MOTION_FIXED";
		case hkpMotion::MOTION_THIN_BOX_INERTIA:
			return "MOTION_THIN_BOX_INERTIA";
		case hkpMotion::MOTION_CHARACTER:
			return "MOTION_CHARACTER";
		default:
			return "INVALID";
		}
	}

	const hkaAnimationContainer* findAnimationContainer(const hkRootLevelContainer* rootContainer)
	{
		return reinterpret_cast<const hkaAnimationContainer*>(findObjectByTypeName(rootContainer, hkaAnimationContainerClass.getName()));
	}

	const hkaSkeleton* findAnimationSkeleton(
		const hkRootLevelContainer* rootContainer,
		const hkaAnimationContainer* animationContainer,
		const hkaSkeleton* ragdollSkeleton)
	{
		const hkaSkeleton* bestSkeleton = HK_NULL;
		int bestBoneCount = -1;

		if (animationContainer != HK_NULL && animationContainer->m_skeletons != HK_NULL)
		{
			for (int index = 0; index < animationContainer->m_numSkeletons; ++index)
			{
				const hkaSkeleton* skeleton = animationContainer->m_skeletons[index];
				if (skeleton == HK_NULL || skeleton == ragdollSkeleton)
				{
					continue;
				}

				if (skeleton->m_numBones > bestBoneCount)
				{
					bestSkeleton = skeleton;
					bestBoneCount = skeleton->m_numBones;
				}
			}
		}

		if (bestSkeleton != HK_NULL)
		{
			return bestSkeleton;
		}

		const void* previousObject = HK_NULL;
		while (const void* object = rootContainer->findObjectByType(hkaSkeletonClass.getName(), previousObject))
		{
			const hkaSkeleton* skeleton = static_cast<const hkaSkeleton*>(object);
			previousObject = object;

			if (skeleton == HK_NULL || skeleton == ragdollSkeleton)
			{
				continue;
			}

			if (skeleton->m_numBones > bestBoneCount)
			{
				bestSkeleton = skeleton;
				bestBoneCount = skeleton->m_numBones;
			}
		}

		return bestSkeleton;
	}

	const hkaSkeletonMapper* findBestMapper(
		const hkRootLevelContainer* rootContainer,
		const hkaSkeleton* ragdollSkeleton,
		const hkaSkeleton* animationSkeleton)
	{
		const hkaSkeletonMapper* bestMapper = HK_NULL;
		int bestScore = -1;

		const void* previousObject = HK_NULL;
		while (const void* object = rootContainer->findObjectByType(hkaSkeletonMapperClass.getName(), previousObject))
		{
			const hkaSkeletonMapper* mapper = static_cast<const hkaSkeletonMapper*>(object);
			previousObject = object;

			if (mapper == HK_NULL)
			{
				continue;
			}

			const bool ragdollToAnimation = mapper->m_mapping.m_skeletonA == ragdollSkeleton && mapper->m_mapping.m_skeletonB == animationSkeleton;
			const bool animationToRagdoll = mapper->m_mapping.m_skeletonA == animationSkeleton && mapper->m_mapping.m_skeletonB == ragdollSkeleton;
			if (ragdollToAnimation)
			{
				return mapper;
			}

			int score = mapper->m_mapping.m_simpleMappings.getSize();
			if (animationToRagdoll)
			{
				score += 100000;
			}

			if (score > bestScore)
			{
				bestMapper = mapper;
				bestScore = score;
			}
		}

		return bestMapper;
	}

	bool copySkeleton(const hkaSkeleton* source, RawSkeleton& destination)
	{
		if (source == HK_NULL || source->m_numBones <= 0 || source->m_bones == HK_NULL)
		{
			return false;
		}

		destination.name = safeName(source->m_name, "Skeleton");
		destination.bones.clear();
		destination.parentIndices.clear();
		destination.referencePose.clear();

		for (int index = 0; index < source->m_numBones; ++index)
		{
			destination.bones.push_back(safeName(source->m_bones[index] ? source->m_bones[index]->m_name : HK_NULL, "Bone"));
			destination.parentIndices.push_back(index < source->m_numParentIndices ? source->m_parentIndices[index] : -1);

			RawTransform transform;
			setIdentityTransform(transform);
			if (source->m_referencePose != HK_NULL && index < source->m_numReferencePose)
			{
				storeTransform(source->m_referencePose[index], transform);
			}
			destination.referencePose.push_back(transform);
		}

		return true;
	}

	bool buildBoneMappingsFromNames(
		const hkaSkeleton* ragdollSkeleton,
		const hkaSkeleton* animationSkeleton,
		std::vector<RawBoneMapping>& mappingsOut)
	{
		if (ragdollSkeleton == HK_NULL || animationSkeleton == HK_NULL)
		{
			return false;
		}

		for (int ragdollBoneIndex = 0; ragdollBoneIndex < ragdollSkeleton->m_numBones; ++ragdollBoneIndex)
		{
			const char* ragdollBoneName = safeName(
				ragdollSkeleton->m_bones && ragdollSkeleton->m_bones[ragdollBoneIndex] ? ragdollSkeleton->m_bones[ragdollBoneIndex]->m_name : HK_NULL,
				"");

			for (int animationBoneIndex = 0; animationBoneIndex < animationSkeleton->m_numBones; ++animationBoneIndex)
			{
				const char* animationBoneName = safeName(
					animationSkeleton->m_bones && animationSkeleton->m_bones[animationBoneIndex] ? animationSkeleton->m_bones[animationBoneIndex]->m_name : HK_NULL,
					"");

				if (strcmp(ragdollBoneName, animationBoneName) == 0)
				{
					RawBoneMapping mapping;
					mapping.ragdollBone = ragdollBoneIndex;
					mapping.animBone = animationBoneIndex;
					setIdentityTransform(mapping.transform);
					mappingsOut.push_back(mapping);
					break;
				}
			}
		}

		return !mappingsOut.empty();
	}

	bool extractBoneMappings(
		const hkaSkeletonMapper* mapper,
		const hkaSkeleton* ragdollSkeleton,
		const hkaSkeleton* animationSkeleton,
		std::vector<RawBoneMapping>& mappingsOut)
	{
		mappingsOut.clear();

		if (mapper != HK_NULL)
		{
			const bool ragdollToAnimation = mapper->m_mapping.m_skeletonA == ragdollSkeleton && mapper->m_mapping.m_skeletonB == animationSkeleton;
			const bool animationToRagdoll = mapper->m_mapping.m_skeletonA == animationSkeleton && mapper->m_mapping.m_skeletonB == ragdollSkeleton;

			if (ragdollToAnimation || animationToRagdoll)
			{
				for (int index = 0; index < mapper->m_mapping.m_simpleMappings.getSize(); ++index)
				{
					const hkaSkeletonMapperData::SimpleMapping& sourceMapping = mapper->m_mapping.m_simpleMappings[index];
					RawBoneMapping mapping;
					mapping.ragdollBone = ragdollToAnimation ? sourceMapping.m_boneA : sourceMapping.m_boneB;
					mapping.animBone = ragdollToAnimation ? sourceMapping.m_boneB : sourceMapping.m_boneA;
					storeTransform(sourceMapping.m_aFromBTransform, mapping.transform);
					mappingsOut.push_back(mapping);
				}
			}
		}

		if (mappingsOut.empty())
		{
			fprintf(stderr, "Warning: no explicit ragdoll-to-animation mapper found, falling back to same-name bone mappings\n");
			return buildBoneMappingsFromNames(ragdollSkeleton, animationSkeleton, mappingsOut);
		}

		return true;
	}

	int findBodyIndex(const std::vector<const hkpRigidBody*>& bodies, const hkpRigidBody* rigidBody)
	{
		for (size_t index = 0; index < bodies.size(); ++index)
		{
			if (bodies[index] == rigidBody)
			{
				return static_cast<int>(index);
			}
		}
		return -1;
	}

	bool extractTransformedShape(const hkpShape* child, const hkTransform& localTransform, RawRigidBody& bodyOut);

	bool extractShape(const hkpShape* shape, RawRigidBody& bodyOut)
	{
		if (shape == HK_NULL)
		{
			return false;
		}

		bodyOut.vertexA[0] = bodyOut.vertexA[1] = bodyOut.vertexA[2] = 0.0f;
		bodyOut.vertexB[0] = bodyOut.vertexB[1] = bodyOut.vertexB[2] = 0.0f;
		bodyOut.halfExtents[0] = bodyOut.halfExtents[1] = bodyOut.halfExtents[2] = 0.0f;

		switch (shape->getType())
		{
		case HK_SHAPE_SPHERE:
			{
				const hkpSphereShape* sphereShape = static_cast<const hkpSphereShape*>(shape);
				bodyOut.shapeType = "sphere";
				bodyOut.radius = sphereShape->getRadius();
				bodyOut.halfExtents[0] = bodyOut.radius;
				bodyOut.halfExtents[1] = bodyOut.radius;
				bodyOut.halfExtents[2] = bodyOut.radius;
				return true;
			}
		case HK_SHAPE_CAPSULE:
			{
				const hkpCapsuleShape* capsuleShape = static_cast<const hkpCapsuleShape*>(shape);
				bodyOut.shapeType = "capsule";
				bodyOut.radius = capsuleShape->getRadius();
				storeVector3(capsuleShape->getVertex(0), bodyOut.vertexA);
				storeVector3(capsuleShape->getVertex(1), bodyOut.vertexB);
				hkVector4 axis;
				axis.setSub4(capsuleShape->getVertex(1), capsuleShape->getVertex(0));
				const float length = axis.length3();
				bodyOut.halfExtents[0] = bodyOut.radius;
				bodyOut.halfExtents[1] = length * 0.5f;
				bodyOut.halfExtents[2] = bodyOut.radius;
				return true;
			}
		case HK_SHAPE_BOX:
			{
				const hkpBoxShape* boxShape = static_cast<const hkpBoxShape*>(shape);
				bodyOut.shapeType = "box";
				bodyOut.radius = 0.0f;
				bodyOut.halfExtents[0] = boxShape->getHalfExtents()(0);
				bodyOut.halfExtents[1] = boxShape->getHalfExtents()(1);
				bodyOut.halfExtents[2] = boxShape->getHalfExtents()(2);
				return true;
			}
		case HK_SHAPE_CONVEX_TRANSLATE:
			{
				// Preserve the wrapper as explicit local shape_offset data so Blender
				// can keep the body origin on the joint while authoring the translated
				// primitive separately.
				const hkpConvexTranslateShape* translateShape = static_cast<const hkpConvexTranslateShape*>(shape);
				if (!extractShape(translateShape->getChildShape(), bodyOut))
				{
					return false;
				}
				bodyOut.shapeOffset[0] += translateShape->getTranslation()(0);
				bodyOut.shapeOffset[1] += translateShape->getTranslation()(1);
				bodyOut.shapeOffset[2] += translateShape->getTranslation()(2);
				return true;
			}
		case HK_SHAPE_CONVEX_TRANSFORM:
			{
				const hkpConvexTransformShape* transformShape = static_cast<const hkpConvexTransformShape*>(shape);
				return extractTransformedShape(transformShape->getChildShape(), transformShape->getTransform(), bodyOut);
			}
		case HK_SHAPE_TRANSFORM:
			{
				const hkpTransformShape* transformShape = static_cast<const hkpTransformShape*>(shape);
				return extractTransformedShape(transformShape->getChildShape(), transformShape->getTransform(), bodyOut);
			}
		default:
			fprintf(stderr, "Error: unsupported ragdoll rigid-body shape type %d\n", static_cast<int>(shape->getType()));
			return false;
		}
	}

	bool extractTransformedShape(const hkpShape* child, const hkTransform& localTransform, RawRigidBody& bodyOut)
	{
		// Transform-wrapped primitive: unwrap to the child, fold the local
		// translation into the world body position and compose the local
		// rotation into the body rotation, so it imports as a plain primitive.
		if (!extractShape(child, bodyOut))
		{
			return false;
		}
		hkQuaternion bodyRot;
		bodyRot.set(bodyOut.rotation[0], bodyOut.rotation[1], bodyOut.rotation[2], bodyOut.rotation[3]);
		hkVector4 worldOffset;
		worldOffset.setRotatedDir(bodyRot, localTransform.getTranslation());
		bodyOut.position[0] += worldOffset(0);
		bodyOut.position[1] += worldOffset(1);
		bodyOut.position[2] += worldOffset(2);
		hkQuaternion localRot;
		localRot.set(localTransform.getRotation());
		hkQuaternion combined;
		combined.setMul(bodyRot, localRot);
		combined.normalize();
		storeQuaternion(combined, bodyOut.rotation);
		return true;
	}

	bool extractRigidBody(
		const hkpRigidBody* rigidBody,
		int boneIndex,
		const char* fallbackName,
		RawRigidBody& bodyOut)
	{
		if (rigidBody == HK_NULL)
		{
			return false;
		}

		bodyOut.name = safeName(rigidBody->getName(), fallbackName);
		bodyOut.boneIndex = boneIndex;
		bodyOut.mass = rigidBody->getMass();
		bodyOut.friction = rigidBody->getFriction();
		bodyOut.restitution = rigidBody->getRestitution();
		bodyOut.motionType = getMotionTypeName(rigidBody->getMotionType());
		storeVector3(rigidBody->getPosition(), bodyOut.position);
		bodyOut.position[3] = 0.0f;
		storeQuaternion(rigidBody->getRotation(), bodyOut.rotation);
		bodyOut.shapeOffset[0] = bodyOut.shapeOffset[1] = bodyOut.shapeOffset[2] = 0.0f;
		bodyOut.linearDamping = rigidBody->getLinearDamping();
		bodyOut.angularDamping = rigidBody->getAngularDamping();
		bodyOut.collisionFilterInfo = static_cast<int>(rigidBody->getCollisionFilterInfo());
		bodyOut.qualityType = static_cast<int>(rigidBody->getQualityType());

		const hkpShape* shape = rigidBody->getCollidable()->getShape();
		return extractShape(shape, bodyOut);
	}

	bool extractConstraint(
		const hkpConstraintInstance* constraint,
		const char* fallbackName,
		const std::vector<const hkpRigidBody*>& bodies,
		RawConstraint& constraintOut)
	{
		if (constraint == HK_NULL)
		{
			return false;
		}

		constraintOut.name = safeName(constraint->getName(), fallbackName);
		constraintOut.twistMin = 0.0f;
		constraintOut.twistMax = 0.0f;
		constraintOut.coneAngle = 0.0f;
		constraintOut.planeMin = 0.0f;
		constraintOut.planeMax = 0.0f;
		constraintOut.hingeMin = -kPi;
		constraintOut.hingeMax = kPi;
		constraintOut.frictionTorque = 0.0f;

		constraintOut.bodyAIndex = findBodyIndex(bodies, constraint->getRigidBodyA());
		constraintOut.bodyBIndex = findBodyIndex(bodies, constraint->getRigidBodyB());
		if (constraintOut.bodyAIndex < 0 || constraintOut.bodyBIndex < 0)
		{
			fprintf(stderr, "Error: constraint %s references rigid bodies outside the exported body set\n", constraintOut.name.c_str());
			return false;
		}

		const hkpConstraintData* constraintData = constraint->getData();
		if (constraintData == HK_NULL)
		{
			fprintf(stderr, "Error: constraint %s has no data\n", constraintOut.name.c_str());
			return false;
		}

		switch (constraintData->getType())
		{
		case hkpConstraintData::CONSTRAINT_TYPE_RAGDOLL:
			{
				const hkpRagdollConstraintData* ragdollData = static_cast<const hkpRagdollConstraintData*>(constraintData);
				constraintOut.constraintType = "ragdoll";
				storeVector3(ragdollData->m_atoms.m_transforms.m_transformA.getTranslation(), constraintOut.pivotA);
				storeVector3(ragdollData->m_atoms.m_transforms.m_transformB.getTranslation(), constraintOut.pivotB);
				storeRotationColumns(ragdollData->m_atoms.m_transforms.m_transformA, constraintOut.twistAxisA, constraintOut.planeAxisA);
				storeRotationColumns(ragdollData->m_atoms.m_transforms.m_transformB, constraintOut.twistAxisB, constraintOut.planeAxisB);
				constraintOut.twistMin = ragdollData->getTwistMinAngularLimit();
				constraintOut.twistMax = ragdollData->getTwistMaxAngularLimit();
				constraintOut.coneAngle = ragdollData->getConeAngularLimit();
				constraintOut.planeMin = ragdollData->getPlaneMinAngularLimit();
				constraintOut.planeMax = ragdollData->getPlaneMaxAngularLimit();
				constraintOut.frictionTorque = ragdollData->getMaxFrictionTorque();
				return true;
			}
		case hkpConstraintData::CONSTRAINT_TYPE_LIMITEDHINGE:
		case hkpConstraintData::CONSTRAINT_TYPE_HINGE_LIMITS:
			{
				const hkpLimitedHingeConstraintData* hingeData = static_cast<const hkpLimitedHingeConstraintData*>(constraintData);
				constraintOut.constraintType = "limited_hinge";
				storeVector3(hingeData->m_atoms.m_transforms.m_transformA.getTranslation(), constraintOut.pivotA);
				storeVector3(hingeData->m_atoms.m_transforms.m_transformB.getTranslation(), constraintOut.pivotB);
				storeRotationColumns(hingeData->m_atoms.m_transforms.m_transformA, constraintOut.twistAxisA, constraintOut.planeAxisA);
				storeRotationColumns(hingeData->m_atoms.m_transforms.m_transformB, constraintOut.twistAxisB, constraintOut.planeAxisB);
				constraintOut.hingeMin = hingeData->getMinAngularLimit();
				constraintOut.hingeMax = hingeData->getMaxAngularLimit();
				constraintOut.frictionTorque = hingeData->getMaxFrictionTorque();
				return true;
			}
		default:
			fprintf(stderr, "Error: unsupported ragdoll constraint type %d for %s\n", static_cast<int>(constraintData->getType()), constraintOut.name.c_str());
			return false;
		}
	}
}

bool readRagdollPackfile(
	const char* inputFile,
	ragdoll_io::RawRagdollData& dataOut)
{
	dataOut = RawRagdollData();

	hkLoader loader;
	hkRootLevelContainer* rootContainer = loader.load(inputFile);
	if (rootContainer == HK_NULL)
	{
		fprintf(stderr, "Error: failed to load ragdoll HKX %s\n", inputFile);
		return false;
	}

	const hkaRagdollInstance* ragdollInstance = reinterpret_cast<const hkaRagdollInstance*>(findObjectByTypeName(rootContainer, hkaRagdollInstanceClass.getName()));
	if (ragdollInstance == HK_NULL)
	{
		fprintf(stderr, "Error: ragdoll instance not found in %s\n", inputFile);
		return false;
	}

	const hkaSkeleton* ragdollSkeleton = ragdollInstance->getSkeleton();
	const hkaAnimationContainer* animationContainer = findAnimationContainer(rootContainer);
	const hkaSkeleton* animationSkeleton = findAnimationSkeleton(rootContainer, animationContainer, ragdollSkeleton);
	if (!copySkeleton(ragdollSkeleton, dataOut.ragdollSkeleton))
	{
		fprintf(stderr, "Error: ragdoll skeleton not found or invalid in %s\n", inputFile);
		return false;
	}
	if (!copySkeleton(animationSkeleton, dataOut.animSkeleton))
	{
		fprintf(stderr, "Error: animation skeleton not found or invalid in %s\n", inputFile);
		return false;
	}

	const hkaSkeletonMapper* mapper = findBestMapper(rootContainer, ragdollSkeleton, animationSkeleton);
	if (!extractBoneMappings(mapper, ragdollSkeleton, animationSkeleton, dataOut.boneMappings))
	{
		fprintf(stderr, "Error: failed to derive ragdoll bone mappings from %s\n", inputFile);
		return false;
	}

	std::vector<const hkpRigidBody*> bodies;
	bodies.reserve(ragdollInstance->getNumBones());
	for (int boneIndex = 0; boneIndex < ragdollInstance->getNumBones(); ++boneIndex)
	{
		const hkpRigidBody* rigidBody = ragdollInstance->getRigidBodyOfBone(boneIndex);
		if (rigidBody == HK_NULL)
		{
			continue;
		}

		const char* boneName = boneIndex < ragdollSkeleton->m_numBones && ragdollSkeleton->m_bones != HK_NULL && ragdollSkeleton->m_bones[boneIndex] != HK_NULL
			? safeName(ragdollSkeleton->m_bones[boneIndex]->m_name, "RigidBody")
			: "RigidBody";

		RawRigidBody rawBody;
		if (!extractRigidBody(rigidBody, boneIndex, boneName, rawBody))
		{
			fprintf(stderr, "Error: failed to extract rigid body for ragdoll bone %d\n", boneIndex);
			return false;
		}

		bodies.push_back(rigidBody);
		dataOut.rigidBodies.push_back(rawBody);
	}

	if (dataOut.rigidBodies.empty())
	{
		fprintf(stderr, "Error: no ragdoll rigid bodies found in %s\n", inputFile);
		return false;
	}

	for (int boneIndex = 0; boneIndex < ragdollInstance->getNumBones(); ++boneIndex)
	{
		const hkpConstraintInstance* constraint = ragdollInstance->getConstraintOfBone(boneIndex);
		if (constraint == HK_NULL)
		{
			continue;
		}

		const char* boneName = boneIndex < ragdollSkeleton->m_numBones && ragdollSkeleton->m_bones != HK_NULL && ragdollSkeleton->m_bones[boneIndex] != HK_NULL
			? safeName(ragdollSkeleton->m_bones[boneIndex]->m_name, "Constraint")
			: "Constraint";

		RawConstraint rawConstraint;
		if (!extractConstraint(constraint, boneName, bodies, rawConstraint))
		{
			return false;
		}

		dataOut.constraints.push_back(rawConstraint);
	}

	return true;
}