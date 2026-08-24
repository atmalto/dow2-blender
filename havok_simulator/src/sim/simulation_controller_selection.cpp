#include "simulation_controller.h"

#include <vector>

#include "simulation_controller_internal.h"
#include "simulation_world.h"
#include "transform_session_controller.h"

using simulation_controller_internal::find_entity_by_id;

const SceneEntitySelection& SimulationController::selected_entity() const
{
    return m_scene_document.selected_entity();
}

const SceneAxisMoveSession& SimulationController::axis_move_session() const
{
    return m_scene_document.axis_move_session();
}

const SceneAxisRotateSession& SimulationController::axis_rotate_session() const
{
    return m_scene_document.axis_rotate_session();
}

const SceneUniformScaleSession& SimulationController::uniform_scale_session() const
{
    return m_scene_document.uniform_scale_session();
}

bool SimulationController::has_active_tool_session() const
{
    return m_transform_session_controller
        ? m_transform_session_controller->has_active_tool_session()
        : false;
}

bool SimulationController::select_entity(SceneEntityId id, SceneEntityKind kind)
{
    const SceneAxisMoveSession& move_session = m_scene_document.axis_move_session();
    const SceneAxisRotateSession& rotate_session = m_scene_document.axis_rotate_session();
    const SceneUniformScaleSession& scale_session = m_scene_document.uniform_scale_session();

    if (move_session.active && (move_session.entity_id != id || move_session.entity_kind != kind))
    {
        cancel_axis_move();
    }

    if (rotate_session.active && (rotate_session.entity_id != id || rotate_session.entity_kind != kind))
    {
        cancel_axis_rotate();
    }

    if (scale_session.active && (scale_session.entity_id != id || scale_session.entity_kind != kind))
    {
        cancel_uniform_scale();
    }

    if (!m_scene_document.select_entity(id, kind))
    {
        return false;
    }

    refresh_selection_highlight();
    return true;
}

void SimulationController::clear_selected_entity()
{
    if (m_scene_document.axis_move_session().active)
    {
        cancel_axis_move();
    }

    if (m_scene_document.axis_rotate_session().active)
    {
        cancel_axis_rotate();
    }

    if (m_scene_document.uniform_scale_session().active)
    {
        cancel_uniform_scale();
    }

    m_scene_document.clear_selection();
    refresh_selection_highlight();
}

bool SimulationController::pick_entity_from_ray(const float ray_origin[3], const float ray_direction[3], SceneEntityId* entity_id, SceneEntityKind* entity_kind) const
{
    if (!m_simulation_world)
    {
        return false;
    }

    return m_simulation_world->pick_entity_from_ray(ray_origin, ray_direction, entity_id, entity_kind);
}

bool SimulationController::begin_axis_move(SceneMoveAxis axis)
{
    return m_transform_session_controller
        ? m_transform_session_controller->begin_axis_move(axis)
        : false;
}

bool SimulationController::update_axis_move_preview(float axis_delta)
{
    return m_transform_session_controller
        ? m_transform_session_controller->update_axis_move_preview(axis_delta)
        : false;
}

bool SimulationController::commit_axis_move()
{
    return m_transform_session_controller
        ? m_transform_session_controller->commit_axis_move()
        : false;
}

void SimulationController::cancel_axis_move()
{
    if (m_transform_session_controller)
    {
        m_transform_session_controller->cancel_axis_move();
    }
}

bool SimulationController::begin_axis_rotate(SceneMoveAxis axis)
{
    return m_transform_session_controller
        ? m_transform_session_controller->begin_axis_rotate(axis)
        : false;
}

bool SimulationController::update_axis_rotate_preview(float angle_delta_degrees)
{
    return m_transform_session_controller
        ? m_transform_session_controller->update_axis_rotate_preview(angle_delta_degrees)
        : false;
}

bool SimulationController::commit_axis_rotate()
{
    return m_transform_session_controller
        ? m_transform_session_controller->commit_axis_rotate()
        : false;
}

void SimulationController::cancel_axis_rotate()
{
    if (m_transform_session_controller)
    {
        m_transform_session_controller->cancel_axis_rotate();
    }
}

bool SimulationController::begin_uniform_scale()
{
    return m_transform_session_controller
        ? m_transform_session_controller->begin_uniform_scale()
        : false;
}

bool SimulationController::set_uniform_scale_axis(SceneMoveAxis axis)
{
    return m_transform_session_controller
        ? m_transform_session_controller->set_uniform_scale_axis(axis)
        : false;
}

bool SimulationController::update_uniform_scale_preview(float scale_factor)
{
    return m_transform_session_controller
        ? m_transform_session_controller->update_uniform_scale_preview(scale_factor)
        : false;
}

bool SimulationController::commit_uniform_scale()
{
    return m_transform_session_controller
        ? m_transform_session_controller->commit_uniform_scale()
        : false;
}

void SimulationController::cancel_uniform_scale()
{
    if (m_transform_session_controller)
    {
        m_transform_session_controller->cancel_uniform_scale();
    }
}

void SimulationController::rebuild_preview_bodies()
{
    m_preview_bodies.clear();

    if (m_has_object_preview)
    {
        BodyRenderState object_preview;
        if (m_simulation_world && m_simulation_world->build_render_state_from_spec(m_object_preview_spec, true, &object_preview))
        {
            m_preview_bodies.push_back(object_preview);
        }
    }

    if (m_has_force_preview)
    {
        m_preview_bodies.push_back(SimulationWorld::build_force_render_state(m_force_preview_spec, true));
    }
}

void SimulationController::refresh_selection_highlight()
{
    if (m_simulation_world)
    {
        m_simulation_world->refresh_selection_highlight(m_scene_document.selected_entity());
    }
}

const ForceSceneEntity* SimulationController::find_force_entity(SceneEntityId entity_id) const
{
    return find_entity_by_id(m_scene_document.forces(), entity_id);
}

ForceSceneEntity* SimulationController::find_force_entity(SceneEntityId entity_id)
{
    return find_entity_by_id(m_scene_document.forces(), entity_id);
}

const PhysicsObjectSceneEntity* SimulationController::find_object_entity(SceneEntityId entity_id) const
{
    return find_entity_by_id(m_scene_document.objects(), entity_id);
}

PhysicsObjectSceneEntity* SimulationController::find_object_entity(SceneEntityId entity_id)
{
    return find_entity_by_id(m_scene_document.objects(), entity_id);
}

bool SimulationController::can_edit_selected_entity() const
{
    const SceneEntitySelection& selected = m_scene_document.selected_entity();

    if (selected.id == 0)
    {
        return false;
    }

    if (selected.kind == SceneEntityKindPhysicsObject)
    {
        const PhysicsObjectSceneEntity* object = find_object_entity(selected.id);
        return object && object->record.editable;
    }

    if (selected.kind == SceneEntityKindRagdoll)
    {
        return find_ragdoll_entity(selected.id) != 0;
    }

    if (selected.kind == SceneEntityKindForce)
    {
        return find_force_entity(selected.id) != 0;
    }

    return false;
}