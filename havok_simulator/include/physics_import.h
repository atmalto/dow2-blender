#ifndef HAVOK_SCENE_APP_PHYSICS_IMPORT_H
#define HAVOK_SCENE_APP_PHYSICS_IMPORT_H

#include <string>
#include <vector>

#include "scene_document.h"

struct ImportedPhysicsObject
{
    ImportedPhysicsObject()
        : editable(true)
    {
    }

    std::string name;
    bool editable;
    SpawnedObjectSceneSpec object_spec;
};

struct ImportedPhysicsSystem
{
    ImportedPhysicsSystem()
        : skipped_body_count(0)
    {
    }

    std::string name;
    std::vector<ImportedPhysicsObject> objects;
    int skipped_body_count;
};

bool load_imported_physics_systems(
    const char* input_file,
    std::vector<ImportedPhysicsSystem>& systems_out,
    std::string* error_message);

#endif