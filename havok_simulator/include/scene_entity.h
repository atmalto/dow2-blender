#ifndef HAVOK_SCENE_APP_SCENE_ENTITY_H
#define HAVOK_SCENE_APP_SCENE_ENTITY_H

#include <string>

typedef unsigned int SceneEntityId;

enum SceneEntityKind
{
    SceneEntityKindNone = 0,
    SceneEntityKindRagdoll = 1,
    SceneEntityKindPhysicsObject = 2,
    SceneEntityKindForce = 3
};

enum SceneMoveAxis
{
    SceneMoveAxisNone = 0,
    SceneMoveAxisX = 1,
    SceneMoveAxisY = 2,
    SceneMoveAxisZ = 3
};

struct SceneEntitySelection
{
    SceneEntitySelection()
        : id(0)
        , kind(SceneEntityKindNone)
    {
    }

    SceneEntityId id;
    SceneEntityKind kind;
};

struct SceneEntityRecord
{
    SceneEntityRecord()
        : id(0)
        , kind(SceneEntityKindNone)
        , selectable(false)
        , movable(false)
        , editable(false)
        , deletable(false)
    {
    }

    SceneEntityId id;
    SceneEntityKind kind;
    std::string name;
    bool selectable;
    bool movable;
    bool editable;
    bool deletable;
};

struct SceneAxisMoveSession
{
    SceneAxisMoveSession()
        : active(false)
        , entity_id(0)
        , entity_kind(SceneEntityKindNone)
        , axis(SceneMoveAxisNone)
    {
        committed_position[0] = 0.0f;
        committed_position[1] = 0.0f;
        committed_position[2] = 0.0f;
        preview_position[0] = 0.0f;
        preview_position[1] = 0.0f;
        preview_position[2] = 0.0f;
    }

    bool active;
    SceneEntityId entity_id;
    SceneEntityKind entity_kind;
    SceneMoveAxis axis;
    float committed_position[3];
    float preview_position[3];
};

struct SceneAxisRotateSession
{
    SceneAxisRotateSession()
        : active(false)
        , entity_id(0)
        , entity_kind(SceneEntityKindNone)
        , axis(SceneMoveAxisNone)
    {
        pivot_position[0] = 0.0f;
        pivot_position[1] = 0.0f;
        pivot_position[2] = 0.0f;
        committed_rotation_degrees[0] = 0.0f;
        committed_rotation_degrees[1] = 0.0f;
        committed_rotation_degrees[2] = 0.0f;
        preview_rotation_degrees[0] = 0.0f;
        preview_rotation_degrees[1] = 0.0f;
        preview_rotation_degrees[2] = 0.0f;
    }

    bool active;
    SceneEntityId entity_id;
    SceneEntityKind entity_kind;
    SceneMoveAxis axis;
    float pivot_position[3];
    float committed_rotation_degrees[3];
    float preview_rotation_degrees[3];
};

struct SceneUniformScaleSession
{
    SceneUniformScaleSession()
        : active(false)
        , entity_id(0)
        , entity_kind(SceneEntityKindNone)
    {
        committed_scale[0] = 1.0f;
        committed_scale[1] = 1.0f;
        committed_scale[2] = 1.0f;
        preview_scale[0] = 1.0f;
        preview_scale[1] = 1.0f;
        preview_scale[2] = 1.0f;
    }

    bool active;
    SceneEntityId entity_id;
    SceneEntityKind entity_kind;
    float committed_scale[3];
    float preview_scale[3];
};

#endif