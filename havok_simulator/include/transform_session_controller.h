#ifndef HAVOK_SCENE_APP_TRANSFORM_SESSION_CONTROLLER_H
#define HAVOK_SCENE_APP_TRANSFORM_SESSION_CONTROLLER_H

#include "scene_document.h"

class SimulationController;

class TransformSessionController
{
public:
    TransformSessionController(SimulationController& host, SceneDocument& scene_document);

    bool has_active_tool_session() const;
    bool begin_axis_move(SceneMoveAxis axis);
    bool update_axis_move_preview(float axis_delta);
    bool commit_axis_move();
    void cancel_axis_move();
    bool begin_axis_rotate(SceneMoveAxis axis);
    bool update_axis_rotate_preview(float angle_delta_degrees);
    bool commit_axis_rotate();
    void cancel_axis_rotate();
    bool begin_uniform_scale();
    bool set_uniform_scale_axis(SceneMoveAxis axis);
    bool update_uniform_scale_preview(float scale_factor);
    bool commit_uniform_scale();
    void cancel_uniform_scale();

private:
    bool can_axis_scale_object(const PhysicsObjectSceneEntity& object) const;
    bool can_uniform_scale_object(const PhysicsObjectSceneEntity& object) const;
    const PhysicsObjectSceneEntity* find_object_entity(SceneEntityId entity_id) const;

    SimulationController& m_host;
    SceneDocument& m_scene_document;
};

#endif