#ifndef DOW2_PHYSICS_HKX_55_LEGACY_CLASSES_H
#define DOW2_PHYSICS_HKX_55_LEGACY_CLASSES_H

#include <Common/Base/Reflection/hkClass.h>
#include <Common/Base/Reflection/hkInternalClassMember.h>

#include "hkx_55_legacy_types.h"

namespace legacy451_physics
{
	extern hkClass g_legacy461PropertyValueClass;
	extern hkClass g_legacy461PropertyClass;
	extern hkClass g_legacy461EnvironmentVariableClass;
	extern hkClass g_legacy461EnvironmentClass;
	extern hkClass g_legacy461AabbClass;
	extern hkClass g_legacy461AabbUint32Class;
	extern hkClass g_legacy461MultiThreadCheckClass;
	extern hkClass g_legacy461EntitySmallArrayClass;
	extern hkClass g_legacy461MaterialClass;
	extern hkClass g_legacy461WorldMemoryWatchDogClass;
	extern hkClass g_legacy461CollisionFilterClass;
	extern hkClass g_legacy461ConvexListFilterClass;
	extern hkClass g_legacy461BroadPhaseHandleClass;
	extern hkClass g_legacy461TypedBroadPhaseHandleClass;
	extern hkClass g_legacy461ShapeClass;
	extern hkClass g_legacy461SphereRepShapeClass;
	extern hkClass g_legacy461ConvexShapeClass;
	extern hkClass g_legacy461ConvexVerticesShapeFourVectorsClass;
	extern hkClass g_legacy461ConvexVerticesShapeClass;
	extern hkClass g_legacy461CdBodyClass;
	extern hkClass g_legacy461CollidableBoundingVolumeDataClass;
	extern hkClass g_legacy461CollidableClass;
	extern hkClass g_legacy461LinkedCollidableClass;
	extern hkClass g_legacy461SweptTransformClass;
	extern hkClass g_legacy461MotionStateClass;
	extern hkClass g_legacy461MotionClass;
	extern hkClass g_legacy461KeyframedRigidMotionClass;
	extern hkClass g_legacy461MaxSizeMotionClass;
	extern hkClass g_legacy461EntityDeactivatorClass;
	extern hkClass g_legacy461RigidBodyDeactivatorClass;
	extern hkClass g_legacy461SpatialRigidBodyDeactivatorSampleClass;
	extern hkClass g_legacy461SpatialRigidBodyDeactivatorClass;
	extern hkClass g_legacy461WorldObjectClass;
	extern hkClass g_legacy461EntitySpuCollisionCallbackClass;
	extern hkClass g_legacy461EntityClassBuilding;
	extern hkClass g_legacy461EntityClass;
	extern hkClass g_legacy461RigidBodyClassBuilding;
	extern hkClass g_legacy461RigidBodyClass;
	extern hkClass g_legacy461ConstraintDataClass;
	extern hkClass g_legacy461ConstraintAtomClass;
	extern hkClass g_legacy461ModifierConstraintAtomClass;
	extern hkClass g_legacy461ConstraintInstanceClass;
	extern hkClass g_legacy461ActionClass;
	extern hkClass g_legacy461PhantomClass;
	extern hkClass g_legacy461WorldCinfoClass;
	extern hkClass g_legacy461PhysicsSystemClassBuilding;
	extern hkClass g_legacy461PhysicsSystemClass;
	extern hkClass g_legacy461PhysicsDataClassBuilding;
	extern hkClass g_legacy461PhysicsDataClass;

	static hkInternalClassMember g_legacy461PropertyValueMembers[] =
	{
		{ "data", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT64, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PropertyValue, m_data), HK_NULL },
	};

	static hkInternalClassMember g_legacy461PropertyMembers[] =
	{
		{ "key", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Property, m_key), HK_NULL },
		{ "alignmentPadding", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Property, m_alignmentPadding), HK_NULL },
		{ "value", &g_legacy461PropertyValueClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Property, m_value), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EnvironmentVariableMembers[] =
	{
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EnvironmentVariable, m_name), HK_NULL },
		{ "value", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EnvironmentVariable, m_value), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EnvironmentMembers[] =
	{
		{ "variables", &g_legacy461EnvironmentVariableClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461Environment, m_variables), HK_NULL },
	};

	static hkInternalClassMember g_legacy461AabbMembers[] =
	{
		{ "min", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Aabb, m_min), HK_NULL },
		{ "max", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Aabb, m_max), HK_NULL },
	};

	static hkInternalClassMember g_legacy461AabbUint32Members[] =
	{
		{ "min", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 3, hkClassMember::ALIGN_16, HK_OFFSET_OF(Legacy461AabbUint32, m_min), HK_NULL },
		{ "expansionMin", HK_NULL, HK_NULL, hkClassMember::TYPE_CHAR, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461AabbUint32, m_expansionMin), HK_NULL },
		{ "expansionShift", HK_NULL, HK_NULL, hkClassMember::TYPE_CHAR, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461AabbUint32, m_expansionShift), HK_NULL },
		{ "max", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461AabbUint32, m_max), HK_NULL },
		{ "expansionMax", HK_NULL, HK_NULL, hkClassMember::TYPE_CHAR, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461AabbUint32, m_expansionMax), HK_NULL },
		{ "sortIndex", HK_NULL, HK_NULL, hkClassMember::TYPE_CHAR, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461AabbUint32, m_sortIndex), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EntitySmallArrayMembers[] =
	{
		{ "data", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySmallArray, m_data), HK_NULL },
		{ "size", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySmallArray, m_size), HK_NULL },
		{ "capacityAndFlags", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySmallArray, m_capacityAndFlags), HK_NULL },
	};

	static hkInternalClassMember g_legacy461MultiThreadCheckMembers[] =
	{
		{ "threadId", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MultiThreadCheck, m_threadId), HK_NULL },
		{ "lockCount", HK_NULL, HK_NULL, hkClassMember::TYPE_INT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MultiThreadCheck, m_lockCount), HK_NULL },
		{ "lockBitStack", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MultiThreadCheck, m_lockBitStack), HK_NULL },
	};

	static const hkInternalClassEnumItem g_legacy461MaterialResponseTypeEnumItems[] =
	{
		{ 0, "RESPONSE_INVALID" },
		{ 1, "RESPONSE_SIMPLE_CONTACT" },
		{ 2, "RESPONSE_REPORTING" },
		{ 3, "RESPONSE_NONE" },
		{ 4, "RESPONSE_MAX_ID" },
	};

	static const hkInternalClassEnum g_legacy461MaterialEnums[] =
	{
		{ "ResponseType", g_legacy461MaterialResponseTypeEnumItems, HK_COUNT_OF(g_legacy461MaterialResponseTypeEnumItems), HK_NULL, 0 },
	};

	static hkInternalClassMember g_legacy461MaterialMembers[] =
	{
		{ "responseType", HK_NULL, reinterpret_cast<const hkClassEnum*>(&g_legacy461MaterialEnums[0]), hkClassMember::TYPE_ENUM, hkClassMember::TYPE_INT8, 0, 0, HK_OFFSET_OF(Legacy461Material, m_responseType), HK_NULL },
		{ "friction", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Material, m_friction), HK_NULL },
		{ "restitution", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Material, m_restitution), HK_NULL },
	};

	static hkInternalClassMember g_legacy461WorldMemoryWatchDogMembers[] =
	{
		{ "memoryLimit", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldMemoryWatchDog, m_memoryLimit), HK_NULL },
	};

	static const hkInternalClassEnumItem g_legacy461FilterTypeEnumItems[] =
	{
		{ 0, "HK_FILTER_UNKNOWN" },
		{ 1, "HK_FILTER_NULL" },
		{ 2, "HK_FILTER_GROUP" },
		{ 3, "HK_FILTER_LIST" },
		{ 4, "HK_FILTER_CUSTOM" },
	};

	static const hkInternalClassEnum g_legacy461CollisionFilterEnums[] =
	{
		{ "hkFilterType", g_legacy461FilterTypeEnumItems, HK_COUNT_OF(g_legacy461FilterTypeEnumItems), HK_NULL, 0 },
	};

	static hkInternalClassMember g_legacy461CollisionFilterMembers[] =
	{
		{ "type", HK_NULL, reinterpret_cast<const hkClassEnum*>(&g_legacy461CollisionFilterEnums[0]), hkClassMember::TYPE_ENUM, hkClassMember::TYPE_VOID, 0, hkClassMember::DEPRECATED_SIZE_32|hkClassMember::ALIGN_16, HK_OFFSET_OF(Legacy461CollisionFilter, m_type), HK_NULL },
		{ "pad", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461CollisionFilter, m_pad), HK_NULL },
	};

	static hkInternalClassMember g_legacy461BroadPhaseHandleMembers[] =
	{
		{ "id", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461BroadPhaseHandle, m_id), HK_NULL },
	};

	static hkInternalClassMember g_legacy461TypedBroadPhaseHandleMembers[] =
	{
		{ "type", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461TypedBroadPhaseHandle, m_type), HK_NULL },
		{ "ownerOffset", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461TypedBroadPhaseHandle, m_ownerOffset), HK_NULL },
		{ "objectQualityType", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461TypedBroadPhaseHandle, m_objectQualityType), HK_NULL },
		{ "collisionFilterInfo", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461TypedBroadPhaseHandle, m_collisionFilterInfo), HK_NULL },
	};

	static hkInternalClassMember g_legacy461ShapeMembers[] =
	{
		{ "userData", HK_NULL, HK_NULL, hkClassMember::TYPE_ULONG, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Shape, m_userData), HK_NULL },
		{ "type", HK_NULL, HK_NULL, hkClassMember::TYPE_ENUM, hkClassMember::TYPE_VOID, 0, hkClassMember::DEPRECATED_SIZE_32, HK_OFFSET_OF(Legacy461Shape, m_type), HK_NULL },
	};

	static hkInternalClassMember g_legacy461ConvexShapeMembers[] =
	{
		{ "radius", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexShape, m_radius), HK_NULL },
	};

	static hkInternalClassMember g_legacy461SweptTransformMembers[] =
	{
		{ "centerOfMass0", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(hkSweptTransform, m_centerOfMass0), HK_NULL },
		{ "centerOfMass1", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(hkSweptTransform, m_centerOfMass1), HK_NULL },
		{ "rotation0", HK_NULL, HK_NULL, hkClassMember::TYPE_QUATERNION, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(hkSweptTransform, m_rotation0), HK_NULL },
		{ "rotation1", HK_NULL, HK_NULL, hkClassMember::TYPE_QUATERNION, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(hkSweptTransform, m_rotation1), HK_NULL },
		{ "centerOfMassLocal", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(hkSweptTransform, m_centerOfMassLocal), HK_NULL },
	};

	static hkInternalClassMember g_legacy461ConvexVerticesShapeFourVectorsMembers[] =
	{
		{ "x", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShapeFourVectors, m_x), HK_NULL },
		{ "y", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShapeFourVectors, m_y), HK_NULL },
		{ "z", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShapeFourVectors, m_z), HK_NULL },
	};

	static hkInternalClassMember g_legacy461ConvexVerticesShapeMembers[] =
	{
		{ "aabbHalfExtents", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_aabbHalfExtents), HK_NULL },
		{ "aabbCenter", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_aabbCenter), HK_NULL },
		{ "rotatedVertices", &g_legacy461ConvexVerticesShapeFourVectorsClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_rotatedVertices), HK_NULL },
		{ "numVertices", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_numVertices), HK_NULL },
		{ "planeEquations", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_VECTOR4, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_planeEquations), HK_NULL },
		{ "connectivity", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461ConvexVerticesShape, m_connectivity), HK_NULL },
	};

	static hkInternalClassMember g_legacy461CdBodyMembers[] =
	{
		{ "shape", &g_legacy461ConvexVerticesShapeClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461CdBody, m_shape), HK_NULL },
		{ "shapeKey", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461CdBody, m_shapeKey), HK_NULL },
		{ "motion", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461CdBody, m_motion), HK_NULL },
		{ "parent", &g_legacy461CdBodyClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461CdBody, m_parent), HK_NULL },
	};

	static hkInternalClassMember g_legacy461CollidableBoundingVolumeDataMembers[] =
	{
		{ "min", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_min), HK_NULL },
		{ "expansionMin", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_expansionMin), HK_NULL },
		{ "expansionShift", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_expansionShift), HK_NULL },
		{ "max", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_max), HK_NULL },
		{ "expansionMax", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 3, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_expansionMax), HK_NULL },
		{ "padding", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_padding), HK_NULL },
		{ "numChildShapeAabbs", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_numChildShapeAabbs), HK_NULL },
		{ "childShapeAabbs", &g_legacy461AabbUint32Class, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461CollidableBoundingVolumeData, m_childShapeAabbs), HK_NULL },
	};

	static hkInternalClassMember g_legacy461CollidableMembers[] =
	{
		{ "ownerOffset", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_ownerOffset), HK_NULL },
		{ "forceCollideOntoPpu", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_forceCollideOntoPpu), HK_NULL },
		{ "shapeSizeOnSpu", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_shapeSizeOnSpu), HK_NULL },
		{ "broadPhaseHandle", &g_legacy461TypedBroadPhaseHandleClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_broadPhaseHandle), HK_NULL },
		{ "boundingVolumeData", &g_legacy461CollidableBoundingVolumeDataClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_boundingVolumeData), HK_NULL },
		{ "allowedPenetrationDepth", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Collidable, m_allowedPenetrationDepth), HK_NULL },
	};

	static hkInternalClassMember g_legacy461LinkedCollidableMembers[] =
	{
		{ "collisionEntries", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461LinkedCollidable, m_collisionEntries), HK_NULL },
	};

	static hkInternalClassMember g_legacy461MotionStateMembers[] =
	{
		{ "transform", HK_NULL, HK_NULL, hkClassMember::TYPE_TRANSFORM, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_transform), HK_NULL },
		{ "sweptTransform", &g_legacy461SweptTransformClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_sweptTransform), HK_NULL },
		{ "deltaAngle", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_deltaAngle), HK_NULL },
		{ "objectRadius", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_objectRadius), HK_NULL },
		{ "linearDamping", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_linearDamping), HK_NULL },
		{ "angularDamping", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_angularDamping), HK_NULL },
		{ "maxLinearVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_maxLinearVelocity), HK_NULL },
		{ "maxAngularVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_maxAngularVelocity), HK_NULL },
		{ "deactivationClass", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MotionState, m_deactivationClass), HK_NULL },
	};

	static const hkInternalClassEnumItem g_legacy461MotionTypeEnumItems[] =
	{
		{ 0, "MOTION_INVALID" },
		{ 1, "MOTION_DYNAMIC" },
		{ 2, "MOTION_SPHERE_INERTIA" },
		{ 3, "MOTION_STABILIZED_SPHERE_INERTIA" },
		{ 4, "MOTION_BOX_INERTIA" },
		{ 5, "MOTION_STABILIZED_BOX_INERTIA" },
		{ 6, "MOTION_KEYFRAMED" },
		{ 7, "MOTION_FIXED" },
		{ 8, "MOTION_THIN_BOX_INERTIA" },
		{ 9, "MOTION_CHARACTER" },
		{ 10, "MOTION_MAX_ID" },
	};

	static const hkInternalClassEnum g_legacy461MotionEnums[] =
	{
		{ "MotionType", g_legacy461MotionTypeEnumItems, HK_COUNT_OF(g_legacy461MotionTypeEnumItems), HK_NULL, 0 },
	};

	static hkInternalClassMember g_legacy461MotionMembers[] =
	{
		{ "type", HK_NULL, reinterpret_cast<const hkClassEnum*>(&g_legacy461MotionEnums[0]), hkClassMember::TYPE_ENUM, hkClassMember::TYPE_UINT8, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_type), HK_NULL },
		{ "deactivationIntegrateCounter", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationIntegrateCounter), HK_NULL },
		{ "deactivationNumInactiveFrames", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationNumInactiveFrames), HK_NULL },
		{ "motionState", &g_legacy461MotionStateClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_motionState), HK_NULL },
		{ "inertiaAndMassInv", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_inertiaAndMassInv), HK_NULL },
		{ "linearVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_linearVelocity), HK_NULL },
		{ "angularVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_angularVelocity), HK_NULL },
		{ "deactivationRefPosition", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationRefPosition), HK_NULL },
		{ "deactivationRefOrientation", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_deactivationRefOrientation), HK_NULL },
		{ "savedMotion", &g_legacy461MaxSizeMotionClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_savedMotion), HK_NULL },
		{ "savedQualityTypeIndex", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461MaxSizeMotion, m_savedQualityTypeIndex), HK_NULL },
	};

	static hkInternalClassMember g_legacy461SpatialRigidBodyDeactivatorSampleMembers[] =
	{
		{ "refPosition", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivatorSample, m_refPosition), HK_NULL },
		{ "refRotation", HK_NULL, HK_NULL, hkClassMember::TYPE_QUATERNION, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivatorSample, m_refRotation), HK_NULL },
	};

	static hkInternalClassMember g_legacy461SpatialRigidBodyDeactivatorMembers[] =
	{
		{ "highFrequencySample", &g_legacy461SpatialRigidBodyDeactivatorSampleClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_highFrequencySample), HK_NULL },
		{ "lowFrequencySample", &g_legacy461SpatialRigidBodyDeactivatorSampleClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_lowFrequencySample), HK_NULL },
		{ "radiusSqrd", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_radiusSqrd), HK_NULL },
		{ "minHighFrequencyTranslation", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_minHighFrequencyTranslation), HK_NULL },
		{ "minHighFrequencyRotation", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_minHighFrequencyRotation), HK_NULL },
		{ "minLowFrequencyTranslation", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_minLowFrequencyTranslation), HK_NULL },
		{ "minLowFrequencyRotation", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461SpatialRigidBodyDeactivator, m_minLowFrequencyRotation), HK_NULL },
	};

	static hkInternalClassMember g_legacy461WorldObjectMembers[] =
	{
		{ "world", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_world), HK_NULL },
		{ "userData", HK_NULL, HK_NULL, hkClassMember::TYPE_ULONG, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_userData), HK_NULL },
		{ "collidable", &g_legacy461LinkedCollidableClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_collidable), HK_NULL },
		{ "multiThreadCheck", &g_legacy461MultiThreadCheckClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_multithreadLock), HK_NULL },
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_name), HK_NULL },
		{ "properties", &g_legacy461PropertyClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461WorldObject, m_properties), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EntitySpuCollisionCallbackMembers[] =
	{
		{ "util", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySpuCollisionCallback, m_util), HK_NULL },
		{ "capacity", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySpuCollisionCallback, m_capacity), HK_NULL },
		{ "eventFilter", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySpuCollisionCallback, m_eventFilter), HK_NULL },
		{ "userFilter", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461EntitySpuCollisionCallback, m_userFilter), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EntityMembers[] =
	{
		{ "material", &g_legacy461MaterialClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_material), HK_NULL },
		{ "breakOffPartsUtil", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_breakOffPartsUtil), HK_NULL },
		{ "solverData", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_solverData), HK_NULL },
		{ "storageIndex", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_storageIndex), HK_NULL },
		{ "processContactCallbackDelay", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_processContactCallbackDelay), HK_NULL },
		{ "constraintsMaster", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintsMaster), HK_NULL },
		{ "constraintsSlave", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintsSlave), HK_NULL },
		{ "constraintRuntime", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintRuntime), HK_NULL },
		{ "deactivator", &g_legacy461EntityDeactivatorClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_deactivator), HK_NULL },
		{ "simulationIsland", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_simulationIsland), HK_NULL },
		{ "autoRemoveLevel", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_autoRemoveLevel), HK_NULL },
		{ "numUserDatasInContactPointProperties", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_numUserDatasInContactPointProperties), HK_NULL },
		{ "uid", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_uid), HK_NULL },
		{ "spuCollisionCallback", &g_legacy461EntitySpuCollisionCallbackClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_spuCollisionCallback), HK_NULL },
		{ "extendedListeners", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_extendedListeners), HK_NULL },
		{ "motion", &g_legacy461MaxSizeMotionClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_motion), HK_NULL },
		{ "collisionListeners", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_collisionListeners), HK_NULL },
		{ "activationListeners", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_activationListeners), HK_NULL },
		{ "entityListeners", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_entityListeners), HK_NULL },
		{ "actions", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_actions), HK_NULL },
	};

	static hkInternalClassMember g_legacy461EntityMembersBuilding[] =
	{
		{ "material", &g_legacy461MaterialClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_material), HK_NULL },
		{ "breakOffPartsUtil", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_breakOffPartsUtil), HK_NULL },
		{ "solverData", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_solverData), HK_NULL },
		{ "storageIndex", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_storageIndex), HK_NULL },
		{ "processContactCallbackDelay", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_processContactCallbackDelay), HK_NULL },
		{ "constraintsMaster", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintsMaster), HK_NULL },
		{ "constraintsSlave", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintsSlave), HK_NULL },
		{ "constraintRuntime", HK_NULL, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_constraintRuntime), HK_NULL },
		{ "simulationIsland", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_simulationIsland), HK_NULL },
		{ "autoRemoveLevel", HK_NULL, HK_NULL, hkClassMember::TYPE_INT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_autoRemoveLevel), HK_NULL },
		{ "numUserDatasInContactPointProperties", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_numUserDatasInContactPointProperties), HK_NULL },
		{ "uid", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_uid), HK_NULL },
		{ "spuCollisionCallback", &g_legacy461EntitySpuCollisionCallbackClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_spuCollisionCallback), HK_NULL },
		{ "extendedListeners", HK_NULL, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_extendedListeners), HK_NULL },
		{ "motion", &g_legacy461MaxSizeMotionClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_motion), HK_NULL },
		{ "collisionListeners", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_collisionListeners), HK_NULL },
		{ "actions", &g_legacy461EntitySmallArrayClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461Entity, m_actions), HK_NULL },
	};

	static hkInternalClassMember g_legacy461ConstraintAtomMembers[] =
	{
		{ "type", HK_NULL, HK_NULL, hkClassMember::TYPE_ENUM, hkClassMember::TYPE_VOID, 0, hkClassMember::DEPRECATED_SIZE_16, 0, HK_NULL },
	};

	static hkInternalClassMember g_legacy461ModifierConstraintAtomMembers[] =
	{
		{ "child", &g_legacy461ConstraintAtomClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, 0, HK_NULL },
	};

	static hkInternalClassMember g_legacy461ConstraintInstanceMembers[] =
	{
		{ "data", &g_legacy461ConstraintDataClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, 0, HK_NULL },
		{ "constraintModifiers", &g_legacy461ModifierConstraintAtomClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, 0, HK_NULL },
	};

	static const hkInternalClassEnumItem g_legacy461RigidBodyDeactivatorEnumItems[] =
	{
		{ 0, "DEACTIVATOR_INVALID" },
		{ 1, "DEACTIVATOR_NEVER" },
		{ 2, "DEACTIVATOR_SPATIAL" },
		{ 3, "DEACTIVATOR_MAX_ID" },
	};

	static const hkInternalClassEnum g_legacy461RigidBodyDeactivatorEnums[] =
	{
		{ "DeactivatorType", g_legacy461RigidBodyDeactivatorEnumItems, HK_COUNT_OF(g_legacy461RigidBodyDeactivatorEnumItems), HK_NULL, 0 },
	};

	static hkInternalClassMember g_legacy461PhysicsSystemMembers[] =
	{
		{ "rigidBodies", &g_legacy461RigidBodyClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_rigidBodies), HK_NULL },
		{ "constraints", &g_legacy461ConstraintInstanceClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_constraints), HK_NULL },
		{ "actions", &g_legacy461ActionClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_actions), HK_NULL },
		{ "phantoms", &g_legacy461PhantomClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_phantoms), HK_NULL },
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_name), HK_NULL },
		{ "userData", HK_NULL, HK_NULL, hkClassMember::TYPE_ULONG, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_userData), HK_NULL },
		{ "active", HK_NULL, HK_NULL, hkClassMember::TYPE_BOOL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_active), HK_NULL },
	};

	static hkInternalClassMember g_legacy461PhysicsSystemMembersBuilding[] =
	{
		{ "rigidBodies", &g_legacy461RigidBodyClassBuilding, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_rigidBodies), HK_NULL },
		{ "constraints", &g_legacy461ConstraintInstanceClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_constraints), HK_NULL },
		{ "actions", &g_legacy461ActionClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_actions), HK_NULL },
		{ "phantoms", &g_legacy461PhantomClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_phantoms), HK_NULL },
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_name), HK_NULL },
		{ "userData", HK_NULL, HK_NULL, hkClassMember::TYPE_ULONG, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_userData), HK_NULL },
		{ "active", HK_NULL, HK_NULL, hkClassMember::TYPE_BOOL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461PhysicsSystem, m_active), HK_NULL },
	};

	static hkInternalClassMember g_legacy461PhysicsDataMembers[] =
	{
		{ "worldCinfo", &g_legacy461WorldCinfoClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461PhysicsData, m_worldCinfo), HK_NULL },
		{ "systems", &g_legacy461PhysicsSystemClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsData, m_systems), HK_NULL },
	};

	static hkInternalClassMember g_legacy461PhysicsDataMembersBuilding[] =
	{
		{ "worldCinfo", &g_legacy461WorldCinfoClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461PhysicsData, m_worldCinfo), HK_NULL },
		{ "systems", &g_legacy461PhysicsSystemClassBuilding, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_POINTER, 0, 0, HK_OFFSET_OF(Legacy461PhysicsData, m_systems), HK_NULL },
	};

	static hkInternalClassMember g_legacy461WorldCinfoMembers[] =
	{
		{ "gravity", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_gravity), HK_NULL },
		{ "broadPhaseQuerySize", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_broadPhaseQuerySize), HK_NULL },
		{ "broadPhaseWorldAabb", &g_legacy461AabbClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_broadPhaseWorldAabb), HK_NULL },
		{ "collisionTolerance", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_collisionTolerance), HK_NULL },
		{ "collisionFilter", &g_legacy461CollisionFilterClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_collisionFilter), HK_NULL },
		{ "convexListFilter", &g_legacy461ConvexListFilterClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_convexListFilter), HK_NULL },
		{ "memoryWatchDog", &g_legacy461WorldMemoryWatchDogClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy461WorldCinfo, m_memoryWatchDog), HK_NULL },
	};

	hkClass g_legacy461PropertyValueClass(
		"hkPropertyValue",
		HK_NULL,
		sizeof(Legacy461PropertyValue),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PropertyValueMembers),
		HK_COUNT_OF(g_legacy461PropertyValueMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461PropertyClass(
		"hkProperty",
		HK_NULL,
		sizeof(Legacy461Property),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PropertyMembers),
		HK_COUNT_OF(g_legacy461PropertyMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EnvironmentVariableClass(
		"hkxEnvironmentVariable",
		HK_NULL,
		sizeof(Legacy461EnvironmentVariable),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EnvironmentVariableMembers),
		HK_COUNT_OF(g_legacy461EnvironmentVariableMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EnvironmentClass(
		"hkxEnvironment",
		HK_NULL,
		sizeof(Legacy461Environment),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EnvironmentMembers),
		HK_COUNT_OF(g_legacy461EnvironmentMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461AabbClass(
		"hkAabb",
		HK_NULL,
		sizeof(Legacy461Aabb),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461AabbMembers),
		HK_COUNT_OF(g_legacy461AabbMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461AabbUint32Class(
		"hkAabbUint32",
		HK_NULL,
		sizeof(Legacy461AabbUint32),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461AabbUint32Members),
		HK_COUNT_OF(g_legacy461AabbUint32Members),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EntitySmallArrayClass(
		"hkEntitySmallArraySerializeOverrideType",
		HK_NULL,
		sizeof(Legacy461EntitySmallArray),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EntitySmallArrayMembers),
		HK_COUNT_OF(g_legacy461EntitySmallArrayMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461MultiThreadCheckClass(
		"hkMultiThreadLock",
		HK_NULL,
		sizeof(Legacy461MultiThreadCheck),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461MultiThreadCheckMembers),
		HK_COUNT_OF(g_legacy461MultiThreadCheckMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461MaterialClass(
		"hkpMaterial",
		HK_NULL,
		sizeof(Legacy461Material),
		HK_NULL,
		0,
		reinterpret_cast<const hkClassEnum*>(g_legacy461MaterialEnums),
		HK_COUNT_OF(g_legacy461MaterialEnums),
		reinterpret_cast<const hkClassMember*>(g_legacy461MaterialMembers),
		HK_COUNT_OF(g_legacy461MaterialMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461WorldMemoryWatchDogClass(
		"hkWorldMemoryWatchDog",
		&hkReferencedObjectClass,
		sizeof(Legacy461WorldMemoryWatchDog),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461WorldMemoryWatchDogMembers),
		HK_COUNT_OF(g_legacy461WorldMemoryWatchDogMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461CollisionFilterClass(
		"hkpCollisionFilter",
		&hkReferencedObjectClass,
		sizeof(Legacy461CollisionFilter),
		HK_NULL,
		4,
		reinterpret_cast<const hkClassEnum*>(g_legacy461CollisionFilterEnums),
		HK_COUNT_OF(g_legacy461CollisionFilterEnums),
		reinterpret_cast<const hkClassMember*>(g_legacy461CollisionFilterMembers),
		HK_COUNT_OF(g_legacy461CollisionFilterMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ConvexListFilterClass(
		"hkpConvexListFilter",
		&hkReferencedObjectClass,
		sizeof(Legacy461ConvexListFilter),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461BroadPhaseHandleClass(
		"hkpBroadPhaseHandle",
		HK_NULL,
		sizeof(Legacy461BroadPhaseHandle),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461BroadPhaseHandleMembers),
		HK_COUNT_OF(g_legacy461BroadPhaseHandleMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461TypedBroadPhaseHandleClass(
		"hkpTypedBroadPhaseHandle",
		&g_legacy461BroadPhaseHandleClass,
		sizeof(Legacy461TypedBroadPhaseHandle),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461TypedBroadPhaseHandleMembers),
		HK_COUNT_OF(g_legacy461TypedBroadPhaseHandleMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ShapeClass(
		"hkpShape",
		&hkReferencedObjectClass,
		sizeof(Legacy461Shape),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ShapeMembers),
		HK_COUNT_OF(g_legacy461ShapeMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461SphereRepShapeClass(
		"hkpSphereRepShape",
		&g_legacy461ShapeClass,
		sizeof(Legacy461SphereRepShape),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ConvexShapeClass(
		"hkpConvexShape",
		&g_legacy461SphereRepShapeClass,
		sizeof(Legacy461ConvexShape),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ConvexShapeMembers),
		HK_COUNT_OF(g_legacy461ConvexShapeMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461SweptTransformClass(
		"hkSweptTransform",
		HK_NULL,
		sizeof(hkSweptTransform),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461SweptTransformMembers),
		HK_COUNT_OF(g_legacy461SweptTransformMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ConvexVerticesShapeFourVectorsClass(
		"hkConvexVerticesShapeFourVectors",
		HK_NULL,
		sizeof(Legacy461ConvexVerticesShapeFourVectors),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ConvexVerticesShapeFourVectorsMembers),
		HK_COUNT_OF(g_legacy461ConvexVerticesShapeFourVectorsMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ConvexVerticesShapeClass(
		"hkpConvexVerticesShape",
		&g_legacy461ConvexShapeClass,
		sizeof(Legacy461ConvexVerticesShape),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ConvexVerticesShapeMembers),
		HK_COUNT_OF(g_legacy461ConvexVerticesShapeMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461CdBodyClass(
		"hkpCdBody",
		HK_NULL,
		sizeof(Legacy461CdBody),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461CdBodyMembers),
		HK_COUNT_OF(g_legacy461CdBodyMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461CollidableBoundingVolumeDataClass(
		"hkpCollidableBoundingVolumeData",
		HK_NULL,
		sizeof(Legacy461CollidableBoundingVolumeData),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461CollidableBoundingVolumeDataMembers),
		HK_COUNT_OF(g_legacy461CollidableBoundingVolumeDataMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461CollidableClass(
		"hkpCollidable",
		&g_legacy461CdBodyClass,
		sizeof(Legacy461Collidable),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461CollidableMembers),
		HK_COUNT_OF(g_legacy461CollidableMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461LinkedCollidableClass(
		"hkpLinkedCollidable",
		&g_legacy461CollidableClass,
		sizeof(Legacy461LinkedCollidable),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461LinkedCollidableMembers),
		HK_COUNT_OF(g_legacy461LinkedCollidableMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461MotionStateClass(
		"hkMotionState",
		HK_NULL,
		sizeof(Legacy461MotionState),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461MotionStateMembers),
		HK_COUNT_OF(g_legacy461MotionStateMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461MotionClass(
		"hkpMotion",
		&hkReferencedObjectClass,
		sizeof(Legacy461MaxSizeMotion),
		HK_NULL,
		0,
		reinterpret_cast<const hkClassEnum*>(g_legacy461MotionEnums),
		HK_COUNT_OF(g_legacy461MotionEnums),
		reinterpret_cast<const hkClassMember*>(g_legacy461MotionMembers),
		HK_COUNT_OF(g_legacy461MotionMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461KeyframedRigidMotionClass(
		"hkpKeyframedRigidMotion",
		&g_legacy461MotionClass,
		sizeof(Legacy461MaxSizeMotion),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461MaxSizeMotionClass(
		"hkpMaxSizeMotion",
		&g_legacy461KeyframedRigidMotionClass,
		sizeof(Legacy461MaxSizeMotion),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EntityDeactivatorClass(
		"hkEntityDeactivator",
		&hkReferencedObjectClass,
		sizeof(Legacy461EntityDeactivator),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461RigidBodyDeactivatorClass(
		"hkRigidBodyDeactivator",
		&g_legacy461EntityDeactivatorClass,
		sizeof(Legacy461RigidBodyDeactivator),
		HK_NULL,
		0,
		reinterpret_cast<const hkClassEnum*>(g_legacy461RigidBodyDeactivatorEnums),
		HK_COUNT_OF(g_legacy461RigidBodyDeactivatorEnums),
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461SpatialRigidBodyDeactivatorSampleClass(
		"hkSpatialRigidBodyDeactivatorSample",
		HK_NULL,
		sizeof(Legacy461SpatialRigidBodyDeactivatorSample),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461SpatialRigidBodyDeactivatorSampleMembers),
		HK_COUNT_OF(g_legacy461SpatialRigidBodyDeactivatorSampleMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461SpatialRigidBodyDeactivatorClass(
		"hkSpatialRigidBodyDeactivator",
		&g_legacy461RigidBodyDeactivatorClass,
		sizeof(Legacy461SpatialRigidBodyDeactivator),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461SpatialRigidBodyDeactivatorMembers),
		HK_COUNT_OF(g_legacy461SpatialRigidBodyDeactivatorMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461WorldObjectClass(
		"hkpWorldObject",
		&hkReferencedObjectClass,
		sizeof(Legacy461WorldObject),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461WorldObjectMembers),
		HK_COUNT_OF(g_legacy461WorldObjectMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EntitySpuCollisionCallbackClass(
		"hkpEntitySpuCollisionCallback",
		HK_NULL,
		sizeof(Legacy461EntitySpuCollisionCallback),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EntitySpuCollisionCallbackMembers),
		HK_COUNT_OF(g_legacy461EntitySpuCollisionCallbackMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EntityClassBuilding(
		"hkpEntity",
		&g_legacy461WorldObjectClass,
		512,
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EntityMembersBuilding),
		HK_COUNT_OF(g_legacy461EntityMembersBuilding),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461EntityClass(
		"hkpEntity",
		&g_legacy461WorldObjectClass,
		sizeof(Legacy461Entity),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461EntityMembers),
		HK_COUNT_OF(g_legacy461EntityMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461RigidBodyClassBuilding(
		"hkpRigidBody",
		&g_legacy461EntityClassBuilding,
		512,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461RigidBodyClass(
		"hkpRigidBody",
		&g_legacy461EntityClass,
		sizeof(Legacy461RigidBody),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461ConstraintDataClass("hkpConstraintData", HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, HK_NULL, 0);
	hkClass g_legacy461ConstraintAtomClass(
		"hkpConstraintAtom",
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ConstraintAtomMembers),
		HK_COUNT_OF(g_legacy461ConstraintAtomMembers),
		HK_NULL,
		HK_NULL,
		0);
	hkClass g_legacy461ModifierConstraintAtomClass(
		"hkpModifierConstraintAtom",
		&g_legacy461ConstraintAtomClass,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ModifierConstraintAtomMembers),
		HK_COUNT_OF(g_legacy461ModifierConstraintAtomMembers),
		HK_NULL,
		HK_NULL,
		0);
	hkClass g_legacy461ConstraintInstanceClass(
		"hkpConstraintInstance",
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461ConstraintInstanceMembers),
		HK_COUNT_OF(g_legacy461ConstraintInstanceMembers),
		HK_NULL,
		HK_NULL,
		0);
	hkClass g_legacy461ActionClass("hkpAction", HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, HK_NULL, 0);
	hkClass g_legacy461PhantomClass("hkpPhantom", HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, 0, HK_NULL, HK_NULL, 0);

	hkClass g_legacy461WorldCinfoClass(
		"hkpWorldCinfo",
		&hkReferencedObjectClass,
		sizeof(Legacy461WorldCinfo),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461WorldCinfoMembers),
		HK_COUNT_OF(g_legacy461WorldCinfoMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461PhysicsSystemClass(
		"hkpPhysicsSystem",
		&hkReferencedObjectClass,
		sizeof(Legacy461PhysicsSystem),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PhysicsSystemMembers),
		HK_COUNT_OF(g_legacy461PhysicsSystemMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461PhysicsSystemClassBuilding(
		"hkpPhysicsSystem",
		&hkReferencedObjectClass,
		sizeof(Legacy461PhysicsSystem),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PhysicsSystemMembersBuilding),
		HK_COUNT_OF(g_legacy461PhysicsSystemMembersBuilding),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461PhysicsDataClass(
		"hkpPhysicsData",
		&hkReferencedObjectClass,
		sizeof(Legacy461PhysicsData),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PhysicsDataMembers),
		HK_COUNT_OF(g_legacy461PhysicsDataMembers),
		HK_NULL,
		HK_NULL,
		0);

	hkClass g_legacy461PhysicsDataClassBuilding(
		"hkpPhysicsData",
		&hkReferencedObjectClass,
		sizeof(Legacy461PhysicsData),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_legacy461PhysicsDataMembersBuilding),
		HK_COUNT_OF(g_legacy461PhysicsDataMembersBuilding),
		HK_NULL,
		HK_NULL,
		0);

	inline const hkClass* selectLegacyPhysicsDataClass(bool useBuildingLayout)
	{
		return useBuildingLayout ? &g_legacy461PhysicsDataClassBuilding : &g_legacy461PhysicsDataClass;
	}

	inline const hkClass* selectLegacyPhysicsSystemClass(bool useBuildingLayout)
	{
		return useBuildingLayout ? &g_legacy461PhysicsSystemClassBuilding : &g_legacy461PhysicsSystemClass;
	}

	inline const hkClass* selectLegacyRigidBodyClass(bool useBuildingLayout)
	{
		return useBuildingLayout ? &g_legacy461RigidBodyClassBuilding : &g_legacy461RigidBodyClass;
	}
}

#endif