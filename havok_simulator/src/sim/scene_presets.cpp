#include "scene_presets.h"

namespace
{
    SpawnedObjectSceneSpec make_plane_spec(bool diagonal)
    {
        SpawnedObjectSceneSpec spec;
        spec.object_type = 0;
        spec.body_type = 1;
        spec.position[0] = diagonal ? -1.5f : 0.0f;
        spec.position[1] = -0.5f;
        spec.position[2] = 0.0f;
        spec.rotation_degrees[0] = 0.0f;
        spec.rotation_degrees[1] = 0.0f;
        spec.rotation_degrees[2] = diagonal ? 20.0f : 0.0f;
        spec.scale[0] = 12.0f;
        spec.scale[1] = 0.5f;
        spec.scale[2] = 12.0f;
        spec.restitution = 0.0f;
        spec.mass = 0.0f;
        return spec;
    }

    SpawnedObjectSceneSpec make_center_cube_spec()
    {
        SpawnedObjectSceneSpec spec;
        spec.object_type = 0;
        spec.body_type = 0;
        spec.position[0] = 0.0f;
        spec.position[1] = 0.75f;
        spec.position[2] = 0.0f;
        spec.rotation_degrees[0] = 0.0f;
        spec.rotation_degrees[1] = 0.0f;
        spec.rotation_degrees[2] = 0.0f;
        spec.scale[0] = 0.75f;
        spec.scale[1] = 0.75f;
        spec.scale[2] = 0.75f;
        spec.restitution = 0.1f;
        spec.mass = 12.0f;
        return spec;
    }

    ForceSceneSpec make_front_push_force_spec()
    {
        ForceSceneSpec spec;
        spec.position[0] = 0.0f;
        spec.position[1] = 1.0f;
        spec.position[2] = 5.0f;
        spec.rotation_degrees[0] = 0.0f;
        spec.rotation_degrees[1] = 0.0f;
        spec.rotation_degrees[2] = 0.0f;
        spec.strength = 120.0f;
        spec.mode = 0;
        spec.active = true;
        return spec;
    }
}

bool build_scene_preset(ScenePresetId preset_id, ScenePresetDefinition* definition)
{
    if (!definition)
    {
        return false;
    }

    *definition = ScenePresetDefinition();

    if (preset_id == ScenePresetBlank)
    {
        definition->ground_mode = 0;
        return true;
    }

    if (preset_id == ScenePresetFlatPlaneWithForce)
    {
        ScenePresetObjectEntry plane_entry;
        ScenePresetObjectEntry cube_entry;
        ScenePresetForceEntry force_entry;

        definition->ground_mode = 0;
        definition->ground_object_index = 0;

        plane_entry.name = "Ground";
        plane_entry.spec = make_plane_spec(false);
        definition->objects.push_back(plane_entry);

        cube_entry.name = "Center Cube";
        cube_entry.spec = make_center_cube_spec();
        definition->objects.push_back(cube_entry);

        force_entry.name = "Front Push Force";
        force_entry.spec = make_front_push_force_spec();
        definition->forces.push_back(force_entry);
        return true;
    }

    if (preset_id == ScenePresetDiagonalPlane)
    {
        ScenePresetObjectEntry plane_entry;

        definition->ground_mode = 1;
        definition->ground_object_index = 0;
        plane_entry.name = "Ground";
        plane_entry.spec = make_plane_spec(true);
        definition->objects.push_back(plane_entry);
        return true;
    }

    return false;
}

const char* scene_preset_label(ScenePresetId preset_id)
{
    if (preset_id == ScenePresetFlatPlaneWithForce)
    {
        return "Flat plane + force + cube";
    }

    if (preset_id == ScenePresetDiagonalPlane)
    {
        return "Diagonal plane";
    }

    return "Blank scene";
}