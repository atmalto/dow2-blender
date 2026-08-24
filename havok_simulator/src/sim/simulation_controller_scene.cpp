#include "simulation_controller.h"

#include <string>
#include <vector>

#include "ragdoll_runtime_manager.h"
#include "scene_persistence.h"
#include "scene_presets.h"
#include "simulation_world.h"

void SimulationController::clear_scene()
{
    clear_scene_contents();
    reset();
}

bool SimulationController::create_scene_from_preset(ScenePresetId preset_id, std::string* error_message)
{
    ScenePresetDefinition definition;
    std::size_t object_index = 0;
    std::size_t force_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before creating a new scene.";
        }
        return false;
    }

    if (!build_scene_preset(preset_id, &definition))
    {
        if (error_message)
        {
            *error_message = "The selected scene preset is not available.";
        }
        return false;
    }

    clear_scene_contents();
    m_ground_mode = static_cast<GroundMode>(definition.ground_mode);

    for (object_index = 0; object_index < definition.objects.size(); ++object_index)
    {
        SpawnedObjectSpec normalized_spec;
        SceneEntityId entity_id = 0;

        if (!normalize_object_spec(definition.objects[object_index].spec, &normalized_spec, error_message))
        {
            clear_scene_contents();
            reset();
            return false;
        }

        entity_id = m_scene_document.add_object(
            normalized_spec,
            definition.objects[object_index].name.c_str(),
            definition.objects[object_index].editable);
        if (static_cast<int>(object_index) == definition.ground_object_index)
        {
            m_default_ground_entity_id = entity_id;
        }
    }

    for (force_index = 0; force_index < definition.forces.size(); ++force_index)
    {
        m_scene_document.add_force(
            definition.forces[force_index].spec,
            definition.forces[force_index].name.c_str());
    }

    m_scene_document.clear_selection();
    reset();
    return true;
}

void SimulationController::clear_scene_contents()
{
    m_is_playing = false;
    m_has_object_preview = false;
    m_has_force_preview = false;
    m_default_ground_entity_id = 0;

    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->clear_runtimes(m_simulation_world);
    }

    m_scene_document.clear();
}

bool SimulationController::build_persisted_scene(PersistedSceneData* scene) const
{
    std::size_t ragdoll_index = 0;
    std::size_t object_index = 0;
    std::size_t force_index = 0;

    if (!scene)
    {
        return false;
    }

    *scene = PersistedSceneData();

    for (ragdoll_index = 0; ragdoll_index < m_scene_document.ragdolls().size(); ++ragdoll_index)
    {
        PersistedSceneRagdoll persisted_ragdoll;
        const RagdollSceneEntity& ragdoll = m_scene_document.ragdolls()[ragdoll_index];

        persisted_ragdoll.name = ragdoll.record.name;
        persisted_ragdoll.spec = ragdoll.ragdoll;
        scene->ragdolls.push_back(persisted_ragdoll);
    }

    for (object_index = 0; object_index < m_scene_document.objects().size(); ++object_index)
    {
        PersistedSceneObject persisted_object;
        const PhysicsObjectSceneEntity& object = m_scene_document.objects()[object_index];

        persisted_object.name = object.record.name;
        persisted_object.editable = object.record.editable;
        persisted_object.spec = object.object_spec;
        scene->objects.push_back(persisted_object);
    }

    for (force_index = 0; force_index < m_scene_document.forces().size(); ++force_index)
    {
        PersistedSceneForce persisted_force;
        const ForceSceneEntity& force = m_scene_document.forces()[force_index];

        persisted_force.name = force.record.name;
        persisted_force.spec = force.force_spec;
        scene->forces.push_back(persisted_force);
    }

    return true;
}

bool SimulationController::load_persisted_scene(const PersistedSceneData& scene, std::vector<std::string>* warnings, std::string* error_message)
{
    std::size_t object_index = 0;
    std::size_t force_index = 0;
    std::size_t ragdoll_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before loading a scene.";
        }
        return false;
    }

    clear_scene_contents();

    for (object_index = 0; object_index < scene.objects.size(); ++object_index)
    {
        SpawnedObjectSpec normalized_spec;
        const PersistedSceneObject& persisted_object = scene.objects[object_index];

        if (!normalize_object_spec(persisted_object.spec, &normalized_spec, error_message))
        {
            clear_scene_contents();
            reset();
            return false;
        }

        m_scene_document.add_object(normalized_spec, persisted_object.name.c_str(), persisted_object.editable);
    }

    for (force_index = 0; force_index < scene.forces.size(); ++force_index)
    {
        const PersistedSceneForce& persisted_force = scene.forces[force_index];
        m_scene_document.add_force(persisted_force.spec, persisted_force.name.c_str());
    }

    for (ragdoll_index = 0; ragdoll_index < scene.ragdolls.size(); ++ragdoll_index)
    {
        const PersistedSceneRagdoll& persisted_ragdoll = scene.ragdolls[ragdoll_index];
        SceneEntityId entity_id = m_scene_document.add_ragdoll(persisted_ragdoll.spec, persisted_ragdoll.name.c_str());
        if (!m_ragdoll_runtime_manager ||
            !m_ragdoll_runtime_manager->load_runtime(entity_id, persisted_ragdoll.spec, error_message))
        {
            m_scene_document.remove_entity(entity_id, SceneEntityKindRagdoll);

            if (warnings)
            {
                warnings->push_back(std::string("Skipped ragdoll '") + persisted_ragdoll.name + "' because its HKX reference could not be loaded.");
            }

            if (error_message)
            {
                error_message->clear();
            }
            continue;
        }
    }

    m_scene_document.clear_selection();
    reset();
    return true;
}

void SimulationController::seed_default_scene_objects()
{
    SpawnedObjectSpec ground_spec;
    SpawnedObjectSpec box_spec;
    SpawnedObjectSpec sphere_spec;

    ground_spec.object_type = ObjectCube;
    ground_spec.body_type = BodyStatic;
    ground_spec.position[0] = 0.0f;
    ground_spec.position[1] = -0.5f;
    ground_spec.position[2] = 0.0f;
    ground_spec.rotation_degrees[0] = 0.0f;
    ground_spec.rotation_degrees[1] = 0.0f;
    ground_spec.rotation_degrees[2] = 0.0f;
    ground_spec.scale[0] = 12.0f;
    ground_spec.scale[1] = 0.5f;
    ground_spec.scale[2] = 12.0f;
    ground_spec.restitution = 0.0f;
    ground_spec.mass = 0.0f;

    box_spec.object_type = ObjectCube;
    box_spec.body_type = BodyDynamic;
    box_spec.position[0] = -1.5f;
    box_spec.position[1] = 6.0f;
    box_spec.position[2] = 0.0f;
    box_spec.rotation_degrees[0] = 0.0f;
    box_spec.rotation_degrees[1] = 0.0f;
    box_spec.rotation_degrees[2] = 0.0f;
    box_spec.scale[0] = 0.75f;
    box_spec.scale[1] = 0.75f;
    box_spec.scale[2] = 0.75f;
    box_spec.restitution = 0.1f;
    box_spec.mass = 12.0f;

    sphere_spec.object_type = ObjectSphere;
    sphere_spec.body_type = BodyDynamic;
    sphere_spec.position[0] = 1.25f;
    sphere_spec.position[1] = 8.0f;
    sphere_spec.position[2] = 0.0f;
    sphere_spec.rotation_degrees[0] = 0.0f;
    sphere_spec.rotation_degrees[1] = 0.0f;
    sphere_spec.rotation_degrees[2] = 0.0f;
    sphere_spec.scale[0] = 0.65f;
    sphere_spec.scale[1] = 0.65f;
    sphere_spec.scale[2] = 0.65f;
    sphere_spec.restitution = 0.25f;
    sphere_spec.mass = 6.0f;

    m_default_ground_entity_id = m_scene_document.add_object(ground_spec, "Ground", true);
    m_scene_document.add_object(box_spec, "Starter Box", true);
    m_scene_document.add_object(sphere_spec, "Starter Sphere", true);
    update_ground_scene_object();
    m_scene_document.clear_selection();
}

void SimulationController::update_ground_scene_object()
{
    PhysicsObjectSceneEntity* ground = find_object_entity(m_default_ground_entity_id);

    if (!ground)
    {
        return;
    }

    ground->object_spec.object_type = ObjectCube;
    ground->object_spec.body_type = BodyStatic;
    ground->object_spec.position[0] = 0.0f;
    ground->object_spec.position[1] = -0.5f;
    ground->object_spec.position[2] = 0.0f;
    ground->object_spec.rotation_degrees[0] = 0.0f;
    ground->object_spec.rotation_degrees[1] = 0.0f;
    ground->object_spec.rotation_degrees[2] = 0.0f;
    ground->object_spec.scale[0] = 12.0f;
    ground->object_spec.scale[1] = 0.5f;
    ground->object_spec.scale[2] = 12.0f;
    ground->object_spec.restitution = 0.0f;
    ground->object_spec.mass = 0.0f;

    if (m_ground_mode == GroundSlanted)
    {
        ground->object_spec.position[0] = -1.5f;
        ground->object_spec.rotation_degrees[2] = 20.0f;
    }
}