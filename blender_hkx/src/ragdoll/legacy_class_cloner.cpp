#include "legacy_class_cloner.h"

#include <string.h>

#include <Common/Base/Reflection/hkClassEnum.h>

LegacyClassCloner::LegacyClassCloner()
	: m_override(HK_NULL)
{
}

void LegacyClassCloner::setOverride(ClassOverride* classOverride)
{
	m_override = classOverride;
}

const hkClass* LegacyClassCloner::mapClass(const hkClass* current)
{
	if (current == HK_NULL)
	{
		return HK_NULL;
	}

	std::map<const hkClass*, hkClass*>::const_iterator existing = m_classClones.find(current);
	if (existing != m_classClones.end())
	{
		return existing->second;
	}

	if (m_override != HK_NULL)
	{
		const hkClass* overridden = m_override->mapClass(current, *this);
		if (overridden != HK_NULL)
		{
			return overridden;
		}
	}

	const std::string mapped = mappedName(current->getName());
	if (mapped == current->getName())
	{
		return current;
	}

	return cloneByRename(current, mapped);
}

const hkClass* LegacyClassCloner::cloneByRename(const hkClass* current, const std::string& mapped)
{
	if (m_inProgress.find(current) != m_inProgress.end())
	{
		return current;
	}
	m_inProgress[current] = true;

	const hkClass* mappedParent = mapClass(current->getParent());
	const int numInterfaces = current->getNumDeclaredInterfaces();
	const hkClass** interfaces = HK_NULL;
	if (numInterfaces > 0)
	{
		interfaces = new const hkClass*[numInterfaces];
		m_interfaceArrays.push_back(interfaces);
		for (int index = 0; index < numInterfaces; ++index)
		{
			interfaces[index] = mapClass(current->getDeclaredInterface(index));
		}
	}

	const int numMembers = current->getNumDeclaredMembers();
	hkInternalClassMember* members = HK_NULL;
	if (numMembers > 0)
	{
		members = new hkInternalClassMember[numMembers];
		m_memberArrays.push_back(members);
		for (int index = 0; index < numMembers; ++index)
		{
			const hkClassMember& member = current->getDeclaredMember(index);
			members[index].m_name = member.getName();
			members[index].m_class = member.hasClass() ? mapClass(member.getClass()) : HK_NULL;
			members[index].m_enum = member.hasEnumClass() ? &member.getEnumClass() : HK_NULL;
			members[index].m_type = static_cast<hkUint8>(member.getType());
			members[index].m_subtype = static_cast<hkUint8>(member.getSubType());
			members[index].m_cArraySize = static_cast<hkUint16>(member.getCstyleArraySize());
			members[index].m_flags = static_cast<hkUint16>(member.getFlags().get());
			members[index].m_offset = static_cast<hkUint16>(member.getOffset());
			members[index].m_attributes = HK_NULL;
		}
	}

	const hkClassEnum* enums = current->getNumDeclaredEnums() > 0 ? &current->getDeclaredEnum(0) : HK_NULL;
	char* ownedName = duplicateString(mapped);
	hkClass* clone = new hkClass(
		ownedName,
		mappedParent,
		current->getObjectSize(),
		interfaces,
		numInterfaces,
		enums,
		current->getNumDeclaredEnums(),
		reinterpret_cast<const hkClassMember*>(members),
		numMembers,
		HK_NULL,
		HK_NULL,
		current->getFlags().get());

	registerClone(current, clone, ownedName);
	m_inProgress.erase(current);
	return clone;
}

std::string LegacyClassCloner::mappedName(const char* currentName)
{
	if (currentName == HK_NULL)
	{
		return std::string();
	}

	if (strncmp(currentName, "hka", 3) == 0)
	{
		return std::string("hk") + (currentName + 3);
	}

	if (strncmp(currentName, "hkp", 3) == 0)
	{
		return std::string("hk") + (currentName + 3);
	}

	return std::string(currentName);
}

hkInternalClassMember* LegacyClassCloner::allocMembers(int count)
{
	hkInternalClassMember* members = new hkInternalClassMember[count];
	m_memberArrays.push_back(members);
	memset(members, 0, sizeof(hkInternalClassMember) * count);
	return members;
}

void LegacyClassCloner::setMember(hkInternalClassMember& member, const char* name, const hkClass* classRef,
	const hkClassEnum* enumRef, hkClassMember::Type type, hkClassMember::Type subtype,
	int cArraySize, int flags, hk_size_t offset)
{
	member.m_name = name;
	member.m_class = classRef;
	member.m_enum = enumRef;
	member.m_type = static_cast<hkUint8>(type);
	member.m_subtype = static_cast<hkUint8>(subtype);
	member.m_cArraySize = static_cast<hkUint16>(cArraySize);
	member.m_flags = static_cast<hkUint16>(flags);
	member.m_offset = static_cast<hkUint16>(offset);
	member.m_attributes = HK_NULL;
}

char* LegacyClassCloner::duplicateString(const std::string& value)
{
	char* copy = new char[value.length() + 1];
	memcpy(copy, value.c_str(), value.length() + 1);
	return copy;
}

const hkClass* LegacyClassCloner::findClone(const hkClass* live) const
{
	std::map<const hkClass*, hkClass*>::const_iterator existing = m_classClones.find(live);
	return existing != m_classClones.end() ? existing->second : HK_NULL;
}

void LegacyClassCloner::registerClone(const hkClass* live, hkClass* clone, char* ownedName)
{
	if (ownedName != HK_NULL)
	{
		m_ownedClassNames.push_back(ownedName);
	}
	m_ownedClasses.push_back(clone);
	m_classClones[live] = clone;
}
