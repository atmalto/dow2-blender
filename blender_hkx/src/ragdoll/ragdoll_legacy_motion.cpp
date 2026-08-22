#include "ragdoll_legacy_motion.h"

#include <string.h>
#include <string>

#include <Common/Base/hkBase.h>
#include <Common/Base/Math/SweptTransform/hkSweptTransform.h>
#include <Common/Base/Object/hkReferencedObject.h>
#include <Common/Base/Reflection/hkClass.h>
#include <Common/Base/Reflection/hkClassEnum.h>
#include <Common/Base/Reflection/hkClassMember.h>
#include <Common/Base/Reflection/hkInternalClassMember.h>
#include <Common/Base/Types/Physics/MotionState/hkMotionState.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/Motion/hkpMotion.h>
#include <Physics/Dynamics/Motion/Rigid/hkpKeyframedRigidMotion.h>

namespace
{
	// Havok 4.5.1-r1 motion layout (ground truth: 2007 SDK compat registry,
	// hkHavok451r1Classes.cpp). Note maxLinearVelocity / maxAngularVelocity are
	// hkReal here and precede the damping fields; the 5.5 SDK stores them as
	// hkUFloat8 after damping. Emitting the 5.5 layout under the 4.5.1 name makes
	// the runtime read a frozen maxLinearVelocity (~0.01), so we describe and
	// marshal the true 4.5.1 layout instead.
	struct Legacy451MotionState
	{
		hkTransform m_transform;
		hkSweptTransform m_sweptTransform;
		hkVector4 m_deltaAngle;
		hkReal m_objectRadius;
		hkReal m_maxLinearVelocity;
		hkReal m_maxAngularVelocity;
		hkReal m_linearDamping;
		hkReal m_angularDamping;
		hkUint16 m_deactivationClass;
		hkUint16 m_deactivationCounter;
		hkUint32 m_deactivationRefOrientation[2];
	};

	struct Legacy451MaxSizeMotion : public hkReferencedObject
	{
		hkUint8 m_type;
		hkUint8 m_deactivationIntegrateCounter;
		hkUint16 m_deactivationNumInactiveFrames[2];
		Legacy451MotionState m_motionState;
		hkVector4 m_inertiaAndMassInv;
		hkVector4 m_linearVelocity;
		hkVector4 m_angularVelocity;
		hkVector4 m_deactivationRefPosition[2];
		void* m_savedMotion;
		hkInt32 m_savedQualityTypeIndex;
	};
}

const hkClass* MotionClassOverride::mapClass(const hkClass* current, LegacyClassCloner& cloner)
{
	const std::string name = LegacyClassCloner::mappedName(current->getName());

	// hkMaxSizeMotion is the entry point (the entity embeds it); building it also
	// builds the hkMotion / hkKeyframedRigidMotion / hkMotionState chain.
	if (name == "hkMaxSizeMotion")
	{
		buildMotionClasses(current, cloner);
		return cloner.findClone(current);
	}

	if (name == "hkMotionState")
	{
		return buildMotionStateClass(current, cloner);
	}

	// hkMotion / hkKeyframedRigidMotion are only reached as parents of
	// hkMaxSizeMotion, which builds and registers them; anything else falls back
	// to the cloner's default rename.
	return HK_NULL;
}

// Build the 4.5.1-r1 hkMotionState class (float maxLinear/maxAngular velocity
// BEFORE damping, UINT16 deactivation fields). The swept transform sub-class is
// stable between versions, so reuse the mapped live one.
const hkClass* MotionClassOverride::buildMotionStateClass(const hkClass* liveMotionState, LegacyClassCloner& cloner)
{
	const hkClass* cached = cloner.findClone(liveMotionState);
	if (cached != HK_NULL)
	{
		return cached;
	}

	const hkClass* sweptClass = HK_NULL;
	const hkClassMember* sweptMember = liveMotionState->getMemberByName("sweptTransform");
	if (sweptMember != HK_NULL && sweptMember->hasClass())
	{
		sweptClass = cloner.mapClass(sweptMember->getClass());
	}

	hkInternalClassMember* members = cloner.allocMembers(11);
	LegacyClassCloner::setMember(members[0], "transform", HK_NULL, HK_NULL, hkClassMember::TYPE_TRANSFORM, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_transform));
	LegacyClassCloner::setMember(members[1], "sweptTransform", sweptClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_sweptTransform));
	LegacyClassCloner::setMember(members[2], "deltaAngle", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_deltaAngle));
	LegacyClassCloner::setMember(members[3], "objectRadius", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_objectRadius));
	LegacyClassCloner::setMember(members[4], "maxLinearVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_maxLinearVelocity));
	LegacyClassCloner::setMember(members[5], "maxAngularVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_maxAngularVelocity));
	LegacyClassCloner::setMember(members[6], "linearDamping", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_linearDamping));
	LegacyClassCloner::setMember(members[7], "angularDamping", HK_NULL, HK_NULL, hkClassMember::TYPE_REAL, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_angularDamping));
	LegacyClassCloner::setMember(members[8], "deactivationClass", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_deactivationClass));
	LegacyClassCloner::setMember(members[9], "deactivationCounter", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MotionState, m_deactivationCounter));
	LegacyClassCloner::setMember(members[10], "deactivationRefOrientation", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT32, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy451MotionState, m_deactivationRefOrientation));

	char* ownedName = cloner.duplicateString(std::string("hkMotionState"));
	hkClass* clone = new hkClass(
		ownedName,
		HK_NULL,
		sizeof(Legacy451MotionState),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(members),
		11,
		HK_NULL,
		HK_NULL,
		liveMotionState->getFlags().get());

	cloner.registerClone(liveMotionState, clone, ownedName);
	return clone;
}

// Build the full 4.5.1-r1 motion container hierarchy (hkMotion /
// hkKeyframedRigidMotion / hkMaxSizeMotion) plus the motion state, wired with
// the member offsets of the marshaled image.
void MotionClassOverride::buildMotionClasses(const hkClass* liveMaxSize, LegacyClassCloner& cloner)
{
	const hkClass* liveKeyframed = liveMaxSize->getParent();
	const hkClass* liveMotion = liveKeyframed != HK_NULL ? liveKeyframed->getParent() : HK_NULL;
	if (liveMotion == HK_NULL)
	{
		return;
	}

	const hkClassMember* motionStateMember = liveMotion->getMemberByName("motionState");
	const hkClass* liveMotionState = (motionStateMember != HK_NULL && motionStateMember->hasClass())
		? motionStateMember->getClass()
		: HK_NULL;
	const hkClass* motionStateClass = (liveMotionState != HK_NULL) ? buildMotionStateClass(liveMotionState, cloner) : HK_NULL;

	const hkClass* mappedRef = cloner.mapClass(liveMotion->getParent());

	const hkClassMember* liveType = liveMotion->getMemberByName("type");
	const hkClassEnum* typeEnum = (liveType != HK_NULL && liveType->hasEnumClass()) ? &liveType->getEnumClass() : HK_NULL;
	const hkClassEnum* motionEnums = liveMotion->getNumDeclaredEnums() > 0 ? &liveMotion->getDeclaredEnum(0) : HK_NULL;

	hkInternalClassMember* motionMembers = cloner.allocMembers(8);
	LegacyClassCloner::setMember(motionMembers[0], "type", HK_NULL, typeEnum, hkClassMember::TYPE_ENUM, hkClassMember::TYPE_UINT8, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_type));
	LegacyClassCloner::setMember(motionMembers[1], "deactivationIntegrateCounter", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT8, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_deactivationIntegrateCounter));
	LegacyClassCloner::setMember(motionMembers[2], "deactivationNumInactiveFrames", HK_NULL, HK_NULL, hkClassMember::TYPE_UINT16, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_deactivationNumInactiveFrames));
	LegacyClassCloner::setMember(motionMembers[3], "motionState", motionStateClass, HK_NULL, hkClassMember::TYPE_STRUCT, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_motionState));
	LegacyClassCloner::setMember(motionMembers[4], "inertiaAndMassInv", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_inertiaAndMassInv));
	LegacyClassCloner::setMember(motionMembers[5], "linearVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_linearVelocity));
	LegacyClassCloner::setMember(motionMembers[6], "angularVelocity", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_angularVelocity));
	LegacyClassCloner::setMember(motionMembers[7], "deactivationRefPosition", HK_NULL, HK_NULL, hkClassMember::TYPE_VECTOR4, hkClassMember::TYPE_VOID, 2, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_deactivationRefPosition));

	char* motionName = cloner.duplicateString(std::string("hkMotion"));
	hkClass* motionClass = new hkClass(
		motionName,
		mappedRef,
		static_cast<int>(HK_OFFSET_OF(Legacy451MaxSizeMotion, m_savedMotion)),
		HK_NULL,
		0,
		motionEnums,
		liveMotion->getNumDeclaredEnums(),
		reinterpret_cast<const hkClassMember*>(motionMembers),
		8,
		HK_NULL,
		HK_NULL,
		liveMotion->getFlags().get());
	cloner.registerClone(liveMotion, motionClass, motionName);

	// Reserve stable storage for hkMaxSizeMotion so the keyframed motion's
	// savedMotion pointer can reference it before it is constructed.
	hkClass* maxSizeClass = static_cast<hkClass*>(::operator new(sizeof(hkClass)));

	hkInternalClassMember* keyMembers = cloner.allocMembers(2);
	LegacyClassCloner::setMember(keyMembers[0], "savedMotion", maxSizeClass, HK_NULL, hkClassMember::TYPE_POINTER, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_savedMotion));
	LegacyClassCloner::setMember(keyMembers[1], "savedQualityTypeIndex", HK_NULL, HK_NULL, hkClassMember::TYPE_INT32, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(Legacy451MaxSizeMotion, m_savedQualityTypeIndex));

	char* keyName = cloner.duplicateString(std::string("hkKeyframedRigidMotion"));
	hkClass* keyframedClass = new hkClass(
		keyName,
		motionClass,
		sizeof(Legacy451MaxSizeMotion),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(keyMembers),
		2,
		HK_NULL,
		HK_NULL,
		liveKeyframed->getFlags().get());
	cloner.registerClone(liveKeyframed, keyframedClass, keyName);

	char* maxName = cloner.duplicateString(std::string("hkMaxSizeMotion"));
	new (maxSizeClass) hkClass(
		maxName,
		keyframedClass,
		sizeof(Legacy451MaxSizeMotion),
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		0,
		HK_NULL,
		HK_NULL,
		liveMaxSize->getFlags().get());
	cloner.registerClone(liveMaxSize, maxSizeClass, maxName);
}

void marshalMotionsTo451(const std::vector<hkpRigidBody*>& bodies, std::vector<MotionOverflowSave>& saves)
{
	const hk_size_t baseOffset = HK_OFFSET_OF(Legacy451MaxSizeMotion, m_type);
	const hk_size_t slotSize = sizeof(hkpMaxSizeMotion);
	const hk_size_t imageSize = sizeof(Legacy451MaxSizeMotion);
	const hk_size_t overflow = imageSize > slotSize ? (imageSize - slotSize) : 0;

	for (size_t i = 0; i < bodies.size(); ++i)
	{
		hkpRigidBody* body = bodies[i];
		if (body == HK_NULL)
		{
			continue;
		}

		hkpMotion* motion = body->getMotion();
		if (motion == HK_NULL)
		{
			continue;
		}

		const hkMotionState* ms = motion->getMotionState();

		Legacy451MaxSizeMotion image;
		memset(reinterpret_cast<char*>(&image) + baseOffset, 0, imageSize - baseOffset);

		image.m_type = static_cast<hkUint8>(motion->getType());
		image.m_deactivationIntegrateCounter = motion->m_deactivationIntegrateCounter;
		image.m_deactivationNumInactiveFrames[0] = motion->m_deactivationNumInactiveFrames[0];
		image.m_deactivationNumInactiveFrames[1] = motion->m_deactivationNumInactiveFrames[1];

		image.m_motionState.m_transform = ms->getTransform();
		image.m_motionState.m_sweptTransform = ms->getSweptTransform();
		image.m_motionState.m_deltaAngle = ms->m_deltaAngle;
		image.m_motionState.m_objectRadius = ms->m_objectRadius;
		image.m_motionState.m_maxLinearVelocity = 200.0f;
		image.m_motionState.m_maxAngularVelocity = 200.0f;
		image.m_motionState.m_linearDamping = ms->m_linearDamping;
		image.m_motionState.m_angularDamping = ms->m_angularDamping;
		image.m_motionState.m_deactivationClass = 2;
		image.m_motionState.m_deactivationCounter = 20;
		image.m_motionState.m_deactivationRefOrientation[0] = 0;
		image.m_motionState.m_deactivationRefOrientation[1] = 0;

		image.m_inertiaAndMassInv = motion->m_inertiaAndMassInv;
		image.m_linearVelocity = motion->m_linearVelocity;
		image.m_angularVelocity = motion->m_angularVelocity;
		image.m_deactivationRefPosition[0] = motion->m_deactivationRefPosition[0];
		image.m_deactivationRefPosition[1] = motion->m_deactivationRefPosition[1];
		image.m_savedMotion = HK_NULL;
		image.m_savedQualityTypeIndex = static_cast<hkInt32>(motion->m_savedQualityTypeIndex);

		char* motionBase = reinterpret_cast<char*>(motion);
		if (overflow > 0)
		{
			MotionOverflowSave save;
			save.dst = motionBase + slotSize;
			save.bytes.assign(save.dst, save.dst + overflow);
			saves.push_back(save);
		}

		memcpy(
			motionBase + baseOffset,
			reinterpret_cast<char*>(&image) + baseOffset,
			imageSize - baseOffset);
	}
}

void restoreMotionOverflows(std::vector<MotionOverflowSave>& saves)
{
	for (size_t i = 0; i < saves.size(); ++i)
	{
		memcpy(saves[i].dst, &saves[i].bytes[0], saves[i].bytes.size());
	}
}
