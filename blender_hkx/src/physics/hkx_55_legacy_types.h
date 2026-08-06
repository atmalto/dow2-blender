#ifndef DOW2_PHYSICS_HKX_55_LEGACY_TYPES_H
#define DOW2_PHYSICS_HKX_55_LEGACY_TYPES_H

#include <Common/Base/hkBase.h>
#include <Common/Base/Object/hkReferencedObject.h>

namespace legacy451_physics
{
	static const char* const kLegacyVersion = "Havok-4.5.1-r1";

	struct Legacy461PropertyValue
	{
		hkUint64 m_data;
	};

	struct Legacy461Property
	{
		hkUint32 m_key;
		hkUint32 m_alignmentPadding;
		Legacy461PropertyValue m_value;
	};

	struct Legacy461EnvironmentVariable
	{
		const char* m_name;
		const char* m_value;
	};

	struct Legacy461Environment
	{
		hkArray<Legacy461EnvironmentVariable> m_variables;
	};

	struct Legacy461Aabb
	{
		hkVector4 m_min;
		hkVector4 m_max;
	};

	struct Legacy461AabbUint32
	{
		hkUint32 m_min[3];
		hkInt8 m_expansionMin[3];
		hkInt8 m_expansionShift;
		hkUint32 m_max[3];
		hkInt8 m_expansionMax[3];
		hkInt8 m_sortIndex;

		Legacy461AabbUint32()
			: m_expansionShift(0),
			  m_sortIndex(0)
		{
			m_min[0] = 0;
			m_min[1] = 0;
			m_min[2] = 0;
			m_expansionMin[0] = 0;
			m_expansionMin[1] = 0;
			m_expansionMin[2] = 0;
			m_max[0] = 0;
			m_max[1] = 0;
			m_max[2] = 0;
			m_expansionMax[0] = 0;
			m_expansionMax[1] = 0;
			m_expansionMax[2] = 0;
		}
	};

	struct Legacy461MultiThreadCheck
	{
		hkUint32 m_threadId;
		hkInt16 m_lockCount;
		hkUint16 m_lockBitStack;
	};

	struct Legacy461Material
	{
		hkInt8 m_responseType;
		hkReal m_friction;
		hkReal m_restitution;
	};

	struct Legacy461WorldMemoryWatchDog : public hkReferencedObject
	{
		hkInt32 m_memoryLimit;

		Legacy461WorldMemoryWatchDog()
			: m_memoryLimit(0)
		{
		}
	};

	struct Legacy461CollisionFilter : public hkReferencedObject
	{
		hkInt32 m_type;
		hkUint32 m_pad[3];

		Legacy461CollisionFilter()
			: m_type(0)
		{
			m_pad[0] = 0;
			m_pad[1] = 0;
			m_pad[2] = 0;
		}
	};

	struct Legacy461ConvexListFilter : public hkReferencedObject
	{
	};

	struct Legacy461CollidableBoundingVolumeData
	{
		hkUint32 m_min[3];
		hkUint8 m_expansionMin[3];
		hkUint8 m_expansionShift;
		hkUint32 m_max[3];
		hkUint8 m_expansionMax[3];
		hkUint8 m_padding;
		hkUint16 m_numChildShapeAabbs;
		Legacy461AabbUint32* m_childShapeAabbs;

		Legacy461CollidableBoundingVolumeData()
			: m_expansionShift(0),
			  m_padding(0),
			  m_numChildShapeAabbs(0),
			  m_childShapeAabbs(HK_NULL)
		{
			m_min[0] = 1;
			m_min[1] = 0;
			m_min[2] = 0;
			m_expansionMin[0] = 0;
			m_expansionMin[1] = 0;
			m_expansionMin[2] = 0;
			m_max[0] = 0;
			m_max[1] = 0;
			m_max[2] = 0;
			m_expansionMax[0] = 0;
			m_expansionMax[1] = 0;
			m_expansionMax[2] = 0;
		}
	};

	struct Legacy461EntitySmallArray
	{
		void* m_data;
		hkUint16 m_size;
		hkUint16 m_capacityAndFlags;
	};

	struct Legacy461EntitySpuCollisionCallback
	{
		void* m_util;
		hkUint16 m_capacity;
		hkUint8 m_eventFilter;
		hkUint8 m_userFilter;
	};

	struct Legacy461BroadPhaseHandle
	{
		hkUint32 m_id;

		Legacy461BroadPhaseHandle()
			: m_id(0)
		{
		}
	};

	struct Legacy461TypedBroadPhaseHandle : public Legacy461BroadPhaseHandle
	{
		hkInt8 m_type;
		hkInt8 m_ownerOffset;
		hkUint16 m_objectQualityType;
		hkUint32 m_collisionFilterInfo;

		Legacy461TypedBroadPhaseHandle()
			: m_type(1),
			  m_ownerOffset(0),
			  m_objectQualityType(4),
			  m_collisionFilterInfo(0)
		{
		}
	};

	struct Legacy461Shape : public hkReferencedObject
	{
		hkUlong m_userData;
		hkInt32 m_type;

		Legacy461Shape()
			: m_userData(0),
			  m_type(0)
		{
		}
	};

	struct Legacy461SphereRepShape : public Legacy461Shape
	{
	};

	struct Legacy461ConvexShape : public Legacy461SphereRepShape
	{
		hkReal m_radius;

		Legacy461ConvexShape()
			: m_radius(0.05f)
		{
		}
	};

	struct Legacy461WorldCinfo : public hkReferencedObject
	{
		hkVector4 m_gravity;
		hkInt32 m_broadPhaseQuerySize;
		Legacy461Aabb m_broadPhaseWorldAabb;
		hkReal m_collisionTolerance;
		Legacy461CollisionFilter* m_collisionFilter;
		Legacy461ConvexListFilter* m_convexListFilter;
		Legacy461WorldMemoryWatchDog* m_memoryWatchDog;

		Legacy461WorldCinfo()
			: m_broadPhaseQuerySize(1024),
			  m_collisionTolerance(0.1f),
			  m_collisionFilter(HK_NULL),
			  m_convexListFilter(HK_NULL),
			  m_memoryWatchDog(HK_NULL)
		{
			m_gravity.set(0.0f, -9.8f, 0.0f, 0.0f);
			m_broadPhaseWorldAabb.m_min.setZero4();
			m_broadPhaseWorldAabb.m_max.setZero4();
		}
	};

	struct Legacy461ConvexVerticesShapeFourVectors
	{
		hkVector4 m_x;
		hkVector4 m_y;
		hkVector4 m_z;
	};

	struct Legacy461ConvexVerticesShape : public Legacy461ConvexShape
	{
		hkVector4 m_aabbHalfExtents;
		hkVector4 m_aabbCenter;
		hkArray<Legacy461ConvexVerticesShapeFourVectors> m_rotatedVertices;
		hkInt32 m_numVertices;
		hkArray<hkVector4> m_planeEquations;
		void* m_connectivity;

		Legacy461ConvexVerticesShape()
			: m_numVertices(0),
			  m_connectivity(HK_NULL)
		{
			m_aabbHalfExtents.setZero4();
			m_aabbCenter.setZero4();
		}
	};

	struct Legacy461CdBody
	{
		Legacy461ConvexVerticesShape* m_shape;
		hkUint32 m_shapeKey;
		void* m_motion;
		Legacy461CdBody* m_parent;

		Legacy461CdBody()
			: m_shape(HK_NULL),
			  m_shapeKey(0xffffffffu),
			  m_motion(HK_NULL),
			  m_parent(HK_NULL)
		{
		}
	};

	struct Legacy461Collidable : public Legacy461CdBody
	{
		hkInt8 m_ownerOffset;
		hkUint8 m_forceCollideOntoPpu;
		hkUint16 m_shapeSizeOnSpu;
		Legacy461TypedBroadPhaseHandle m_broadPhaseHandle;
		Legacy461CollidableBoundingVolumeData m_boundingVolumeData;
		hkReal m_allowedPenetrationDepth;

		Legacy461Collidable()
			: m_ownerOffset(0),
			  m_forceCollideOntoPpu(0),
			  m_shapeSizeOnSpu(0),
			  m_allowedPenetrationDepth(HK_REAL_MAX)
		{
		}
	};

	struct Legacy461LinkedCollidable : public Legacy461Collidable
	{
		hkArray<void*> m_collisionEntries;

		Legacy461LinkedCollidable()
		{
		}
	};

	struct Legacy461WorldObject : public hkReferencedObject
	{
		void* m_world;
		hkUlong m_userData;
		Legacy461LinkedCollidable m_collidable;
		Legacy461MultiThreadCheck m_multithreadLock;
		const char* m_name;
		hkArray<Legacy461Property> m_properties;

		Legacy461WorldObject()
			: m_world(HK_NULL),
			  m_userData(0),
			  m_name(HK_NULL)
		{
			m_multithreadLock.m_threadId = 0;
			m_multithreadLock.m_lockCount = 0;
			m_multithreadLock.m_lockBitStack = 0;
		}
	};

	struct Legacy461MotionState
	{
		hkTransform m_transform;
		hkSweptTransform m_sweptTransform;
		hkVector4 m_deltaAngle;
		hkReal m_objectRadius;
		hkReal m_linearDamping;
		hkReal m_angularDamping;
		hkUint8 m_maxLinearVelocity;
		hkUint8 m_maxAngularVelocity;
		hkUint8 m_deactivationClass;

		Legacy461MotionState()
			: m_objectRadius(0.0f),
			  m_linearDamping(0.0f),
			  m_angularDamping(0.05f),
			  m_maxLinearVelocity(200),
			  m_maxAngularVelocity(200),
			  m_deactivationClass(0)
		{
			m_deltaAngle.setZero4();
		}
	};

	struct Legacy461MaxSizeMotion : public hkReferencedObject
	{
		hkInt8 m_type;
		hkUint8 m_deactivationIntegrateCounter;
		hkUint16 m_deactivationNumInactiveFrames[2];
		Legacy461MotionState m_motionState;
		hkVector4 m_inertiaAndMassInv;
		hkVector4 m_linearVelocity;
		hkVector4 m_angularVelocity;
		hkVector4 m_deactivationRefPosition[2];
		hkUint32 m_deactivationRefOrientation[2];
		Legacy461MaxSizeMotion* m_savedMotion;
		hkUint16 m_savedQualityTypeIndex;

		Legacy461MaxSizeMotion()
			: m_type(7),
			  m_deactivationIntegrateCounter(0),
			  m_savedMotion(HK_NULL),
			  m_savedQualityTypeIndex(0)
		{
			m_deactivationNumInactiveFrames[0] = 0;
			m_deactivationNumInactiveFrames[1] = 0;
			m_inertiaAndMassInv.setZero4();
			m_linearVelocity.setZero4();
			m_angularVelocity.setZero4();
			m_deactivationRefPosition[0].setZero4();
			m_deactivationRefPosition[1].setZero4();
			m_deactivationRefOrientation[0] = 0;
			m_deactivationRefOrientation[1] = 0;
		}
	};

	struct Legacy461SpatialRigidBodyDeactivatorSample
	{
		hkVector4 m_refPosition;
		hkQuaternion m_refRotation;

		Legacy461SpatialRigidBodyDeactivatorSample()
		{
			m_refPosition.set(HK_REAL_MAX, HK_REAL_MAX, HK_REAL_MAX, HK_REAL_MAX);
			m_refRotation.set(0.0f, 0.0f, 0.0f, 1.0f);
		}
	};

	struct Legacy461EntityDeactivator : public hkReferencedObject
	{
	};

	struct Legacy461RigidBodyDeactivator : public Legacy461EntityDeactivator
	{
	};

	struct Legacy461SpatialRigidBodyDeactivator : public Legacy461RigidBodyDeactivator
	{
		Legacy461SpatialRigidBodyDeactivatorSample m_highFrequencySample;
		Legacy461SpatialRigidBodyDeactivatorSample m_lowFrequencySample;
		hkReal m_radiusSqrd;
		hkReal m_minHighFrequencyTranslation;
		hkReal m_minHighFrequencyRotation;
		hkReal m_minLowFrequencyTranslation;
		hkReal m_minLowFrequencyRotation;

		Legacy461SpatialRigidBodyDeactivator()
			: m_radiusSqrd(-1.0f),
			  m_minHighFrequencyTranslation(0.01f),
			  m_minHighFrequencyRotation(0.005f),
			  m_minLowFrequencyTranslation(0.1f),
			  m_minLowFrequencyRotation(0.2f)
		{
		}
	};

	struct Legacy461Entity : public Legacy461WorldObject
	{
		Legacy461Material m_material;
		void* m_breakOffPartsUtil;
		hkUint32 m_solverData;
		hkUint16 m_storageIndex;
		hkUint16 m_processContactCallbackDelay;
		Legacy461EntitySmallArray m_constraintsMaster;
		hkArray<void*> m_constraintsSlave;
		hkArray<void*> m_constraintRuntime;
		void* m_simulationIsland;
		hkInt8 m_autoRemoveLevel;
		hkUint8 m_numUserDatasInContactPointProperties;
		hkUint32 m_uid;
		Legacy461EntitySpuCollisionCallback m_spuCollisionCallback;
		void* m_extendedListeners;
		Legacy461MaxSizeMotion m_motion;
		Legacy461EntitySmallArray m_collisionListeners;
		Legacy461EntitySmallArray m_actions;
		Legacy461EntityDeactivator* m_deactivator;
		Legacy461EntitySmallArray m_activationListeners;
		Legacy461EntitySmallArray m_entityListeners;

		Legacy461Entity()
			: m_breakOffPartsUtil(HK_NULL),
			  m_solverData(0),
			  m_storageIndex(0xffffu),
			  m_processContactCallbackDelay(0xffffu),
			  m_simulationIsland(HK_NULL),
			  m_autoRemoveLevel(0),
			  m_numUserDatasInContactPointProperties(0),
			  m_extendedListeners(HK_NULL),
			  m_uid(0xffffffffu),
			  m_deactivator(HK_NULL)
		{
			m_material.m_responseType = 1;
			m_material.m_friction = 0.5f;
			m_material.m_restitution = 0.4f;
			m_constraintsMaster.m_data = HK_NULL;
			m_constraintsMaster.m_size = 0;
			m_constraintsMaster.m_capacityAndFlags = 0;
			m_collisionListeners.m_data = HK_NULL;
			m_collisionListeners.m_size = 0;
			m_collisionListeners.m_capacityAndFlags = 0;
			m_activationListeners.m_data = HK_NULL;
			m_activationListeners.m_size = 0;
			m_activationListeners.m_capacityAndFlags = 0;
			m_entityListeners.m_data = HK_NULL;
			m_entityListeners.m_size = 0;
			m_entityListeners.m_capacityAndFlags = 0;
			m_actions.m_data = HK_NULL;
			m_actions.m_size = 0;
			m_actions.m_capacityAndFlags = 0;
			m_spuCollisionCallback.m_util = HK_NULL;
			m_spuCollisionCallback.m_capacity = 0;
			m_spuCollisionCallback.m_eventFilter = 0;
			m_spuCollisionCallback.m_userFilter = 0;
		}
	};

	struct Legacy461RigidBody : public Legacy461Entity
	{
	};

	struct Legacy461PhysicsSystem : public hkReferencedObject
	{
		hkArray<Legacy461RigidBody*> m_rigidBodies;
		hkArray<void*> m_constraints;
		hkArray<void*> m_actions;
		hkArray<void*> m_phantoms;
		const char* m_name;
		hkUlong m_userData;
		hkBool m_active;

		Legacy461PhysicsSystem()
			: m_name(HK_NULL),
			  m_userData(0),
			  m_active(true)
		{
		}
	};

	struct Legacy461PhysicsData : public hkReferencedObject
	{
		void* m_worldCinfo;
		hkArray<Legacy461PhysicsSystem*> m_systems;

		Legacy461PhysicsData()
			: m_worldCinfo(HK_NULL)
		{
		}
	};
}

#endif