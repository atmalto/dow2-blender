#ifndef DOW2_RAGDOLL_LEGACY_MOTION_H
#define DOW2_RAGDOLL_LEGACY_MOTION_H

#include <vector>

#include "legacy_class_cloner.h"

class hkpRigidBody;

// Emits custom Havok 4.5.1-r1 definitions for the motion hierarchy
// (hkMotionState / hkMotion / hkKeyframedRigidMotion / hkMaxSizeMotion), whose
// field layout genuinely differs from Havok 5.5: in 4.5.1 maxLinearVelocity /
// maxAngularVelocity are hkReal (float) placed BEFORE the damping fields, with
// wider deactivation fields. Plug into LegacyClassCloner via setOverride().
class MotionClassOverride : public LegacyClassCloner::ClassOverride
{
public:
	virtual const hkClass* mapClass(const hkClass* current, LegacyClassCloner& cloner);

private:
	const hkClass* buildMotionStateClass(const hkClass* liveMotionState, LegacyClassCloner& cloner);
	void buildMotionClasses(const hkClass* liveMaxSize, LegacyClassCloner& cloner);
};

// Bytes of the entity region that the oversized 4.5.1 motion image overwrites,
// captured so they can be restored after serialization.
struct MotionOverflowSave
{
	char* dst;
	std::vector<char> bytes;
};

// Overwrite each rigid body's embedded 5.5 motion with a 4.5.1-layout image in
// place, preserving the hkReferencedObject base. Any bytes written past the 5.5
// slot are captured in `saves` for later restoration.
void marshalMotionsTo451(const std::vector<hkpRigidBody*>& bodies, std::vector<MotionOverflowSave>& saves);

// Restore the bytes captured by marshalMotionsTo451().
void restoreMotionOverflows(std::vector<MotionOverflowSave>& saves);

#endif
