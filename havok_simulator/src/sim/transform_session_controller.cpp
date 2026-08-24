#include "transform_session_controller.h"

#include "simulation_controller.h"

TransformSessionController::TransformSessionController(SimulationController& host, SceneDocument& scene_document)
    : m_host(host)
    , m_scene_document(scene_document)
{
}

bool TransformSessionController::has_active_tool_session() const
{
    return m_scene_document.axis_move_session().active ||
        m_scene_document.axis_rotate_session().active ||
        m_scene_document.uniform_scale_session().active;
}

bool TransformSessionController::begin_axis_move(SceneMoveAxis axis)
{
    const SceneAxisMoveSession& move_session = m_scene_document.axis_move_session();

    if (m_scene_document.axis_rotate_session().active || m_scene_document.uniform_scale_session().active)
    {
        return false;
    }

    if (!m_host.can_author_scene() && !move_session.active)
    {
        return false;
    }

    if (!m_scene_document.begin_axis_move(axis))
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_position(
        m_scene_document.axis_move_session().entity_id,
        m_scene_document.axis_move_session().entity_kind,
        m_scene_document.axis_move_session().preview_position))
    {
        m_scene_document.cancel_axis_move();
        return false;
    }

    return true;
}

bool TransformSessionController::update_axis_move_preview(float axis_delta)
{
    const SceneAxisMoveSession& move_session = m_scene_document.axis_move_session();

    if (!move_session.active)
    {
        return false;
    }

    if (!m_scene_document.update_axis_move_preview(axis_delta))
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_position(
        move_session.entity_id,
        move_session.entity_kind,
        m_scene_document.axis_move_session().preview_position))
    {
        return false;
    }

    m_host.m_runtime_matches_scene = false;
    return true;
}

bool TransformSessionController::commit_axis_move()
{
    const SceneAxisMoveSession move_session = m_scene_document.axis_move_session();
    const PhysicsObjectSceneEntity* object = 0;

    if (!move_session.active)
    {
        return false;
    }

    if (!m_scene_document.commit_axis_move())
    {
        return false;
    }

    if (move_session.entity_kind == SceneEntityKindPhysicsObject)
    {
        object = find_object_entity(move_session.entity_id);
        if (object && object->object_spec.body_type == SimulationController::BodyStatic)
        {
            m_host.reset();
            return true;
        }
    }

    m_host.m_runtime_matches_scene = true;
    return true;
}

void TransformSessionController::cancel_axis_move()
{
    const SceneAxisMoveSession move_session = m_scene_document.axis_move_session();

    if (!move_session.active)
    {
        return;
    }

    m_host.apply_entity_runtime_position(move_session.entity_id, move_session.entity_kind, move_session.committed_position);
    m_scene_document.cancel_axis_move();
    m_host.m_runtime_matches_scene = true;
}

bool TransformSessionController::begin_axis_rotate(SceneMoveAxis axis)
{
    const SceneAxisRotateSession& rotate_session = m_scene_document.axis_rotate_session();

    if (m_scene_document.axis_move_session().active || m_scene_document.uniform_scale_session().active)
    {
        return false;
    }

    if (!m_host.can_author_scene() && !rotate_session.active)
    {
        return false;
    }

    if (!m_scene_document.begin_axis_rotate(axis))
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_rotation(
        m_scene_document.axis_rotate_session().entity_id,
        m_scene_document.axis_rotate_session().entity_kind,
        m_scene_document.axis_rotate_session().preview_rotation_degrees))
    {
        m_scene_document.cancel_axis_rotate();
        return false;
    }

    return true;
}

bool TransformSessionController::update_axis_rotate_preview(float angle_delta_degrees)
{
    const SceneAxisRotateSession& rotate_session = m_scene_document.axis_rotate_session();

    if (!rotate_session.active)
    {
        return false;
    }

    if (!m_scene_document.update_axis_rotate_preview(angle_delta_degrees))
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_rotation(
        rotate_session.entity_id,
        rotate_session.entity_kind,
        m_scene_document.axis_rotate_session().preview_rotation_degrees))
    {
        return false;
    }

    m_host.m_runtime_matches_scene = false;
    return true;
}

bool TransformSessionController::commit_axis_rotate()
{
    const SceneAxisRotateSession rotate_session = m_scene_document.axis_rotate_session();
    const PhysicsObjectSceneEntity* object = 0;

    if (!rotate_session.active)
    {
        return false;
    }

    if (!m_scene_document.commit_axis_rotate())
    {
        return false;
    }

    if (rotate_session.entity_kind == SceneEntityKindPhysicsObject)
    {
        object = find_object_entity(rotate_session.entity_id);
        if (object && object->object_spec.body_type == SimulationController::BodyStatic)
        {
            m_host.reset();
            return true;
        }
    }

    m_host.m_runtime_matches_scene = true;
    return true;
}

void TransformSessionController::cancel_axis_rotate()
{
    const SceneAxisRotateSession rotate_session = m_scene_document.axis_rotate_session();

    if (!rotate_session.active)
    {
        return;
    }

    m_host.apply_entity_runtime_rotation(
        rotate_session.entity_id,
        rotate_session.entity_kind,
        rotate_session.committed_rotation_degrees);
    m_scene_document.cancel_axis_rotate();
    m_host.m_runtime_matches_scene = true;
}

bool TransformSessionController::begin_uniform_scale()
{
    const SceneUniformScaleSession& scale_session = m_scene_document.uniform_scale_session();
    const PhysicsObjectSceneEntity* object = 0;

    if (m_scene_document.axis_move_session().active || m_scene_document.axis_rotate_session().active)
    {
        return false;
    }

    if (!m_host.can_author_scene() && !scale_session.active)
    {
        return false;
    }

    // Forces have no geometric shape to validate; the scale gesture drives their
    // cylinder radius. Physics objects still require a scalable shape.
    if (m_scene_document.selected_entity().kind != SceneEntityKindForce)
    {
        object = find_object_entity(m_scene_document.selected_entity().id);
        if (!object || !can_uniform_scale_object(*object))
        {
            return false;
        }
    }

    if (!m_scene_document.begin_uniform_scale())
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_scale(
        m_scene_document.uniform_scale_session().entity_id,
        m_scene_document.uniform_scale_session().entity_kind,
        m_scene_document.uniform_scale_session().preview_scale))
    {
        m_scene_document.cancel_uniform_scale();
        return false;
    }

    return true;
}

bool TransformSessionController::set_uniform_scale_axis(SceneMoveAxis axis)
{
    const SceneUniformScaleSession& scale_session = m_scene_document.uniform_scale_session();
    const PhysicsObjectSceneEntity* object = 0;

    if (!scale_session.active)
    {
        return false;
    }

    if (axis != SceneMoveAxisNone)
    {
        if (scale_session.entity_kind != SceneEntityKindPhysicsObject)
        {
            return false;
        }

        object = find_object_entity(scale_session.entity_id);
        if (!object || !can_axis_scale_object(*object))
        {
            return false;
        }
    }

    return m_scene_document.set_uniform_scale_axis(axis);
}

bool TransformSessionController::update_uniform_scale_preview(float scale_factor)
{
    const SceneUniformScaleSession& scale_session = m_scene_document.uniform_scale_session();

    if (!scale_session.active)
    {
        return false;
    }

    if (!m_scene_document.update_uniform_scale_preview(scale_factor))
    {
        return false;
    }

    if (!m_host.apply_entity_runtime_scale(
        scale_session.entity_id,
        scale_session.entity_kind,
        m_scene_document.uniform_scale_session().preview_scale))
    {
        return false;
    }

    m_host.m_runtime_matches_scene = false;
    return true;
}

bool TransformSessionController::commit_uniform_scale()
{
    const SceneUniformScaleSession scale_session = m_scene_document.uniform_scale_session();

    if (!scale_session.active)
    {
        return false;
    }

    if (!m_scene_document.commit_uniform_scale())
    {
        return false;
    }

    m_host.reset();
    return true;
}

void TransformSessionController::cancel_uniform_scale()
{
    const SceneUniformScaleSession scale_session = m_scene_document.uniform_scale_session();

    if (!scale_session.active)
    {
        return;
    }

    m_host.apply_entity_runtime_scale(
        scale_session.entity_id,
        scale_session.entity_kind,
        scale_session.committed_scale);
    m_scene_document.cancel_uniform_scale();
    m_host.m_runtime_matches_scene = true;
}

bool TransformSessionController::can_axis_scale_object(const PhysicsObjectSceneEntity& object) const
{
    if (!object.record.editable)
    {
        return false;
    }

    return object.object_spec.object_type == SimulationController::ObjectCube ||
        object.object_spec.object_type == SimulationController::ObjectWedge;
}

bool TransformSessionController::can_uniform_scale_object(const PhysicsObjectSceneEntity& object) const
{
    if (!object.record.editable)
    {
        return false;
    }

    return object.object_spec.object_type == SimulationController::ObjectCube ||
        object.object_spec.object_type == SimulationController::ObjectSphere ||
        object.object_spec.object_type == SimulationController::ObjectWedge;
}

const PhysicsObjectSceneEntity* TransformSessionController::find_object_entity(SceneEntityId entity_id) const
{
    const std::vector<PhysicsObjectSceneEntity>& objects = m_scene_document.objects();

    for (std::size_t object_index = 0; object_index < objects.size(); ++object_index)
    {
        if (objects[object_index].record.id == entity_id)
        {
            return &objects[object_index];
        }
    }

    return 0;
}