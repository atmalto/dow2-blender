#ifndef HAVOK_SCENE_APP_SCENE_PERSISTENCE_H
#define HAVOK_SCENE_APP_SCENE_PERSISTENCE_H

#include <string>
#include <vector>

#include "scene_document.h"

struct PersistedSceneRagdoll
{
    std::string name;
    RagdollSceneSpec spec;
};

struct PersistedSceneObject
{
    PersistedSceneObject()
        : editable(true)
    {
    }

    std::string name;
    bool editable;
    SpawnedObjectSceneSpec spec;
};

struct PersistedSceneForce
{
    std::string name;
    ForceSceneSpec spec;
};

struct PersistedSceneData
{
    PersistedSceneData()
        : version(1)
    {
    }

    int version;
    std::vector<PersistedSceneRagdoll> ragdolls;
    std::vector<PersistedSceneObject> objects;
    std::vector<PersistedSceneForce> forces;
};

bool save_scene_file(
    const char* output_file,
    const PersistedSceneData& scene,
    std::string* error_message);

bool load_scene_file(
    const char* input_file,
    PersistedSceneData* scene,
    std::vector<std::string>* warnings,
    std::string* error_message);

#endif