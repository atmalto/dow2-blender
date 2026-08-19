#include "ragdoll_runtime_manager.h"

#include "ragdoll_runtime.h"
#include "simulation_world.h"

RagdollRuntimeManager::RagdollRuntimeManager()
{
}

RagdollRuntimeManager::~RagdollRuntimeManager()
{
    clear_runtimes(0);
}

bool RagdollRuntimeManager::load_ragdoll(
    SceneDocument& scene_document,
    const char* path,
    SceneEntityId* entity_id,
    std::string* error_message)
{
    RagdollSceneSpec ragdoll_spec;
    SceneEntityId created_entity_id = 0;

    ragdoll_spec.asset_path = path ? path : "";
    ragdoll_spec.position[0] = 0.0f;
    ragdoll_spec.position[1] = 0.0f;
    ragdoll_spec.position[2] = 0.0f;

    created_entity_id = scene_document.add_ragdoll(ragdoll_spec, "Ragdoll");
    if (!load_runtime(created_entity_id, ragdoll_spec, error_message))
    {
        scene_document.remove_entity(created_entity_id, SceneEntityKindRagdoll);
        return false;
    }

    scene_document.select_entity(created_entity_id, SceneEntityKindRagdoll);
    if (entity_id)
    {
        *entity_id = created_entity_id;
    }

    return true;
}

bool RagdollRuntimeManager::load_runtime(SceneEntityId entity_id, const RagdollSceneSpec& spec, std::string* error_message)
{
    RagdollRuntime* runtime_state = new RagdollRuntime();

    if (!runtime_state->load(entity_id, spec, error_message))
    {
        delete runtime_state;
        return false;
    }

    m_ragdoll_runtimes.push_back(runtime_state);
    return true;
}

void RagdollRuntimeManager::detach_from_world(SimulationWorld* simulation_world)
{
    if (simulation_world)
    {
        simulation_world->remove_loaded_ragdolls_from_world(m_ragdoll_runtimes);
    }
}

void RagdollRuntimeManager::clear_scene_ragdolls(SceneDocument& scene_document, SimulationWorld* simulation_world)
{
    detach_from_world(simulation_world);
    clear_runtimes(0);
    scene_document.clear_ragdolls();
}

void RagdollRuntimeManager::clear_runtimes(SimulationWorld* simulation_world)
{
    detach_from_world(simulation_world);

    while (!m_ragdoll_runtimes.empty())
    {
        release_runtime_at(m_ragdoll_runtimes.size() - 1);
    }
}

void RagdollRuntimeManager::release_runtime_at(std::size_t runtime_index)
{
    RagdollRuntime* runtime_state = 0;

    if (runtime_index >= m_ragdoll_runtimes.size())
    {
        return;
    }

    runtime_state = m_ragdoll_runtimes[runtime_index];
    delete runtime_state;
    m_ragdoll_runtimes.erase(m_ragdoll_runtimes.begin() + runtime_index);
}

void RagdollRuntimeManager::step_runtimes(float timestep)
{
    std::size_t runtime_index = 0;

    for (runtime_index = 0; runtime_index < m_ragdoll_runtimes.size(); ++runtime_index)
    {
        if (m_ragdoll_runtimes[runtime_index])
        {
            m_ragdoll_runtimes[runtime_index]->step(timestep);
        }
    }
}

void RagdollRuntimeManager::delete_runtime_for_entity(SceneEntityId entity_id)
{
    std::size_t runtime_index = 0;

    for (runtime_index = 0; runtime_index < m_ragdoll_runtimes.size(); ++runtime_index)
    {
        if (m_ragdoll_runtimes[runtime_index] && m_ragdoll_runtimes[runtime_index]->entity_id() == entity_id)
        {
            release_runtime_at(runtime_index);
            return;
        }
    }
}

bool RagdollRuntimeManager::has_ragdoll(const SceneDocument& scene_document) const
{
    return !scene_document.ragdolls().empty();
}

const std::string& RagdollRuntimeManager::ragdoll_path(const SceneDocument& scene_document) const
{
    static const std::string empty_path;
    const RagdollSceneEntity* ragdoll = active_entity(scene_document);
    return ragdoll ? ragdoll->ragdoll.asset_path : empty_path;
}

bool RagdollRuntimeManager::set_active_start_position(SceneDocument& scene_document, const float position[3])
{
    RagdollSceneEntity* ragdoll = active_entity(scene_document);
    RagdollRuntime* runtime_state = active_runtime(scene_document);

    if (ragdoll)
    {
        ragdoll->ragdoll.position[0] = position[0];
        ragdoll->ragdoll.position[1] = position[1];
        ragdoll->ragdoll.position[2] = position[2];
    }

    if (ragdoll && runtime_state)
    {
        runtime_state->set_start_position(ragdoll->ragdoll.position);
        return true;
    }

    return false;
}

void RagdollRuntimeManager::get_active_start_position(const SceneDocument& scene_document, float& x, float& y, float& z) const
{
    const RagdollSceneEntity* ragdoll = active_entity(scene_document);

    if (!ragdoll)
    {
        x = 0.0f;
        y = 0.0f;
        z = 0.0f;
        return;
    }

    x = ragdoll->ragdoll.position[0];
    y = ragdoll->ragdoll.position[1];
    z = ragdoll->ragdoll.position[2];
}

int RagdollRuntimeManager::ragdoll_count(const SceneDocument& scene_document) const
{
    return static_cast<int>(scene_document.ragdolls().size());
}

bool RagdollRuntimeManager::get_preview_data(SceneEntityId entity_id, RagdollPreviewData* preview_data) const
{
    const RagdollRuntime* runtime_state = 0;

    if (!preview_data || entity_id == 0)
    {
        return false;
    }

    runtime_state = find_runtime(entity_id);
    if (!runtime_state)
    {
        return false;
    }

    *preview_data = runtime_state->preview_data();
    return true;
}

bool RagdollRuntimeManager::get_selected_preview_data(const SceneDocument& scene_document, RagdollPreviewData* preview_data) const
{
    const RagdollRuntime* runtime_state = active_runtime(scene_document);

    if (!preview_data || !runtime_state)
    {
        return false;
    }

    *preview_data = runtime_state->preview_data();
    return true;
}

bool RagdollRuntimeManager::get_runtime_diagnostics(SceneEntityId entity_id, RagdollRuntimeDiagnostics* diagnostics) const
{
    const RagdollRuntime* runtime_state = 0;

    if (!diagnostics || entity_id == 0)
    {
        return false;
    }

    runtime_state = find_runtime(entity_id);
    if (!runtime_state)
    {
        return false;
    }

    *diagnostics = runtime_state->diagnostics();
    return true;
}

bool RagdollRuntimeManager::get_selected_runtime_diagnostics(
    const SceneDocument& scene_document,
    RagdollRuntimeDiagnostics* diagnostics) const
{
    const RagdollRuntime* runtime_state = active_runtime(scene_document);

    if (!diagnostics || !runtime_state)
    {
        return false;
    }

    *diagnostics = runtime_state->diagnostics();
    return true;
}

const RagdollSceneEntity* RagdollRuntimeManager::primary_entity(const SceneDocument& scene_document) const
{
    const std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
    return ragdolls.empty() ? 0 : &ragdolls[0];
}

RagdollSceneEntity* RagdollRuntimeManager::primary_entity(SceneDocument& scene_document) const
{
    std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
    return ragdolls.empty() ? 0 : &ragdolls[0];
}

const RagdollSceneEntity* RagdollRuntimeManager::active_entity(const SceneDocument& scene_document) const
{
    const SceneEntitySelection& selected = scene_document.selected_entity();
    const RagdollSceneEntity* selected_ragdoll = 0;

    if (selected.kind == SceneEntityKindRagdoll)
    {
        selected_ragdoll = find_entity(scene_document, selected.id);
    }

    return selected_ragdoll ? selected_ragdoll : primary_entity(scene_document);
}

RagdollSceneEntity* RagdollRuntimeManager::active_entity(SceneDocument& scene_document) const
{
    const SceneEntitySelection selected = scene_document.selected_entity();
    RagdollSceneEntity* selected_ragdoll = 0;

    if (selected.kind == SceneEntityKindRagdoll)
    {
        selected_ragdoll = find_entity(scene_document, selected.id);
    }

    return selected_ragdoll ? selected_ragdoll : primary_entity(scene_document);
}

const RagdollSceneEntity* RagdollRuntimeManager::find_entity(const SceneDocument& scene_document, SceneEntityId entity_id) const
{
    const std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
    std::size_t ragdoll_index = 0;

    for (ragdoll_index = 0; ragdoll_index < ragdolls.size(); ++ragdoll_index)
    {
        if (ragdolls[ragdoll_index].record.id == entity_id)
        {
            return &ragdolls[ragdoll_index];
        }
    }

    return 0;
}

RagdollSceneEntity* RagdollRuntimeManager::find_entity(SceneDocument& scene_document, SceneEntityId entity_id) const
{
    std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
    std::size_t ragdoll_index = 0;

    for (ragdoll_index = 0; ragdoll_index < ragdolls.size(); ++ragdoll_index)
    {
        if (ragdolls[ragdoll_index].record.id == entity_id)
        {
            return &ragdolls[ragdoll_index];
        }
    }

    return 0;
}

RagdollRuntime* RagdollRuntimeManager::find_runtime(SceneEntityId entity_id)
{
    std::size_t runtime_index = 0;

    for (runtime_index = 0; runtime_index < m_ragdoll_runtimes.size(); ++runtime_index)
    {
        if (m_ragdoll_runtimes[runtime_index] && m_ragdoll_runtimes[runtime_index]->entity_id() == entity_id)
        {
            return m_ragdoll_runtimes[runtime_index];
        }
    }

    return 0;
}

const RagdollRuntime* RagdollRuntimeManager::find_runtime(SceneEntityId entity_id) const
{
    std::size_t runtime_index = 0;

    for (runtime_index = 0; runtime_index < m_ragdoll_runtimes.size(); ++runtime_index)
    {
        if (m_ragdoll_runtimes[runtime_index] && m_ragdoll_runtimes[runtime_index]->entity_id() == entity_id)
        {
            return m_ragdoll_runtimes[runtime_index];
        }
    }

    return 0;
}

RagdollRuntime* RagdollRuntimeManager::primary_runtime()
{
    return m_ragdoll_runtimes.empty() ? 0 : m_ragdoll_runtimes[0];
}

const RagdollRuntime* RagdollRuntimeManager::primary_runtime() const
{
    return m_ragdoll_runtimes.empty() ? 0 : m_ragdoll_runtimes[0];
}

RagdollRuntime* RagdollRuntimeManager::active_runtime(const SceneDocument& scene_document)
{
    const SceneEntitySelection selected = scene_document.selected_entity();
    RagdollRuntime* selected_runtime = 0;

    if (selected.kind == SceneEntityKindRagdoll)
    {
        selected_runtime = find_runtime(selected.id);
    }

    return selected_runtime ? selected_runtime : primary_runtime();
}

const RagdollRuntime* RagdollRuntimeManager::active_runtime(const SceneDocument& scene_document) const
{
    const SceneEntitySelection selected = scene_document.selected_entity();
    const RagdollRuntime* selected_runtime = 0;

    if (selected.kind == SceneEntityKindRagdoll)
    {
        selected_runtime = find_runtime(selected.id);
    }

    return selected_runtime ? selected_runtime : primary_runtime();
}

RagdollRuntime* RagdollRuntimeManager::find_runtime_owning_body(const hkpRigidBody* body)
{
    std::size_t runtime_index = 0;

    if (!body)
    {
        return 0;
    }

    for (runtime_index = 0; runtime_index < m_ragdoll_runtimes.size(); ++runtime_index)
    {
        RagdollRuntime* runtime_state = m_ragdoll_runtimes[runtime_index];
        int bone_index = 0;

        if (!runtime_state)
        {
            continue;
        }

        for (bone_index = 0; bone_index < runtime_state->body_count(); ++bone_index)
        {
            if (runtime_state->body_at(bone_index) == body)
            {
                return runtime_state;
            }
        }
    }

    return 0;
}

std::vector<RagdollRuntime*>& RagdollRuntimeManager::runtimes()
{
    return m_ragdoll_runtimes;
}

const std::vector<RagdollRuntime*>& RagdollRuntimeManager::runtimes() const
{
    return m_ragdoll_runtimes;
}