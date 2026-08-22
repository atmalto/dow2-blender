#ifndef DOW2_RAGDOLL_LEGACY_CLASS_CLONER_H
#define DOW2_RAGDOLL_LEGACY_CLASS_CLONER_H

#include <map>
#include <string>
#include <vector>

#include <Common/Base/hkBase.h>
#include <Common/Base/Reflection/hkClass.h>
#include <Common/Base/Reflection/hkClassMember.h>
#include <Common/Base/Reflection/hkInternalClassMember.h>

class hkClassEnum;

// Clonesa live Havok 5.5 reflection class graph into a renamed Havok 4.5.1-r1
// variant (hka*/hkp* -> hk*). This engine only knows how to rename and copy
// reflection members; classes whose byte layout genuinely changed between
// versions are delegared to a ClassOverride so the cloner itself stays free of
// any type-specific knowledge
class LegacyClassCloner
{
public:
	// Hook for classes that need a custom 4.5.1 definition instead of a plain
	// rename clone (ex: the motion hierarchy, whose field layout changed
	// between versions
	class ClassOverride
	{
	public:
		virtual ~ClassOverride() {}

		// Return a mapped class for `current`, or HK_NULL to fallback to the
		// defualt rename clone. Implementations may call cloner.mapClass() to map
		// sub-classes and must register any class they build via
		// cloner.registerClone() so later lookups will resolve to it.
		virtual const hkClass* mapClass(const hkClass* current, LegacyClassCloner& cloner) = 0;
	};

	LegacyClassCloner();

	void setOverride(ClassOverride* classOverride);

	// Map a live 5.5 class to its 4.5.1 counterpart, recursively mapping parents,
	// interfaces and member classes. Returns `current` unchanged when the name
	// needs no remap and no override applies.
	const hkClass* mapClass(const hkClass* current);

	// Name remap rule: hka*/hkp* -> hk*, everything else unchanged.
	static std::string mappedName(const char* currentName);

	// --- utils for ClassOverride implementations building custom classes ---

	// allocate a zero'ed member array owned (and later leaked) by the cloner
	hkInternalClassMember* allocMembers(int count);

	static void setMember(hkInternalClassMember& member, const char* name, const hkClass* classRef,
		const hkClassEnum* enumRef, hkClassMember::Type type, hkClassMember::Type subtype,
		int cArraySize, int flags, hk_size_t offset);

	char* duplicateString(const std::string& value);

	// Look up a previously registered clone, or HK_NULL.
	const hkClass* findClone(const hkClass* live) const;

	// Record a built clone so later mapClass()/findClone() calls resolve to it.
	// `ownedName`, when non-null, is tracked for lifetime alongside `clone`.
	void registerClone(const hkClass* live, hkClass* clone, char* ownedName);

private:
	const hkClass* cloneByRename(const hkClass* current, const std::string& mapped);

	std::map<const hkClass*, hkClass*> m_classClones;
	std::map<const hkClass*, bool> m_inProgress;
	std::vector<const hkClass**> m_interfaceArrays;
	std::vector<hkInternalClassMember*> m_memberArrays;
	std::vector<char*> m_ownedClassNames;
	std::vector<hkClass*> m_ownedClasses;
	ClassOverride* m_override;
};

#endif
