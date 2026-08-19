#ifndef HAVOK_SCENE_APP_SCENE_PRESETS_H
#define HAVOK_SCENE_APP_SCENE_PRESETS_H

#include <string>
#include <vector>

#include "scene_document.h"

enum ScenePresetId
{
    ScenePresetBlank = 0,
    ScenePresetFlatPlaneWithForce = 1,
    ScenePresetDiagonalPlane = 2
};

struct ScenePresetObjectEntry
{
    ScenePresetObjectEntry()
        : editable(true)
    {
    }

    std::string name;
    SpawnedObjectSceneSpec spec;
    bool editable;
};

struct ScenePresetForceEntry
{
    std::string name;
    ForceSceneSpec spec;
};

struct ScenePresetDefinition
{
    ScenePresetDefinition()
        : ground_mode(0)
        , ground_object_index(-1)
    {
    }

    int ground_mode;
    int ground_object_index;
    std::vector<ScenePresetObjectEntry> objects;
    std::vector<ScenePresetForceEntry> forces;
};

bool build_scene_preset(ScenePresetId preset_id, ScenePresetDefinition* definition);
const char* scene_preset_label(ScenePresetId preset_id);

#endif