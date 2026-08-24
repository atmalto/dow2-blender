#include "simulation_controller.h"

#include <string>

#include "ragdoll_runtime_manager.h"
#include "simulation_controller_internal.h"
#include "simulation_world.h"

using simulation_controller_internal::make_numbered_name;
using simulation_controller_internal::require_authoring_selection;
using simulation_controller_internal::require_selected_kind;

bool SimulationController::load_ragdoll(const char* path, std::string* error_message)
{
    SceneEntityId entity_id = 0;

    if (!m_ragdoll_runtime_manager ||
        !m_ragdoll_runtime_manager->load_ragdoll(m_scene_document, path, &entity_id, error_message))
    {
        return false;
    }

    RagdollSceneEntity* ragdoll = active_ragdoll_entity();
    if (ragdoll)
    {
        ragdoll->record.name = make_numbered_name("Ragdoll", entity_id);
    }

    reset();
    return true;
}

bool SimulationController::has_ragdoll() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->has_ragdoll(m_scene_document) : false;
}

const std::string& SimulationController::ragdoll_path() const
{
    static const std::string empty_path;
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->ragdoll_path(m_scene_document) : empty_path;
}

void SimulationController::set_ragdoll_start_position(float x, float y, float z)
{
    const float position[3] = { x, y, z };

    if (m_ragdoll_runtime_manager &&
        m_ragdoll_runtime_manager->set_active_start_position(m_scene_document, position) &&
        m_simulation_world)
    {
        m_simulation_world->sync_render_state();
    }
}

void SimulationController::get_ragdoll_start_position(float& x, float& y, float& z) const
{
    if (!m_ragdoll_runtime_manager)
    {
        x = 0.0f;
        y = 0.0f;
        z = 0.0f;
        return;
    }

    m_ragdoll_runtime_manager->get_active_start_position(m_scene_document, x, y, z);
}

int SimulationController::ragdoll_count() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->ragdoll_count(m_scene_document) : 0;
}

bool SimulationController::get_ragdoll_preview_data(SceneEntityId entity_id, RagdollPreviewData* preview_data) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_preview_data(entity_id, preview_data)
        : false;
}

bool SimulationController::get_selected_ragdoll_preview_data(RagdollPreviewData* preview_data) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_selected_preview_data(m_scene_document, preview_data)
        : false;
}

bool SimulationController::get_ragdoll_runtime_diagnostics(SceneEntityId entity_id, RagdollRuntimeDiagnostics* diagnostics) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_runtime_diagnostics(entity_id, diagnostics)
        : false;
}

bool SimulationController::get_selected_ragdoll_runtime_diagnostics(RagdollRuntimeDiagnostics* diagnostics) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_selected_runtime_diagnostics(m_scene_document, diagnostics)
        : false;
}

bool SimulationController::get_selected_ragdoll_spec(RagdollSceneSpec* spec) const
{
    SceneEntitySelection selected;
    const RagdollSceneEntity* ragdoll = 0;

    if (!spec)
    {
        return false;
    }

    if (!require_selected_kind(
        m_scene_document,
        SceneEntityKindRagdoll,
        "Select a ragdoll first.",
        &selected,
        0))
    {
        return false;
    }

    ragdoll = find_ragdoll_entity(selected.id);
    if (!ragdoll)
    {
        return false;
    }

    *spec = ragdoll->ragdoll;
    return true;
}

bool SimulationController::update_selected_ragdoll(const RagdollSceneSpec& spec, std::string* error_message)
{
    SceneEntitySelection selected;
    RagdollSceneEntity* ragdoll = 0;

    if (!require_authoring_selection(
        m_scene_document,
        can_author_scene(),
        SceneEntityKindRagdoll,
        "Select a ragdoll and reset simulation before editing.",
        &selected,
        error_message))
    {
        return false;
    }

    ragdoll = active_ragdoll_entity();
    if (!ragdoll)
    {
        return false;
    }

    ragdoll->ragdoll = spec;
    reset();
    return true;
}

void SimulationController::release_ragdoll_runtime_at(std::size_t runtime_index)
{
    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->release_runtime_at(runtime_index);
    }
}

void SimulationController::unload_ragdoll()
{
    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->clear_scene_ragdolls(m_scene_document, m_simulation_world);
    }
}

const RagdollSceneEntity* SimulationController::primary_ragdoll_entity() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_entity(m_scene_document) : 0;
}

RagdollSceneEntity* SimulationController::primary_ragdoll_entity()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_entity(m_scene_document) : 0;
}

const RagdollSceneEntity* SimulationController::active_ragdoll_entity() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_entity(m_scene_document) : 0;
}

RagdollSceneEntity* SimulationController::active_ragdoll_entity()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_entity(m_scene_document) : 0;
}

const RagdollSceneEntity* SimulationController::find_ragdoll_entity(SceneEntityId entity_id) const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_entity(m_scene_document, entity_id) : 0;
}

RagdollRuntime* SimulationController::find_ragdoll_runtime(SceneEntityId entity_id)
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_runtime(entity_id) : 0;
}

const RagdollRuntime* SimulationController::find_ragdoll_runtime(SceneEntityId entity_id) const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_runtime(entity_id) : 0;
}

RagdollRuntime* SimulationController::primary_ragdoll_runtime()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_runtime() : 0;
}

RagdollRuntime* SimulationController::active_ragdoll_runtime()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_runtime(m_scene_document) : 0;
}

const RagdollRuntime* SimulationController::primary_ragdoll_runtime() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_runtime() : 0;
}

const RagdollRuntime* SimulationController::active_ragdoll_runtime() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_runtime(m_scene_document) : 0;
}