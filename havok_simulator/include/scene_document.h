#ifndef HAVOK_SCENE_APP_SCENE_DOCUMENT_H
#define HAVOK_SCENE_APP_SCENE_DOCUMENT_H

#include <string>
#include <vector>

#include "scene_entity.h"

struct ConvexHullVertex
{
    ConvexHullVertex()
        : x(0.0f)
        , y(0.0f)
        , z(0.0f)
    {
    }

    ConvexHullVertex(float px, float py, float pz)
        : x(px)
        , y(py)
        , z(pz)
    {
    }

    float x;
    float y;
    float z;
};

struct SpawnedObjectSceneSpec
{
    SpawnedObjectSceneSpec()
        : object_type(0)
        , body_type(0)
        , restitution(0.4f)
        , mass(10.0f)
        , shape_radius(0.05f)
    {
        position[0] = position[1] = position[2] = 0.0f;
        rotation_degrees[0] = rotation_degrees[1] = rotation_degrees[2] = 0.0f;
        scale[0] = scale[1] = scale[2] = 1.0f;
    }

    int object_type;
    int body_type;
    float position[3];
    float rotation_degrees[3];
    float scale[3];
    float restitution;
    float mass;
    float shape_radius;
    std::vector<ConvexHullVertex> convex_hull_vertices;
};

struct ForceSceneSpec
{
    float position[3];
    float rotation_degrees[3];
    float strength;
    int mode;
    bool active;
};

struct RagdollSceneSpec
{
    std::string asset_path;
    float position[3];
};

struct RagdollSceneEntity
{
    SceneEntityRecord record;
    RagdollSceneSpec ragdoll;
};

struct PhysicsObjectSceneEntity
{
    SceneEntityRecord record;
    SpawnedObjectSceneSpec object_spec;
};

struct ForceSceneEntity
{
    SceneEntityRecord record;
    ForceSceneSpec force_spec;
};

class SceneDocument
{
public:
    SceneDocument();

    void clear();
    void clear_ragdolls();
    void clear_selection();
    void cancel_axis_move();
    void cancel_axis_rotate();
    void cancel_uniform_scale();

    SceneEntityId add_ragdoll(const RagdollSceneSpec& spec, const char* name);
    SceneEntityId add_object(const SpawnedObjectSceneSpec& spec, const char* name, bool editable);
    SceneEntityId add_force(const ForceSceneSpec& spec, const char* name);
    bool remove_entity(SceneEntityId id, SceneEntityKind kind);
    SceneEntityId duplicate_entity(SceneEntityId id, SceneEntityKind kind);

    bool has_entity(SceneEntityId id, SceneEntityKind kind) const;
    bool select_entity(SceneEntityId id, SceneEntityKind kind);
    const SceneEntitySelection& selected_entity() const;
    bool begin_axis_move(SceneMoveAxis axis);
    bool update_axis_move_preview(float axis_delta);
    bool commit_axis_move();
    const SceneAxisMoveSession& axis_move_session() const;
    bool begin_axis_rotate(SceneMoveAxis axis);
    bool update_axis_rotate_preview(float angle_delta_degrees);
    bool commit_axis_rotate();
    const SceneAxisRotateSession& axis_rotate_session() const;
    bool begin_uniform_scale();
    bool update_uniform_scale_preview(float scale_factor);
    bool commit_uniform_scale();
    const SceneUniformScaleSession& uniform_scale_session() const;

    const std::vector<RagdollSceneEntity>& ragdolls() const;
    std::vector<RagdollSceneEntity>& ragdolls();
    const std::vector<PhysicsObjectSceneEntity>& objects() const;
    std::vector<PhysicsObjectSceneEntity>& objects();
    const std::vector<ForceSceneEntity>& forces() const;
    std::vector<ForceSceneEntity>& forces();

private:
    SceneEntityId allocate_entity_id();
    static SceneEntityRecord make_record(SceneEntityKind kind, SceneEntityId id, const char* name);
    bool get_entity_position(SceneEntityId id, SceneEntityKind kind, float position[3]) const;
    bool set_entity_position(SceneEntityId id, SceneEntityKind kind, const float position[3]);
    bool get_entity_rotation(SceneEntityId id, SceneEntityKind kind, float rotation_degrees[3]) const;
    bool set_entity_rotation(SceneEntityId id, SceneEntityKind kind, const float rotation_degrees[3]);
    bool get_entity_scale(SceneEntityId id, SceneEntityKind kind, float scale[3]) const;
    bool set_entity_scale(SceneEntityId id, SceneEntityKind kind, const float scale[3]);
    bool is_entity_movable(SceneEntityId id, SceneEntityKind kind) const;
    bool is_entity_rotatable(SceneEntityId id, SceneEntityKind kind) const;
    bool is_entity_scalable(SceneEntityId id, SceneEntityKind kind) const;

    SceneEntityId m_next_entity_id;
    SceneEntitySelection m_selected_entity;
    SceneAxisMoveSession m_axis_move_session;
    SceneAxisRotateSession m_axis_rotate_session;
    SceneUniformScaleSession m_uniform_scale_session;
    std::vector<RagdollSceneEntity> m_ragdolls;
    std::vector<PhysicsObjectSceneEntity> m_objects;
    std::vector<ForceSceneEntity> m_forces;
};

#endif