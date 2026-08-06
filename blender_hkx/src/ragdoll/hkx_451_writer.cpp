#include "hkx_451_writer.h"

#include <map>
#include <stdio.h>
#include <string>
#include <vector>

#include <Animation/Animation/Mapper/hkaSkeletonMapper.h>
#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>
#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Reflection/hkClass.h>
#include <Common/Base/Reflection/hkClassEnum.h>
#include <Common/Base/Reflection/hkClassMember.h>
#include <Common/Base/Reflection/hkInternalClassMember.h>
#include <Common/Base/System/Io/OStream/hkOStream.h>
#include <Common/Serialize/Packfile/Binary/hkBinaryPackfileWriter.h>
#include <Common/Serialize/Packfile/hkPackfileWriter.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>
#include <Common/Serialize/Util/hkStructureLayout.h>
#include <Physics/Dynamics/Constraint/Motor/Position/hkpPositionConstraintMotor.h>
#include <Physics/Utilities/Serialize/hkpPhysicsData.h>

namespace
{
	static const char* const kTargetVersion = "Havok-4.5.1-r1";

	struct LegacyEnvironmentVariable
	{
		const char* m_name;
		const char* m_value;
	};

	struct LegacyEnvironment
	{
		hkArray<LegacyEnvironmentVariable> m_variables;
	};

	static hkInternalClassMember g_environmentVariableMembers[] =
	{
		{ "name", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(LegacyEnvironmentVariable, m_name), HK_NULL },
		{ "value", HK_NULL, HK_NULL, hkClassMember::TYPE_CSTRING, hkClassMember::TYPE_VOID, 0, 0, HK_OFFSET_OF(LegacyEnvironmentVariable, m_value), HK_NULL },
	};

	hkClass g_environmentVariableClass(
		"hkxEnvironmentVariable",
		HK_NULL,
		sizeof(LegacyEnvironmentVariable),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_environmentVariableMembers),
		HK_COUNT_OF(g_environmentVariableMembers),
		HK_NULL,
		HK_NULL,
		0);

	static hkInternalClassMember g_environmentMembers[] =
	{
		{ "variables", &g_environmentVariableClass, HK_NULL, hkClassMember::TYPE_ARRAY, hkClassMember::TYPE_STRUCT, 0, 0, HK_OFFSET_OF(LegacyEnvironment, m_variables), HK_NULL },
	};

	hkClass g_environmentClass(
		"hkxEnvironment",
		HK_NULL,
		sizeof(LegacyEnvironment),
		HK_NULL,
		0,
		HK_NULL,
		0,
		reinterpret_cast<const hkClassMember*>(g_environmentMembers),
		HK_COUNT_OF(g_environmentMembers),
		HK_NULL,
		HK_NULL,
		0);

	class LegacyClassCloner
	{
	public:
		LegacyClassCloner()
		{
		}

		const hkClass* mapClass(const hkClass* current)
		{
			if (current == HK_NULL)
			{
				return HK_NULL;
			}

			const std::string mappedName = getMappedName(current->getName());
			if (mappedName == current->getName())
			{
				return current;
			}

			std::map<const hkClass*, hkClass*>::const_iterator existing = m_classClones.find(current);
			if (existing != m_classClones.end())
			{
				return existing->second;
			}

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
			char* ownedName = duplicateString(mappedName);
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

			m_ownedClassNames.push_back(ownedName);
			m_ownedClasses.push_back(clone);
			m_classClones[current] = clone;
			m_inProgress.erase(current);
			return clone;
		}

	private:
		static std::string getMappedName(const char* currentName)
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

		char* duplicateString(const std::string& value)
		{
			char* copy = new char[value.length() + 1];
			memcpy(copy, value.c_str(), value.length() + 1);
			return copy;
		}

		std::map<const hkClass*, hkClass*> m_classClones;
		std::map<const hkClass*, bool> m_inProgress;
		std::vector<const hkClass**> m_interfaceArrays;
		std::vector<hkInternalClassMember*> m_memberArrays;
		std::vector<char*> m_ownedClassNames;
		std::vector<hkClass*> m_ownedClasses;
	};

	class LegacyClassListener : public hkPackfileWriter::AddObjectListener
	{
	public:
		explicit LegacyClassListener(LegacyClassCloner& cloner)
			: m_cloner(cloner)
		{
		}

		virtual void addObjectCallback(ObjectPointer& objectPointer, ClassPointer& classPointer)
		{
			(void)objectPointer;
			if (classPointer != HK_NULL)
			{
				classPointer = m_cloner.mapClass(classPointer);
			}
		}

	private:
		LegacyClassCloner& m_cloner;
	};

	void populateEnvironment(LegacyEnvironment& environment)
	{
		environment.m_variables.setSize(3);
		environment.m_variables[0].m_name = "modeller";
		environment.m_variables[0].m_value = "Blender 4.3";
		environment.m_variables[1].m_name = "configuration";
		environment.m_variables[1].m_value = "Default";
		environment.m_variables[2].m_name = "infoString";
		environment.m_variables[2].m_value = "Generated by dow2_tools ragdoll_workspace";
	}
}

bool writeRagdollGraphAs451(const RagdollBuildResult& buildResult, const char* outputFile)
{
	if (outputFile == HK_NULL
		|| buildResult.animationContainer == HK_NULL
		|| buildResult.physicsData == HK_NULL
		|| buildResult.ragdollInstance == HK_NULL
		|| buildResult.ragdollToAnimationMapper == HK_NULL
		|| buildResult.animationToRagdollMapper == HK_NULL)
	{
		return false;
	}

	printf("Preparing legacy class mapping...\n");
	fflush(stdout);
	LegacyClassCloner cloner;
	const hkClass* animationContainerClass = cloner.mapClass(&hkaAnimationContainerClass);
	const hkClass* physicsDataClass = cloner.mapClass(&hkpPhysicsDataClass);
	const hkClass* ragdollInstanceClass = cloner.mapClass(&hkaRagdollInstanceClass);
	const hkClass* skeletonMapperClass = cloner.mapClass(&hkaSkeletonMapperClass);

	printf("Preparing legacy root container...\n");
	fflush(stdout);
	LegacyEnvironment environment;
	populateEnvironment(environment);

	hkRootLevelContainer root;
	root.m_namedVariants = hkAllocate<hkRootLevelContainer::NamedVariant>(6, HK_MEMORY_CLASS_SERIALIZE);
	root.m_numNamedVariants = 6;
	root.m_namedVariants[0].set("Environment Data", &environment, &g_environmentClass);
	root.m_namedVariants[1].set("Animation Container", buildResult.animationContainer, animationContainerClass);
	root.m_namedVariants[2].set("Physics Data", buildResult.physicsData, physicsDataClass);
	root.m_namedVariants[3].set("RagdollInstance", buildResult.ragdollInstance, ragdollInstanceClass);
	root.m_namedVariants[4].set("SkeletonMapper", buildResult.ragdollToAnimationMapper, skeletonMapperClass);
	root.m_namedVariants[5].set("SkeletonMapper", buildResult.animationToRagdollMapper, skeletonMapperClass);

	printf("Configuring packfile writer...\n");
	fflush(stdout);
	LegacyClassListener listener(cloner);
	hkBinaryPackfileWriter writer;
	writer.setContents(&root, hkRootLevelContainerClass, &listener);

	hkPackfileWriter::Options options;
	options.m_layout = hkStructureLayout::MsvcWin32LayoutRules;
	options.m_writeMetaInfo = true;
	options.m_contentsVersion = kTargetVersion;

	printf("Opening output stream...\n");
	fflush(stdout);
	hkOstream stream(outputFile);
	if (!stream.isOk())
	{
		fprintf(stderr, "Error: cannot open %s for writing\n", outputFile);
		return false;
	}

	printf("Saving packfile...\n");
	fflush(stdout);
	if (writer.save(stream.getStreamWriter(), options) != HK_SUCCESS)
	{
		fprintf(stderr, "Error: failed to write Havok 4.5.1 ragdoll packfile\n");
		return false;
	}

	return true;
}