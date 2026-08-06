#ifndef DOW2_PHYSICS_HKX_55_LEGACY_BUILDER_H
#define DOW2_PHYSICS_HKX_55_LEGACY_BUILDER_H

#include <vector>
#include <stdlib.h>
#include <stdio.h>

#include <Common/Base/Reflection/Registry/hkVtableClassRegistry.h>
#include <Common/Serialize/Packfile/hkPackfileWriter.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Physics/Utilities/Serialize/hkpPhysicsData.h>
#include <Physics/Dynamics/World/hkpPhysicsSystem.h>
#include <Physics/Dynamics/Entity/hkpEntity.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>

#include "hkx_55_legacy_classes.h"

namespace legacy451_physics
{
	inline bool isDebugEnvEnabled(const char* name)
	{
		if (name == HK_NULL)
		{
			return false;
		}

		char* value = HK_NULL;
		size_t valueLength = 0;
		if (_dupenv_s(&value, &valueLength, name) != 0)
		{
			return false;
		}

		const bool enabled = (value != HK_NULL && value[0] != '\0');
		free(value);
		return enabled;
	}

	struct LegacyGraph
	{
		Legacy461PhysicsData* physicsData;
		Legacy461Environment environment;
		std::vector<Legacy461PhysicsSystem*> systems;
		std::vector<Legacy461RigidBody*> rigidBodies;
		std::vector<Legacy461ConvexVerticesShape*> shapes;
		std::vector<Legacy461SpatialRigidBodyDeactivator*> deactivators;

		LegacyGraph()
			: physicsData(HK_NULL)
		{
		}

		~LegacyGraph()
		{
			for (size_t i = 0; i < deactivators.size(); ++i)
			{
				delete deactivators[i];
			}
			for (size_t i = 0; i < shapes.size(); ++i)
			{
				delete shapes[i];
			}
			for (size_t i = 0; i < rigidBodies.size(); ++i)
			{
				delete rigidBodies[i];
			}
			for (size_t i = 0; i < systems.size(); ++i)
			{
				delete systems[i];
			}
			delete physicsData;
		}
	};

	struct ExactClassInfo
	{
		const void* object;
		const hkClass* klass;
	};

	class ExactLegacyClassListener : public hkPackfileWriter::AddObjectListener
	{
	public:
		ExactLegacyClassListener(const std::vector<ExactClassInfo>& classes)
			: m_classes(classes)
		{
		}

		virtual void addObjectCallback(ObjectPointer& objP, ClassPointer& klassP)
		{
			for (size_t i = 0; i < m_classes.size(); ++i)
			{
				if (m_classes[i].object == objP)
				{
					klassP = m_classes[i].klass;
					return;
				}
			}
		}

	private:
		const std::vector<ExactClassInfo>& m_classes;
	};

	inline void registerExactObject(
		hkVtableClassRegistry& registry,
		std::vector<ExactClassInfo>& exactClasses,
		const hkReferencedObject* object,
		const hkClass* klass)
	{
		if (object == HK_NULL || klass == HK_NULL)
		{
			return;
		}

		registry.registerVtable(*reinterpret_cast<const void* const*>(object), klass);
		ExactClassInfo info;
		info.object = object;
		info.klass = klass;
		exactClasses.push_back(info);
	}

	inline void fillLegacyShape(
		Legacy461ConvexVerticesShape* legacyShape,
		const hkpConvexVerticesShape* currentShape)
	{
		hkArray<hkVector4> originalVertices;
		currentShape->getOriginalVertices(originalVertices);

		legacyShape->m_type = currentShape->getType();
		legacyShape->m_radius = currentShape->getRadius();
		legacyShape->m_numVertices = originalVertices.getSize();
		legacyShape->m_planeEquations = currentShape->getPlaneEquations();

		hkVector4 minValue;
		hkVector4 maxValue;
		if (originalVertices.getSize() > 0)
		{
			minValue = originalVertices[0];
			maxValue = originalVertices[0];
			for (int i = 1; i < originalVertices.getSize(); ++i)
			{
				minValue.setMin4(minValue, originalVertices[i]);
				maxValue.setMax4(maxValue, originalVertices[i]);
			}
			legacyShape->m_aabbCenter.setInterpolate4(minValue, maxValue, 0.5f);
			legacyShape->m_aabbHalfExtents.setSub4(maxValue, minValue);
			legacyShape->m_aabbHalfExtents.mul4(0.5f);
		}

		const int packedVertexGroups = (legacyShape->m_numVertices + 3) / 4;
		legacyShape->m_rotatedVertices.setSize(packedVertexGroups);
		for (int groupIndex = 0; groupIndex < packedVertexGroups; ++groupIndex)
		{
			float xs[4];
			float ys[4];
			float zs[4];
			for (int lane = 0; lane < 4; ++lane)
			{
				int vertexIndex = groupIndex * 4 + lane;
				if (vertexIndex >= legacyShape->m_numVertices)
				{
					vertexIndex = legacyShape->m_numVertices - 1;
				}
				const hkVector4& vertex = originalVertices[vertexIndex];
				xs[lane] = vertex(0);
				ys[lane] = vertex(1);
				zs[lane] = vertex(2);
			}
			legacyShape->m_rotatedVertices[groupIndex].m_x.set(xs[0], xs[1], xs[2], xs[3]);
			legacyShape->m_rotatedVertices[groupIndex].m_y.set(ys[0], ys[1], ys[2], ys[3]);
			legacyShape->m_rotatedVertices[groupIndex].m_z.set(zs[0], zs[1], zs[2], zs[3]);
		}
	}

	inline bool buildLegacyGraph(
		hkRootLevelContainer* legacyRoot,
		LegacyGraph& graph,
		const hkRootLevelContainer* currentRoot)
	{
		if (legacyRoot == HK_NULL || currentRoot == HK_NULL || currentRoot->m_numNamedVariants <= 0)
		{
			fprintf(stderr, "Error: invalid physics graph passed to legacy builder\n");
			return false;
		}

		const hkpPhysicsData* currentPhysicsData = reinterpret_cast<const hkpPhysicsData*>(currentRoot->m_namedVariants[0].getObject());
		if (currentPhysicsData == HK_NULL)
		{
			fprintf(stderr, "Error: root container does not contain physics data\n");
			return false;
		}

		graph.physicsData = new Legacy461PhysicsData();
		const hkArray<hkpPhysicsSystem*>& currentSystems = currentPhysicsData->getPhysicsSystems();
		graph.physicsData->m_systems.setSize(currentSystems.getSize());

		for (int systemIndex = 0; systemIndex < currentSystems.getSize(); ++systemIndex)
		{
			const hkpPhysicsSystem* currentSystem = currentSystems[systemIndex];
			if (currentSystem == HK_NULL)
			{
				fprintf(stderr, "Error: physics system %d is null\n", systemIndex);
				return false;
			}

			Legacy461PhysicsSystem* legacySystem = new Legacy461PhysicsSystem();
			legacySystem->m_name = currentSystem->getName();
			legacySystem->m_active = currentSystem->isActive();
			graph.systems.push_back(legacySystem);
			graph.physicsData->m_systems[systemIndex] = legacySystem;

			const hkArray<hkpRigidBody*>& currentBodies = currentSystem->getRigidBodies();
			legacySystem->m_rigidBodies.setSize(currentBodies.getSize());
			for (int bodyIndex = 0; bodyIndex < currentBodies.getSize(); ++bodyIndex)
			{
				const hkpRigidBody* currentBody = currentBodies[bodyIndex];
				const hkpConvexVerticesShape* currentShape = reinterpret_cast<const hkpConvexVerticesShape*>(currentBody->getCollidable()->getShape());
				if (currentBody == HK_NULL || currentShape == HK_NULL)
				{
					fprintf(stderr, "Error: rigid body %d in system %d is missing a convex vertices shape\n", bodyIndex, systemIndex);
					return false;
				}

				Legacy461ConvexVerticesShape* legacyShape = new Legacy461ConvexVerticesShape();
				fillLegacyShape(legacyShape, currentShape);
				graph.shapes.push_back(legacyShape);

				const hkpMotion* currentMotion = reinterpret_cast<const hkpMotion*>(&currentBody->m_motion);
				Legacy461SpatialRigidBodyDeactivator* legacyDeactivator = HK_NULL;
				if (currentMotion->getType() != hkpMotion::MOTION_FIXED)
				{
					legacyDeactivator = new Legacy461SpatialRigidBodyDeactivator();
					graph.deactivators.push_back(legacyDeactivator);
				}

				Legacy461RigidBody* legacyBody = new Legacy461RigidBody();
				legacyBody->m_name = currentBody->getName();
				legacyBody->m_collidable.m_shape = legacyShape;
				legacyBody->m_collidable.m_forceCollideOntoPpu = currentBody->getCollidable()->m_forceCollideOntoPpu;
				legacyBody->m_collidable.m_broadPhaseHandle.m_type = 1;
				legacyBody->m_collidable.m_broadPhaseHandle.m_objectQualityType = currentBody->getQualityType();
				legacyBody->m_collidable.m_broadPhaseHandle.m_collisionFilterInfo = currentBody->getCollisionFilterInfo();
				legacyBody->m_collidable.m_boundingVolumeData.m_min[0] = 1;
				legacyBody->m_collidable.m_boundingVolumeData.m_min[1] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_min[2] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[0] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[1] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[2] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionShift = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_max[0] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_max[1] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_max[2] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[0] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[1] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[2] = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_padding = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_numChildShapeAabbs = 0;
				legacyBody->m_collidable.m_boundingVolumeData.m_childShapeAabbs = HK_NULL;
				legacyBody->m_collidable.m_allowedPenetrationDepth = currentBody->getCollidable()->m_allowedPenetrationDepth;
				legacyBody->m_material.m_responseType = currentBody->getMaterial().getResponseType();
				legacyBody->m_material.m_friction = currentBody->getFriction();
				legacyBody->m_material.m_restitution = currentBody->getRestitution();
				legacyBody->m_storageIndex = currentBody->m_storageIndex;
				legacyBody->m_processContactCallbackDelay = currentBody->getProcessContactCallbackDelay();
				legacyBody->m_deactivator = legacyDeactivator;
				legacyBody->m_autoRemoveLevel = currentBody->m_autoRemoveLevel;
				legacyBody->m_uid = currentBody->getUid();
				legacyBody->m_spuCollisionCallback.m_eventFilter = currentBody->m_spuCollisionCallback.m_eventFilter;
				legacyBody->m_spuCollisionCallback.m_userFilter = currentBody->m_spuCollisionCallback.m_userFilter;

				const hkMotionState* currentMotionState = currentMotion->getMotionState();
				legacyBody->m_motion.m_type = currentMotion->getType();
				legacyBody->m_motion.m_deactivationIntegrateCounter = currentMotion->m_deactivationIntegrateCounter;
				legacyBody->m_motion.m_deactivationNumInactiveFrames[0] = currentMotion->m_deactivationNumInactiveFrames[0];
				legacyBody->m_motion.m_deactivationNumInactiveFrames[1] = currentMotion->m_deactivationNumInactiveFrames[1];
				legacyBody->m_motion.m_motionState.m_transform = currentMotionState->getTransform();
				legacyBody->m_motion.m_motionState.m_sweptTransform = currentMotionState->getSweptTransform();
				legacyBody->m_motion.m_motionState.m_deltaAngle = currentMotionState->m_deltaAngle;
				legacyBody->m_motion.m_motionState.m_objectRadius = currentMotionState->m_objectRadius;
				legacyBody->m_motion.m_motionState.m_linearDamping = currentMotionState->m_linearDamping;
				legacyBody->m_motion.m_motionState.m_angularDamping = currentMotionState->m_angularDamping;
				legacyBody->m_motion.m_motionState.m_maxLinearVelocity = static_cast<hkUint8>(currentMotionState->m_maxLinearVelocity);
				legacyBody->m_motion.m_motionState.m_maxAngularVelocity = static_cast<hkUint8>(currentMotionState->m_maxAngularVelocity);
				legacyBody->m_motion.m_motionState.m_deactivationClass = static_cast<hkUint8>(currentMotionState->m_deactivationClass);
				legacyBody->m_motion.m_deactivationRefOrientation[0] = currentMotion->m_deactivationRefOrientation[0];
				legacyBody->m_motion.m_deactivationRefOrientation[1] = currentMotion->m_deactivationRefOrientation[1];
				legacyBody->m_motion.m_inertiaAndMassInv = currentMotion->m_inertiaAndMassInv;
				legacyBody->m_motion.m_linearVelocity = currentMotion->m_linearVelocity;
				legacyBody->m_motion.m_angularVelocity = currentMotion->m_angularVelocity;
				legacyBody->m_motion.m_deactivationRefPosition[0] = currentMotion->m_deactivationRefPosition[0];
				legacyBody->m_motion.m_deactivationRefPosition[1] = currentMotion->m_deactivationRefPosition[1];
				legacyBody->m_motion.m_savedQualityTypeIndex = static_cast<hkUint16>(currentMotion->m_savedQualityTypeIndex);

				if (currentMotion->getType() == hkpMotion::MOTION_FIXED)
				{
					legacyBody->m_motion.m_deactivationNumInactiveFrames[0] = 0;
					legacyBody->m_motion.m_deactivationNumInactiveFrames[1] = 0;
					legacyBody->m_motion.m_savedQualityTypeIndex = 0;
				}

				if (isDebugEnvEnabled("DOW2_HKX_DEBUG_LEGACY") && systemIndex == 0 && bodyIndex == 0)
				{
					fprintf(stderr,
						"LEGACY451 layout: WorldObject=%u Entity=%u RigidBody=%u Motion=%u Collidable=%u collidableOff=%u motionOff=%u bvdOff=%u deactOff=%u inactiveOff=%u\n",
						static_cast<unsigned>(sizeof(Legacy461WorldObject)),
						static_cast<unsigned>(sizeof(Legacy461Entity)),
						static_cast<unsigned>(sizeof(Legacy461RigidBody)),
						static_cast<unsigned>(sizeof(Legacy461MaxSizeMotion)),
						static_cast<unsigned>(sizeof(Legacy461Collidable)),
						static_cast<unsigned>(HK_OFFSET_OF(Legacy461WorldObject, m_collidable)),
						static_cast<unsigned>(HK_OFFSET_OF(Legacy461Entity, m_motion)),
						static_cast<unsigned>(HK_OFFSET_OF(Legacy461Collidable, m_boundingVolumeData)),
						static_cast<unsigned>(HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationIntegrateCounter)),
						static_cast<unsigned>(HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationNumInactiveFrames)));
					fprintf(stderr,
						"LEGACY451 first body: shapeType=%d responseType=%d bvd_min=%u,%u,%u expMin=%u,%u,%u expShift=%u max=%u,%u,%u expMax=%u,%u,%u pad=%u childCount=%u allowed=%g deact=%u inactive=%u,%u type=%d\n",
						legacyBody->m_collidable.m_shape->m_type,
						legacyBody->m_material.m_responseType,
						legacyBody->m_collidable.m_boundingVolumeData.m_min[0],
						legacyBody->m_collidable.m_boundingVolumeData.m_min[1],
						legacyBody->m_collidable.m_boundingVolumeData.m_min[2],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[0],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[1],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMin[2],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionShift,
						legacyBody->m_collidable.m_boundingVolumeData.m_max[0],
						legacyBody->m_collidable.m_boundingVolumeData.m_max[1],
						legacyBody->m_collidable.m_boundingVolumeData.m_max[2],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[0],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[1],
						legacyBody->m_collidable.m_boundingVolumeData.m_expansionMax[2],
						legacyBody->m_collidable.m_boundingVolumeData.m_padding,
						legacyBody->m_collidable.m_boundingVolumeData.m_numChildShapeAabbs,
						legacyBody->m_collidable.m_allowedPenetrationDepth,
						legacyBody->m_motion.m_deactivationIntegrateCounter,
						legacyBody->m_motion.m_deactivationNumInactiveFrames[0],
						legacyBody->m_motion.m_deactivationNumInactiveFrames[1],
						legacyBody->m_motion.m_type);
				}

				graph.rigidBodies.push_back(legacyBody);
				legacySystem->m_rigidBodies[bodyIndex] = legacyBody;
			}
		}

		graph.environment.m_variables.setSize(3);
		graph.environment.m_variables[0].m_name = "modeller";
		graph.environment.m_variables[0].m_value = "Blender 4.3";
		graph.environment.m_variables[1].m_name = "configuration";
		graph.environment.m_variables[1].m_value = "Default";
		graph.environment.m_variables[2].m_name = "infoString";
		graph.environment.m_variables[2].m_value = "Generated by dow2_tools";

		legacyRoot->m_namedVariants = hkAllocate<hkRootLevelContainer::NamedVariant>(2, HK_MEMORY_CLASS_SERIALIZE);
		legacyRoot->m_numNamedVariants = 2;
		legacyRoot->m_namedVariants[0].set("Environment Data", &graph.environment, &g_legacy461EnvironmentClass);
		const bool useBuildingLayout = graph.deactivators.empty();
		legacyRoot->m_namedVariants[1].set("Physics Data", graph.physicsData, selectLegacyPhysicsDataClass(useBuildingLayout));
		return true;
	}
}

#endif