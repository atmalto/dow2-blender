#include "simulation_controller.h"

#include <string>
#include <vector>

#include "physics_import.h"
#include "ragdoll_runtime_manager.h"
#include "simulation_controller_internal.h"
#include "simulation_world.h"

using simulation_controller_internal::make_numbered_name;
using simulation_controller_internal::require_authoring_selection;
using simulation_controller_internal::require_selected_kind;

bool SimulationController::add_object(const SpawnedObjectSpec& spec, std::string* error_message)
{
    SpawnedObjectSpec normalized_spec;
    SceneEntityId entity_id = 0;

    if (!normalize_object_spec(spec, &normalized_spec, error_message))
    {
        return false;
    }

    entity_id = m_scene_document.add_object(normalized_spec, "Object", true);
    PhysicsObjectSceneEntity* object = find_object_entity(entity_id);
    if (object)
    {
        object->record.name = make_numbered_name("Rigid Body", entity_id);
    }
    m_scene_document.select_entity(entity_id, SceneEntityKindPhysicsObject);
    reset();
    return true;
}

bool SimulationController::import_physics_systems(const std::vector<ImportedPhysicsSystem>& systems, const std::vector<int>& selected_systems, std::string* error_message)
{
    SceneEntityId last_entity_id = 0;
    int imported_count = 0;
    std::size_t selected_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before importing physics.";
        }
        return false;
    }

    for (selected_index = 0; selected_index < selected_systems.size(); ++selected_index)
    {
        const int system_index = selected_systems[selected_index];
        const ImportedPhysicsSystem* system = 0;
        std::size_t object_index = 0;

        if (system_index < 0 || system_index >= static_cast<int>(systems.size()))
        {
            continue;
        }

        system = &systems[system_index];
        for (object_index = 0; object_index < system->objects.size(); ++object_index)
        {
            const ImportedPhysicsObject& imported_object = system->objects[object_index];
            SpawnedObjectSpec normalized_spec;
            SceneEntityId entity_id = 0;
            PhysicsObjectSceneEntity* object_entity = 0;

            if (!normalize_object_spec(imported_object.object_spec, &normalized_spec, error_message))
            {
                return false;
            }

            entity_id = m_scene_document.add_object(normalized_spec, imported_object.name.c_str(), imported_object.editable);
            object_entity = find_object_entity(entity_id);
            if (object_entity)
            {
                object_entity->record.name = system->name + " / " + imported_object.name;
            }
            last_entity_id = entity_id;
            ++imported_count;
        }
    }

    if (imported_count <= 0 || last_entity_id == 0)
    {
        if (error_message)
        {
            *error_message = "None of the selected physics systems produced importable scene objects.";
        }
        return false;
    }

    m_scene_document.select_entity(last_entity_id, SceneEntityKindPhysicsObject);
    reset();
    return true;
}

int SimulationController::spawned_object_count() const
{
    return static_cast<int>(m_scene_document.objects().size());
}

bool SimulationController::get_selected_object_spec(SpawnedObjectSpec* spec) const
{
    SceneEntitySelection selected;
    const PhysicsObjectSceneEntity* object = 0;

    if (!spec)
    {
        return false;
    }

    if (!require_selected_kind(
        m_scene_document,
        SceneEntityKindPhysicsObject,
        "Select an object first.",
        &selected,
        0))
    {
        return false;
    }

    object = find_object_entity(selected.id);
    if (!object)
    {
        return false;
    }

    *spec = object->object_spec;
    return true;
}

bool SimulationController::update_selected_object(const SpawnedObjectSpec& spec, std::string* error_message)
{
    SceneEntitySelection selected;
    PhysicsObjectSceneEntity* object = 0;
    SpawnedObjectSpec normalized_spec;

    if (!require_authoring_selection(
        m_scene_document,
        can_author_scene(),
        SceneEntityKindPhysicsObject,
        "Select an object and reset simulation before editing.",
        &selected,
        error_message))
    {
        return false;
    }

    if (!normalize_object_spec(spec, &normalized_spec, error_message))
    {
        return false;
    }

    object = find_object_entity(selected.id);
    if (!object)
    {
        return false;
    }

    if (!object->record.editable)
    {
        if (error_message)
        {
            *error_message = "The selected imported convex hull does not have a parametric editor.";
        }
        return false;
    }

    object->object_spec = normalized_spec;
    reset();
    return true;
}

bool SimulationController::add_force_entity(const ForceSpec& spec, std::string* error_message)
{
    ForceSpec committed_spec = spec;
    SceneEntityId entity_id = 0;

    (void)error_message;

    entity_id = m_scene_document.add_force(committed_spec, "Force");
    ForceSceneEntity* force = find_force_entity(entity_id);
    if (force)
    {
        force->record.name = make_numbered_name("Force", entity_id);
    }
    m_scene_document.select_entity(entity_id, SceneEntityKindForce);
    reset();
    return true;
}

int SimulationController::force_count() const
{
    return static_cast<int>(m_scene_document.forces().size());
}

bool SimulationController::get_selected_force_spec(ForceSpec* spec) const
{
    SceneEntitySelection selected;
    const ForceSceneEntity* force = 0;

    if (!spec)
    {
        return false;
    }

    if (!require_selected_kind(
        m_scene_document,
        SceneEntityKindForce,
        "Select a force first.",
        &selected,
        0))
    {
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    *spec = force->force_spec;
    return true;
}

bool SimulationController::update_selected_force(const ForceSpec& spec, std::string* error_message)
{
    SceneEntitySelection selected;
    ForceSceneEntity* force = 0;

    if (!require_authoring_selection(
        m_scene_document,
        can_author_scene(),
        SceneEntityKindForce,
        "Select a force and reset simulation before editing.",
        &selected,
        error_message))
    {
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    force->force_spec = spec;
    reset();
    return true;
}

bool SimulationController::set_selected_force_preview(const ForceSpec& spec, std::string* error_message)
{
    SceneEntitySelection selected;
    ForceSceneEntity* force = 0;
    std::size_t body_index = 0;

    if (!require_selected_kind(
        m_scene_document,
        SceneEntityKindForce,
        "Select a force before previewing force edits.",
        &selected,
        error_message))
    {
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    force->force_spec = spec;

    for (body_index = 0; m_simulation_world && body_index < m_simulation_world->render_bodies().size(); ++body_index)
    {
        BodyRenderState& render_state = m_simulation_world->render_bodies()[body_index];
        if (render_state.entity_id == selected.id && render_state.entity_kind == SceneEntityKindForce)
        {
            SimulationWorld::apply_force_spec_to_render_state(spec, &render_state);
            return true;
        }
    }

    return false;
}

bool SimulationController::delete_selected_entity()
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    if (!can_author_scene() || selected.id == 0)
    {
        return false;
    }

    if (selected.kind == SceneEntityKindRagdoll && m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->delete_runtime_for_entity(selected.id);
    }

    if (!m_scene_document.remove_entity(selected.id, selected.kind))
    {
        return false;
    }

    reset();
    return true;
}

bool SimulationController::duplicate_selected_entity(std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    SceneEntityId duplicate_id = 0;

    if (!can_author_scene() || selected.id == 0)
    {
        return false;
    }

    duplicate_id = m_scene_document.duplicate_entity(selected.id, selected.kind);
    if (duplicate_id == 0)
    {
        return false;
    }

    if (selected.kind == SceneEntityKindRagdoll)
    {
        const RagdollSceneEntity* duplicate = find_ragdoll_entity(duplicate_id);

        if (!duplicate || !m_ragdoll_runtime_manager ||
            !m_ragdoll_runtime_manager->load_runtime(duplicate_id, duplicate->ragdoll, error_message))
        {
            m_scene_document.remove_entity(duplicate_id, SceneEntityKindRagdoll);
            return false;
        }
    }

    m_scene_document.select_entity(duplicate_id, selected.kind);
    reset();
    return true;
}

void SimulationController::set_object_preview(const SpawnedObjectSpec& spec)
{
    m_has_object_preview = true;
    m_object_preview_spec = spec;

    if (m_object_preview_spec.object_type == ObjectSphere)
    {
        m_object_preview_spec.scale[1] = m_object_preview_spec.scale[0];
        m_object_preview_spec.scale[2] = m_object_preview_spec.scale[0];
    }

    rebuild_preview_bodies();
}

void SimulationController::clear_object_preview()
{
    m_has_object_preview = false;
    rebuild_preview_bodies();
}

bool SimulationController::apply_push_force(const ForceSpec& spec, std::string* error_message)
{
    if (!m_simulation_world)
    {
        return false;
    }

    if (!m_ragdoll_runtime_manager ||
        !m_simulation_world->apply_push_force(m_ragdoll_runtime_manager->runtimes(), spec, error_message))
    {
        return false;
    }

    m_runtime_matches_scene = false;
    return true;
}

void SimulationController::set_force_preview(const ForceSpec& spec)
{
    m_has_force_preview = true;
    m_force_preview_spec = spec;
    rebuild_preview_bodies();
}

void SimulationController::clear_force_preview()
{
    m_has_force_preview = false;
    rebuild_preview_bodies();
}

bool SimulationController::normalize_object_spec(
    const SpawnedObjectSpec& spec,
    SpawnedObjectSpec* normalized_spec,
    std::string* error_message) const
{
    if (!normalized_spec)
    {
        return false;
    }

    *normalized_spec = spec;

    if (normalized_spec->object_type == ObjectConvexHull)
    {
        if (normalized_spec->convex_hull_vertices.size() < 4)
        {
            if (error_message)
            {
                *error_message = "Convex hull objects require at least four vertices.";
            }
            return false;
        }
    }

    if (normalized_spec->scale[0] <= 0.0f || normalized_spec->scale[1] <= 0.0f || normalized_spec->scale[2] <= 0.0f)
    {
        if (error_message)
        {
            *error_message = "Object scale must be positive on every axis.";
        }
        return false;
    }

    if (normalized_spec->body_type == BodyDynamic && normalized_spec->mass <= 0.0f)
    {
        if (error_message)
        {
            *error_message = "Dynamic objects require a positive mass.";
        }
        return false;
    }

    if (normalized_spec->body_type == BodyStatic)
    {
        normalized_spec->mass = 0.0f;
    }

    if (normalized_spec->object_type == ObjectSphere)
    {
        normalized_spec->scale[1] = normalized_spec->scale[0];
        normalized_spec->scale[2] = normalized_spec->scale[0];
    }

    return true;
}

bool SimulationController::apply_entity_runtime_position(SceneEntityId id, SceneEntityKind kind, const float position[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_position(
            m_scene_document,
            m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->runtimes() : std::vector<RagdollRuntime*>(),
            id,
            kind,
            position)
        : false;
}

bool SimulationController::apply_entity_runtime_rotation(SceneEntityId id, SceneEntityKind kind, const float rotation_degrees[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_rotation(m_scene_document, id, kind, rotation_degrees)
        : false;
}

bool SimulationController::apply_entity_runtime_scale(SceneEntityId id, SceneEntityKind kind, const float scale[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_scale(m_scene_document, id, kind, scale)
        : false;
}