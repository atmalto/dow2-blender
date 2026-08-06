#include "hkx_55_writer.h"

#include <stdio.h>
#include <stdlib.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/System/Io/IStream/hkIStream.h>
#include <Common/Base/System/Io/OStream/hkOStream.h>
#include <Common/Serialize/Packfile/Binary/hkBinaryPackfileReader.h>
#include <Common/Serialize/Packfile/Binary/hkBinaryPackfileWriter.h>
#include <Common/Serialize/Util/hkStructureLayout.h>

#include "hkx_55_legacy_builder.h"

namespace
{
	bool isDebugEnvEnabled(const char* name)
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
}

bool writePhysicsPackfile(
	hkRootLevelContainer* rootContainer,
	const char* outputFile)
{
	if (rootContainer == HK_NULL || outputFile == HK_NULL)
	{
		fprintf(stderr, "Error: invalid arguments passed to writePhysicsPackfile\n");
		return false;
	}

	legacy451_physics::LegacyGraph graph;
	hkRootLevelContainer legacyRoot;
	if (!legacy451_physics::buildLegacyGraph(&legacyRoot, graph, rootContainer))
	{
		return false;
	}

	printf("Writing Havok 4.5.1 HKX file: %s\n", outputFile);

	hkOstream stream(outputFile);
	if (!stream.isOk())
	{
		fprintf(stderr, "Error: cannot open output HKX file %s\n", outputFile);
		return false;
	}

	hkBinaryPackfileWriter writer;
	hkVtableClassRegistry registry;
	std::vector<legacy451_physics::ExactClassInfo> exactClasses;
	const bool useBuildingLayout = graph.deactivators.empty();
	const hkClass* physicsDataClass = legacy451_physics::selectLegacyPhysicsDataClass(useBuildingLayout);
	const hkClass* physicsSystemClass = legacy451_physics::selectLegacyPhysicsSystemClass(useBuildingLayout);
	const hkClass* rigidBodyClass = legacy451_physics::selectLegacyRigidBodyClass(useBuildingLayout);

	legacy451_physics::registerExactObject(registry, exactClasses, graph.physicsData, physicsDataClass);
	for (size_t i = 0; i < graph.systems.size(); ++i)
	{
		legacy451_physics::registerExactObject(registry, exactClasses, graph.systems[i], physicsSystemClass);
	}
	for (size_t i = 0; i < graph.rigidBodies.size(); ++i)
	{
		legacy451_physics::registerExactObject(registry, exactClasses, graph.rigidBodies[i], rigidBodyClass);
	}
	for (size_t i = 0; i < graph.shapes.size(); ++i)
	{
		legacy451_physics::registerExactObject(registry, exactClasses, graph.shapes[i], &legacy451_physics::g_legacy461ConvexVerticesShapeClass);
	}
	for (size_t i = 0; i < graph.deactivators.size(); ++i)
	{
		legacy451_physics::registerExactObject(registry, exactClasses, graph.deactivators[i], &legacy451_physics::g_legacy461SpatialRigidBodyDeactivatorClass);
	}

	legacy451_physics::ExactLegacyClassListener listener(exactClasses);
	writer.setContentsWithRegistry(&legacyRoot, hkRootLevelContainerClass, &registry, &listener);

	hkPackfileWriter::Options options;
	options.m_layout = hkStructureLayout::MsvcWin32LayoutRules;
	options.m_writeMetaInfo = true;
	options.m_contentsVersion = legacy451_physics::kLegacyVersion;

	if (writer.save(stream.getStreamWriter(), options) != HK_SUCCESS)
	{
		fprintf(stderr, "Error: Failed to write HKX file\n");
		return false;
	}

	if (isDebugEnvEnabled("DOW2_HKX_DEBUG_READBACK"))
	{
		hkIstream input(outputFile);
		if (input.isOk())
		{
			hkBinaryPackfileReader reader;
			if (reader.loadEntireFile(input.getStreamReader()) == HK_SUCCESS)
			{
				hkRootLevelContainer* readRoot = static_cast<hkRootLevelContainer*>(reader.getContents("hkRootLevelContainer"));
				if (readRoot != HK_NULL && readRoot->m_numNamedVariants > 1)
				{
					legacy451_physics::Legacy461PhysicsData* readPhysics = static_cast<legacy451_physics::Legacy461PhysicsData*>(readRoot->m_namedVariants[1].getObject());
					if (readPhysics != HK_NULL && readPhysics->m_systems.getSize() > 0 && readPhysics->m_systems[0] != HK_NULL && readPhysics->m_systems[0]->m_rigidBodies.getSize() > 0 && readPhysics->m_systems[0]->m_rigidBodies[0] != HK_NULL)
					{
						legacy451_physics::Legacy461RigidBody* readBody = readPhysics->m_systems[0]->m_rigidBodies[0];
						fprintf(stderr,
							"READBACK first body: shapeType=%d responseType=%d bvd_min=%u,%u,%u expMin=%u,%u,%u expShift=%u max=%u,%u,%u expMax=%u,%u,%u pad=%u childCount=%u allowed=%g deact=%u inactive=%u,%u type=%d\n",
							readBody->m_collidable.m_shape != HK_NULL ? readBody->m_collidable.m_shape->m_type : -1,
							readBody->m_material.m_responseType,
							readBody->m_collidable.m_boundingVolumeData.m_min[0],
							readBody->m_collidable.m_boundingVolumeData.m_min[1],
							readBody->m_collidable.m_boundingVolumeData.m_min[2],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMin[0],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMin[1],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMin[2],
							readBody->m_collidable.m_boundingVolumeData.m_expansionShift,
							readBody->m_collidable.m_boundingVolumeData.m_max[0],
							readBody->m_collidable.m_boundingVolumeData.m_max[1],
							readBody->m_collidable.m_boundingVolumeData.m_max[2],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMax[0],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMax[1],
							readBody->m_collidable.m_boundingVolumeData.m_expansionMax[2],
							readBody->m_collidable.m_boundingVolumeData.m_padding,
							readBody->m_collidable.m_boundingVolumeData.m_numChildShapeAabbs,
							readBody->m_collidable.m_allowedPenetrationDepth,
							readBody->m_motion.m_deactivationIntegrateCounter,
							readBody->m_motion.m_deactivationNumInactiveFrames[0],
							readBody->m_motion.m_deactivationNumInactiveFrames[1],
							readBody->m_motion.m_type);
					}
				}
			}
		}
	}

	return true;
}