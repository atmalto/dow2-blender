#ifndef HAVOK_SCENE_APP_SIMULATION_WORLD_H
#define HAVOK_SCENE_APP_SIMULATION_WORLD_H

#include <map>
#include <string>
#include <vector>

#include "body_render_state.h"
#include "scene_document.h"

class hkpRigidBody;
class hkpWorld;
class RagdollRuntime;

class SimulationWorld
{
public:
    typedef ::SpawnedObjectSceneSpec SpawnedObjectSpec;
    typedef ::ForceSceneSpec ForceSpec;

    SimulationWorld();
    ~SimulationWorld();

    void initialize_runtime();
    void shutdown_runtime();

    void destroy_world();
    void create_world(const SceneDocument& scene_document, const std::vector<RagdollRuntime*>& ragdoll_runtimes);
    void remove_loaded_ragdolls_from_world(const std::vector<RagdollRuntime*>& ragdoll_runtimes);

    void set_timestep(float timestep);
    float timestep() const;

    hkpWorld* world();
    const hkpWorld* world() const;

    const std::vector<BodyRenderState>& render_bodies() const;
    std::vector<BodyRenderState>& render_bodies();

    void sync_render_state();
    void refresh_selection_highlight(const SceneEntitySelection& selected);
    bool resolve_runtime_entity_for_body(const hkpRigidBody* body, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const;
    bool pick_entity_from_ray(const float ray_origin[3], const float ray_direction[3], SceneEntityId* entity_id, SceneEntityKind* entity_kind) const;

    bool apply_push_force(const std::vector<RagdollRuntime*>& ragdoll_runtimes, const ForceSpec& spec, std::string* error_message);
    void apply_continuous_force_entities(const SceneDocument& scene_document, const std::vector<RagdollRuntime*>& ragdoll_runtimes);

    bool apply_entity_runtime_position(
        const SceneDocument& scene_document,
        const std::vector<RagdollRuntime*>& ragdoll_runtimes,
        SceneEntityId id,
        SceneEntityKind kind,
        const float position[3]);
    bool apply_entity_runtime_rotation(
        const SceneDocument& scene_document,
        SceneEntityId id,
        SceneEntityKind kind,
        const float rotation_degrees[3]);
    bool apply_entity_runtime_scale(
        const SceneDocument& scene_document,
        SceneEntityId id,
        SceneEntityKind kind,
        const float scale[3]);

    bool build_render_state_from_spec(const SpawnedObjectSpec& spec, bool is_preview, BodyRenderState* state) const;

    static void apply_force_spec_to_render_state(const ForceSpec& spec, BodyRenderState* state);
    static BodyRenderState build_force_render_state(const ForceSpec& spec, bool is_preview);

private:
    struct RuntimeBodyBinding
    {
        SceneEntityId entity_id;
        SceneEntityKind entity_kind;
        hkpRigidBody* body;
        int render_index;
    };

    struct RuntimeEntityBinding
    {
        SceneEntityId entity_id;
        SceneEntityKind entity_kind;
        int first_runtime_body_index;
        int runtime_body_count;
        int first_render_index;
        int render_body_count;
    };

    void create_spawned_objects(const SceneDocument& scene_document);
    void create_force_entities(const SceneDocument& scene_document, const SceneEntitySelection& selected);
    void add_loaded_ragdolls(
        const SceneDocument& scene_document,
        const std::vector<RagdollRuntime*>& ragdoll_runtimes,
        const SceneEntitySelection& selected);
    void add_body(
        SceneEntityId entity_id,
        SceneEntityKind entity_kind,
        hkpRigidBody* body,
        const BodyRenderState& state,
        const SceneEntitySelection& selected);
    void add_render_body(
        SceneEntityId entity_id,
        SceneEntityKind entity_kind,
        hkpRigidBody* body,
        const BodyRenderState& state,
        const SceneEntitySelection& selected);
    bool create_body_from_spec(
        const SpawnedObjectSpec& spec,
        hkpRigidBody** body,
        BodyRenderState* state,
        std::string* error_message);
    bool find_force_target(
        const std::vector<RagdollRuntime*>& ragdoll_runtimes,
        const ForceSpec& spec,
        hkpRigidBody** body,
        float hit_point[3],
        float direction[3],
        std::string* error_message) const;
    RagdollRuntime* find_ragdoll_runtime_owning_body(
        const std::vector<RagdollRuntime*>& ragdoll_runtimes,
        const hkpRigidBody* body) const;
    const RuntimeBodyBinding* find_runtime_body_binding(const hkpRigidBody* body) const;
    const RuntimeEntityBinding* find_runtime_entity_binding(SceneEntityId entity_id, SceneEntityKind entity_kind) const;
    bool pick_force_entity_from_ray(
        const float ray_origin[3],
        const float ray_direction[3],
        float max_distance,
        SceneEntityId* entity_id,
        SceneEntityKind* entity_kind) const;

    static int s_runtime_refcount;

    float m_timestep;
    hkpWorld* m_world;
    std::vector<hkpRigidBody*> m_owned_bodies;
    std::vector<RuntimeBodyBinding> m_runtime_bodies;
    std::map<const hkpRigidBody*, std::size_t> m_runtime_body_lookup;
    std::vector<RuntimeEntityBinding> m_runtime_entities;
    std::vector<BodyRenderState> m_render_bodies;
};

#endif