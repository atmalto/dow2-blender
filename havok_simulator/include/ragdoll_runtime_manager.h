#ifndef HAVOK_SCENE_APP_RAGDOLL_RUNTIME_MANAGER_H
#define HAVOK_SCENE_APP_RAGDOLL_RUNTIME_MANAGER_H

#include <string>
#include <vector>

#include "ragdoll_preview_data.h"
#include "ragdoll_runtime_diagnostics.h"
#include "scene_document.h"

class hkpRigidBody;
class RagdollRuntime;
class SimulationWorld;

class RagdollRuntimeManager
{
public:
    RagdollRuntimeManager();
    ~RagdollRuntimeManager();

    bool load_ragdoll(SceneDocument& scene_document, const char* path, SceneEntityId* entity_id, std::string* error_message);
    bool load_runtime(SceneEntityId entity_id, const RagdollSceneSpec& spec, std::string* error_message);

    void detach_from_world(SimulationWorld* simulation_world);
    void clear_scene_ragdolls(SceneDocument& scene_document, SimulationWorld* simulation_world);
    void clear_runtimes(SimulationWorld* simulation_world);
    void release_runtime_at(std::size_t runtime_index);
    void step_runtimes(float timestep);
    void delete_runtime_for_entity(SceneEntityId entity_id);

    bool has_ragdoll(const SceneDocument& scene_document) const;
    const std::string& ragdoll_path(const SceneDocument& scene_document) const;
    bool set_active_start_position(SceneDocument& scene_document, const float position[3]);
    void get_active_start_position(const SceneDocument& scene_document, float& x, float& y, float& z) const;
    int ragdoll_count(const SceneDocument& scene_document) const;
    bool get_preview_data(SceneEntityId entity_id, RagdollPreviewData* preview_data) const;
    bool get_selected_preview_data(const SceneDocument& scene_document, RagdollPreviewData* preview_data) const;
    bool get_runtime_diagnostics(SceneEntityId entity_id, RagdollRuntimeDiagnostics* diagnostics) const;
    bool get_selected_runtime_diagnostics(const SceneDocument& scene_document, RagdollRuntimeDiagnostics* diagnostics) const;

    const RagdollSceneEntity* primary_entity(const SceneDocument& scene_document) const;
    RagdollSceneEntity* primary_entity(SceneDocument& scene_document) const;
    const RagdollSceneEntity* active_entity(const SceneDocument& scene_document) const;
    RagdollSceneEntity* active_entity(SceneDocument& scene_document) const;
    const RagdollSceneEntity* find_entity(const SceneDocument& scene_document, SceneEntityId entity_id) const;
    RagdollSceneEntity* find_entity(SceneDocument& scene_document, SceneEntityId entity_id) const;

    RagdollRuntime* find_runtime(SceneEntityId entity_id);
    const RagdollRuntime* find_runtime(SceneEntityId entity_id) const;
    RagdollRuntime* primary_runtime();
    const RagdollRuntime* primary_runtime() const;
    RagdollRuntime* active_runtime(const SceneDocument& scene_document);
    const RagdollRuntime* active_runtime(const SceneDocument& scene_document) const;
    RagdollRuntime* find_runtime_owning_body(const hkpRigidBody* body);

    std::vector<RagdollRuntime*>& runtimes();
    const std::vector<RagdollRuntime*>& runtimes() const;

private:
    mutable std::vector<RagdollRuntime*> m_ragdoll_runtimes;
};

#endif