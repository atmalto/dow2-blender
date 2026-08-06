#include "hkx_451r_reader.h"

#include <stdio.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/Math/Matrix/hkTransform.h>
#include <Common/Base/System/Io/IStream/hkIStream.h>
#include <Physics/Collide/Agent/Collidable/hkpCollidable.h>
#include <Physics/Collide/Shape/Compound/Collection/List/hkpListShape.h>
#include <Physics/Collide/Shape/Compound/Tree/Mopp/hkpMoppBvTreeShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTransform/hkpConvexTransformShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTranslate/hkpConvexTranslateShape.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>
#include <Physics/Collide/Shape/Misc/Transform/hkpTransformShape.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/Motion/hkpMotion.h>
#include <Physics/Dynamics/World/hkpPhysicsSystem.h>
#include <Physics/Utilities/Serialize/hkpHavokSnapshot.h>
#include <Physics/Utilities/Serialize/hkpPhysicsData.h>

namespace
{
	class LoadedPhysicsSnapshot
	{
	public:
		LoadedPhysicsSnapshot()
			: m_allocatedData(HK_NULL)
		{
		}

		~LoadedPhysicsSnapshot()
		{
			if (m_allocatedData != HK_NULL)
			{
				m_allocatedData->removeReference();
				m_allocatedData = HK_NULL;
			}
		}

		hkpPhysicsData* load(const char* inputFile)
		{
			hkIstream input(inputFile);
			if (!input.isOk())
			{
				fprintf(stderr, "Error: cannot open input HKX file %s\n", inputFile);
				return HK_NULL;
			}

			hkpPhysicsData* physicsData = hkpHavokSnapshot::load(input.getStreamReader(), &m_allocatedData);
			if (physicsData == HK_NULL)
			{
				fprintf(stderr, "Error: failed to load physics data from %s\n", inputFile);
			}
			return physicsData;
		}

	private:
		hkPackfileReader::AllocatedData* m_allocatedData;
	};

	const char* getMotionTypeName(hkpMotion::MotionType motionType)
	{
		switch (motionType)
		{
		case hkpMotion::MOTION_DYNAMIC:
			return "DYNAMIC";
		case hkpMotion::MOTION_SPHERE_INERTIA:
			return "SPHERE_INERTIA";
		case hkpMotion::MOTION_STABILIZED_SPHERE_INERTIA:
			return "STABILIZED_SPHERE_INERTIA";
		case hkpMotion::MOTION_BOX_INERTIA:
			return "BOX_INERTIA";
		case hkpMotion::MOTION_STABILIZED_BOX_INERTIA:
			return "STABILIZED_BOX_INERTIA";
		case hkpMotion::MOTION_KEYFRAMED:
			return "KEYFRAMED";
		case hkpMotion::MOTION_FIXED:
			return "FIXED";
		case hkpMotion::MOTION_THIN_BOX_INERTIA:
			return "THIN_BOX_INERTIA";
		case hkpMotion::MOTION_CHARACTER:
			return "CHARACTER";
		default:
			return "INVALID";
		}
	}

	const char* getResponseTypeName(hkpMaterial::ResponseType responseType)
	{
		switch (responseType)
		{
		case hkpMaterial::RESPONSE_SIMPLE_CONTACT:
			return "RESPONSE_SIMPLE_CONTACT";
		case hkpMaterial::RESPONSE_REPORTING:
			return "RESPONSE_REPORTING";
		case hkpMaterial::RESPONSE_NONE:
			return "RESPONSE_NONE";
		default:
			return "RESPONSE_SIMPLE_CONTACT";
		}
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

	hkTransform makeTranslationTransform(const hkVector4& translation)
	{
		hkTransform transform;
		transform.setIdentity();
		transform.setTranslation(translation);
		return transform;
	}

	void appendVertex(const hkVector4& source, std::vector<RawVertex>& verticesOut)
	{
		RawVertex vertex;
		vertex.x = source(0);
		vertex.y = source(1);
		vertex.z = source(2);
		verticesOut.push_back(vertex);
	}

	float extractShapeRadius(const hkpShape* shape)
	{
		if (shape == HK_NULL)
		{
			return 0.05f;
		}

		switch (shape->getType())
		{
		case HK_SHAPE_CONVEX_VERTICES:
			return static_cast<const hkpConvexVerticesShape*>(shape)->getRadius();
		case HK_SHAPE_CONVEX_TRANSLATE:
			return extractShapeRadius(static_cast<const hkpConvexTranslateShape*>(shape)->getChildShape());
		case HK_SHAPE_TRANSFORM:
			return extractShapeRadius(static_cast<const hkpTransformShape*>(shape)->getChildShape());
		case HK_SHAPE_CONVEX_TRANSFORM:
			return extractShapeRadius(static_cast<const hkpConvexTransformShape*>(shape)->getChildShape());
		case HK_SHAPE_LIST:
			{
				const hkpListShape* listShape = static_cast<const hkpListShape*>(shape);
				if (listShape->getNumChildShapes() > 0)
				{
					return extractShapeRadius(listShape->getChildShapeInl(0));
				}
				break;
			}
		case HK_SHAPE_MOPP:
			return extractShapeRadius(static_cast<const hkpMoppBvTreeShape*>(shape)->getChild());
		default:
			break;
		}
		return 0.05f;
	}

	bool collectShapeVertices(
		const hkpShape* shape,
		const hkTransform& transform,
		std::vector<RawVertex>& verticesOut)
	{
		if (shape == HK_NULL)
		{
			return false;
		}

		switch (shape->getType())
		{
		case HK_SHAPE_CONVEX_VERTICES:
			{
				const hkpConvexVerticesShape* convexShape = static_cast<const hkpConvexVerticesShape*>(shape);
				hkArray<hkVector4> originalVertices;
				convexShape->getOriginalVertices(originalVertices);
				for (int index = 0; index < originalVertices.getSize(); ++index)
				{
					hkVector4 transformedVertex;
					transformedVertex.setTransformedPos(transform, originalVertices[index]);
					appendVertex(transformedVertex, verticesOut);
				}
				return originalVertices.getSize() > 0;
			}

		case HK_SHAPE_CONVEX_TRANSLATE:
			{
				const hkpConvexTranslateShape* translateShape = static_cast<const hkpConvexTranslateShape*>(shape);
				hkTransform localTransform = makeTranslationTransform(translateShape->getTranslation());
				hkTransform combinedTransform;
				combinedTransform.setMul(transform, localTransform);
				return collectShapeVertices(translateShape->getChildShape(), combinedTransform, verticesOut);
			}

		case HK_SHAPE_TRANSFORM:
			{
				const hkpTransformShape* transformShape = static_cast<const hkpTransformShape*>(shape);
				hkTransform combinedTransform;
				combinedTransform.setMul(transform, transformShape->getTransform());
				return collectShapeVertices(transformShape->getChildShape(), combinedTransform, verticesOut);
			}

		case HK_SHAPE_CONVEX_TRANSFORM:
			{
				const hkpConvexTransformShape* transformShape = static_cast<const hkpConvexTransformShape*>(shape);
				hkTransform combinedTransform;
				combinedTransform.setMul(transform, transformShape->getTransform());
				return collectShapeVertices(transformShape->getChildShape(), combinedTransform, verticesOut);
			}

		case HK_SHAPE_LIST:
			{
				const hkpListShape* listShape = static_cast<const hkpListShape*>(shape);
				bool foundVertices = false;
				for (int index = 0; index < listShape->getNumChildShapes(); ++index)
				{
					if (collectShapeVertices(listShape->getChildShapeInl(index), transform, verticesOut))
					{
						foundVertices = true;
					}
				}
				return foundVertices;
			}

		case HK_SHAPE_MOPP:
			{
				const hkpMoppBvTreeShape* moppShape = static_cast<const hkpMoppBvTreeShape*>(shape);
				return collectShapeVertices(moppShape->getChild(), transform, verticesOut);
			}

		default:
			return false;
		}
	}

	bool extractRigidBody(const hkpRigidBody* rigidBody, RawRigidBody& rigidBodyOut)
	{
		if (rigidBody == HK_NULL)
		{
			return false;
		}

		const char* rigidBodyName = rigidBody->getName();
		rigidBodyOut.name = (rigidBodyName != HK_NULL && rigidBodyName[0] != '\0') ? rigidBodyName : "RigidBody";
		rigidBodyOut.motionType = getMotionTypeName(rigidBody->getMotionType());
		storeVector3(rigidBody->getPosition(), rigidBodyOut.position);
		storeQuaternion(rigidBody->getRotation(), rigidBodyOut.rotation);
		rigidBodyOut.friction = rigidBody->getFriction();
		rigidBodyOut.restitution = rigidBody->getRestitution();
		rigidBodyOut.qualityType = (int)rigidBody->getQualityType();
		rigidBodyOut.allowedPenetrationDepth = rigidBody->getCollidable()->m_allowedPenetrationDepth;
		rigidBodyOut.processContactCallbackDelay = (int)rigidBody->getProcessContactCallbackDelay();
		rigidBodyOut.collisionFilterInfo = (unsigned int)rigidBody->getCollisionFilterInfo();
		rigidBodyOut.eventFilter = (int)rigidBody->m_spuCollisionCallback.m_eventFilter;
		rigidBodyOut.userFilter = (int)rigidBody->m_spuCollisionCallback.m_userFilter;
		rigidBodyOut.mass = rigidBody->getMass();
		rigidBodyOut.centerOfMassMode = "CUSTOM";
		storeVector3(rigidBody->getCenterOfMassLocal(), rigidBodyOut.centerOfMassOverride);
		rigidBodyOut.responseType = getResponseTypeName(rigidBody->getMaterial().getResponseType());
		rigidBodyOut.deactivatorPresent = rigidBody->getMotionType() != hkpMotion::MOTION_FIXED;

		hkpRigidBody* mutableRigidBody = const_cast<hkpRigidBody*>(rigidBody);
		const hkpMotion* motion = mutableRigidBody->getMotion();
		if (motion != HK_NULL)
		{
			rigidBodyOut.deactivationIntegrateCounter = (int)motion->m_deactivationIntegrateCounter;
			const hkMotionState* motionState = motion->getMotionState();
			if (motionState != HK_NULL)
			{
				rigidBodyOut.linearDamping = motionState->m_linearDamping;
				rigidBodyOut.angularDamping = motionState->m_angularDamping;
				rigidBodyOut.maxLinearVelocity = motionState->m_maxLinearVelocity;
				rigidBodyOut.maxAngularVelocity = motionState->m_maxAngularVelocity;
				rigidBodyOut.deactivationClass = (int)motionState->m_deactivationClass;
			}
		}

		const hkpShape* shape = rigidBody->getCollidable()->getShape();
		if (shape == HK_NULL)
		{
			return false;
		}
		rigidBodyOut.shapeRadius = extractShapeRadius(shape);

		const hkTransform& worldFromBody = rigidBody->getTransform();
		return collectShapeVertices(shape, worldFromBody, rigidBodyOut.vertices) && !rigidBodyOut.vertices.empty();
	}
}

bool readPhysicsPackfile(
	const char* inputFile,
	std::vector<RawPhysicsSystem>& systemsOut)
{
	systemsOut.clear();

	LoadedPhysicsSnapshot snapshot;
	hkpPhysicsData* physicsData = snapshot.load(inputFile);
	if (physicsData == HK_NULL)
	{
		return false;
	}

	const hkArray<hkpPhysicsSystem*>& physicsSystems = physicsData->getPhysicsSystems();
	if (physicsSystems.getSize() <= 0)
	{
		fprintf(stderr, "Error: no physics systems were found in %s\n", inputFile);
		return false;
	}

	bool foundRigidBodies = false;
	for (int systemIndex = 0; systemIndex < physicsSystems.getSize(); ++systemIndex)
	{
		const hkpPhysicsSystem* physicsSystem = physicsSystems[systemIndex];
		if (physicsSystem == HK_NULL)
		{
			continue;
		}

		RawPhysicsSystem rawSystem;
		const char* systemName = physicsSystem->getName();
		rawSystem.name = (systemName != HK_NULL && systemName[0] != '\0') ? systemName : "Physics System";

		const hkArray<hkpRigidBody*>& rigidBodies = physicsSystem->getRigidBodies();
		for (int rigidBodyIndex = 0; rigidBodyIndex < rigidBodies.getSize(); ++rigidBodyIndex)
		{
			RawRigidBody rawRigidBody;
			if (extractRigidBody(rigidBodies[rigidBodyIndex], rawRigidBody))
			{
				rawSystem.rigidBodies.push_back(rawRigidBody);
				foundRigidBodies = true;
			}
		}

		systemsOut.push_back(rawSystem);
	}

	if (!foundRigidBodies)
	{
		fprintf(stderr, "Error: no convex rigid bodies were found in %s\n", inputFile);
		return false;
	}

	return true;
}