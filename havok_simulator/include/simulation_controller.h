#ifndef HAVOK_SCENE_APP_SIMULATION_CONTROLLER_H
#define HAVOK_SCENE_APP_SIMULATION_CONTROLLER_H

#include <map>
#include <vector>

#include "body_render_state.h"
#include "ragdoll_preview_data.h"
#include "ragdoll_runtime_diagnostics.h"
#include "scene_presets.h"
#include "scene_document.h"

class hkpBoxShape;
class hkpRigidBody;
class hkpSphereShape;
class hkpWorld;
class RagdollRuntime;
class RagdollRuntimeManager;
class SimulationWorld;
class TransformSessionController;
struct ImportedPhysicsSystem;
struct PersistedSceneData;

class SimulationController
{
public:
    enum ObjectType
    {
        ObjectCube = 0,
        ObjectSphere = 1,
        ObjectWedge = 2,
        ObjectConvexHull = 3
    };

    enum RigidBodyType
    {
        BodyDynamic = 0,
        BodyStatic = 1
    };

    enum GroundMode
    {
        GroundFlat = 0,
        GroundSlanted = 1
    };

    enum ForceMode
    {
        ForcePush = 0,
        ForcePull = 1
    };

    typedef ::SpawnedObjectSceneSpec SpawnedObjectSpec;
    typedef ::ForceSceneSpec ForceSpec;

    SimulationController();
    ~SimulationController();

    void set_ground_mode(GroundMode mode);
    GroundMode ground_mode() const;
    void clear_scene();

    void reset();
    void step();

    void set_playing(bool playing);
    bool is_playing() const;

    bool load_ragdoll(const char* path, std::string* error_message);
    bool has_ragdoll() const;
    const std::string& ragdoll_path() const;
    bool create_scene_from_preset(ScenePresetId preset_id, std::string* error_message);

    void set_ragdoll_start_position(float x, float y, float z);
    void get_ragdoll_start_position(float& x, float& y, float& z) const;
    int ragdoll_count() const;
    bool get_ragdoll_preview_data(SceneEntityId entity_id, RagdollPreviewData* preview_data) const;
    bool get_selected_ragdoll_preview_data(RagdollPreviewData* preview_data) const;
    bool get_ragdoll_runtime_diagnostics(SceneEntityId entity_id, RagdollRuntimeDiagnostics* diagnostics) const;
    bool get_selected_ragdoll_runtime_diagnostics(RagdollRuntimeDiagnostics* diagnostics) const;
    bool get_selected_ragdoll_spec(RagdollSceneSpec* spec) const;
    bool update_selected_ragdoll(const RagdollSceneSpec& spec, std::string* error_message);

    bool add_object(const SpawnedObjectSpec& spec, std::string* error_message);
    bool import_physics_systems(const std::vector<ImportedPhysicsSystem>& systems, const std::vector<int>& selected_systems, std::string* error_message);
    int spawned_object_count() const;
    bool get_selected_object_spec(SpawnedObjectSpec* spec) const;
    bool update_selected_object(const SpawnedObjectSpec& spec, std::string* error_message);
    bool add_force_entity(const ForceSpec& spec, std::string* error_message);
    int force_count() const;
    bool get_selected_force_spec(ForceSpec* spec) const;
    bool update_selected_force(const ForceSpec& spec, std::string* error_message);
    bool set_selected_force_preview(const ForceSpec& spec, std::string* error_message);
    bool build_persisted_scene(PersistedSceneData* scene) const;
    bool load_persisted_scene(const PersistedSceneData& scene, std::vector<std::string>* warnings, std::string* error_message);
    bool delete_selected_entity();
    bool duplicate_selected_entity(std::string* error_message);

    void set_object_preview(const SpawnedObjectSpec& spec);
    void clear_object_preview();

    bool apply_push_force(const ForceSpec& spec, std::string* error_message);
    void set_force_preview(const ForceSpec& spec);
    void clear_force_preview();

    float timestep() const;
    bool can_author_scene() const;
    const std::vector<BodyRenderState>& render_bodies() const;
    const std::vector<BodyRenderState>& preview_bodies() const;
    const SceneDocument& scene_document() const;
    const SceneEntitySelection& selected_entity() const;
    const SceneAxisMoveSession& axis_move_session() const;
    const SceneAxisRotateSession& axis_rotate_session() const;
    const SceneUniformScaleSession& uniform_scale_session() const;
    bool has_active_tool_session() const;
    bool can_edit_selected_entity() const;
    bool select_entity(SceneEntityId id, SceneEntityKind kind);
    void clear_selected_entity();
    bool pick_entity_from_ray(const float ray_origin[3], const float ray_direction[3], SceneEntityId* entity_id, SceneEntityKind* entity_kind) const;
    bool begin_axis_move(SceneMoveAxis axis);
    bool update_axis_move_preview(float axis_delta);
    bool commit_axis_move();
    void cancel_axis_move();
    bool begin_axis_rotate(SceneMoveAxis axis);
    bool update_axis_rotate_preview(float angle_delta_degrees);
    bool commit_axis_rotate();
    void cancel_axis_rotate();
    bool begin_uniform_scale();
    bool update_uniform_scale_preview(float scale_factor);
    bool commit_uniform_scale();
    void cancel_uniform_scale();
    bool resolve_runtime_entity_for_body(const hkpRigidBody* body, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const;

private:
    friend class TransformSessionController;

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

    void initialize_runtime();
    void shutdown_runtime();
    void clear_scene_contents();
    void destroy_world();
    void create_world();
    void create_ground_body();
    void create_dynamic_box();
    void create_dynamic_sphere();
    void seed_default_scene_objects();
    void update_ground_scene_object();
    void create_spawned_objects();
    void create_force_entities();
    void add_loaded_ragdoll();
    void apply_continuous_force_entities();
    void step_ragdoll_runtimes();
    void sync_render_state();
    void add_body(SceneEntityId entity_id, SceneEntityKind entity_kind, hkpRigidBody* body, const BodyRenderState& state);
    void add_render_body(SceneEntityId entity_id, SceneEntityKind entity_kind, hkpRigidBody* body, const BodyRenderState& state);
    void remove_loaded_ragdoll_from_world();
    void unload_ragdoll();
    void rebuild_preview_bodies();
    void refresh_selection_highlight();
    bool apply_entity_runtime_position(SceneEntityId id, SceneEntityKind kind, const float position[3]);
    bool apply_entity_runtime_rotation(SceneEntityId id, SceneEntityKind kind, const float rotation_degrees[3]);
    bool apply_entity_runtime_scale(SceneEntityId id, SceneEntityKind kind, const float scale[3]);
    bool normalize_object_spec(const SpawnedObjectSpec& spec, SpawnedObjectSpec* normalized_spec, std::string* error_message) const;
    void release_ragdoll_runtime_at(std::size_t runtime_index);
    const RagdollSceneEntity* primary_ragdoll_entity() const;
    RagdollSceneEntity* primary_ragdoll_entity();
    const RagdollSceneEntity* active_ragdoll_entity() const;
    RagdollSceneEntity* active_ragdoll_entity();
    const RagdollSceneEntity* find_ragdoll_entity(SceneEntityId entity_id) const;
    const ForceSceneEntity* find_force_entity(SceneEntityId entity_id) const;
    ForceSceneEntity* find_force_entity(SceneEntityId entity_id);
    const PhysicsObjectSceneEntity* find_object_entity(SceneEntityId entity_id) const;
    PhysicsObjectSceneEntity* find_object_entity(SceneEntityId entity_id);
    RagdollRuntime* find_ragdoll_runtime(SceneEntityId entity_id);
    const RagdollRuntime* find_ragdoll_runtime(SceneEntityId entity_id) const;
    RagdollRuntime* find_ragdoll_runtime_owning_body(const hkpRigidBody* body);
    RagdollRuntime* primary_ragdoll_runtime();
    RagdollRuntime* active_ragdoll_runtime();
    const RagdollRuntime* primary_ragdoll_runtime() const;
    const RagdollRuntime* active_ragdoll_runtime() const;
    const RuntimeBodyBinding* find_runtime_body_binding(const hkpRigidBody* body) const;
    const RuntimeEntityBinding* find_runtime_entity_binding(SceneEntityId entity_id, SceneEntityKind entity_kind) const;
    bool pick_force_entity_from_ray(const float ray_origin[3], const float ray_direction[3], float max_distance, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const;

    bool create_body_from_spec(
        const SpawnedObjectSpec& spec,
        hkpRigidBody** body,
        BodyRenderState* state,
        std::string* error_message);
    bool build_render_state_from_spec(const SpawnedObjectSpec& spec, bool is_preview, BodyRenderState* state) const;
    bool find_force_target(
        const ForceSpec& spec,
        hkpRigidBody** body,
        float hit_point[3],
        float direction[3],
        std::string* error_message) const;

    static int s_runtime_refcount;

    GroundMode m_ground_mode;
    bool m_is_playing;
    bool m_runtime_matches_scene;
    RagdollRuntimeManager* m_ragdoll_runtime_manager;
    SimulationWorld* m_simulation_world;
    TransformSessionController* m_transform_session_controller;
    float m_timestep;
    hkpWorld* m_world;
    hkpBoxShape* m_ground_shape;
    hkpBoxShape* m_box_shape;
    hkpSphereShape* m_sphere_shape;
    bool m_has_object_preview;
    bool m_has_force_preview;
    SceneDocument m_scene_document;
    SpawnedObjectSpec m_object_preview_spec;
    ForceSpec m_force_preview_spec;
    std::vector<hkpRigidBody*> m_owned_bodies;
    std::vector<RuntimeBodyBinding> m_runtime_bodies;
    std::map<const hkpRigidBody*, std::size_t> m_runtime_body_lookup;
    std::vector<RuntimeEntityBinding> m_runtime_entities;
    std::vector<BodyRenderState> m_render_bodies;
    std::vector<BodyRenderState> m_preview_bodies;
    SceneEntityId m_default_ground_entity_id;
};

#endif