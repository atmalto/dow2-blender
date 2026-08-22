#include "scene_document.h"

#include <cmath>

SceneDocument::SceneDocument()
    : m_next_entity_id(1)
{
}

void SceneDocument::clear()
{
    m_ragdolls.clear();
    m_objects.clear();
    m_forces.clear();
    cancel_axis_move();
    cancel_axis_rotate();
    cancel_uniform_scale();
    clear_selection();
}

void SceneDocument::clear_ragdolls()
{
    m_ragdolls.clear();

    if (m_axis_move_session.active && m_axis_move_session.entity_kind == SceneEntityKindRagdoll)
    {
        cancel_axis_move();
    }

    if (m_selected_entity.kind == SceneEntityKindRagdoll)
    {
        clear_selection();
    }
}

void SceneDocument::clear_selection()
{
    m_selected_entity = SceneEntitySelection();
}

void SceneDocument::cancel_axis_move()
{
    m_axis_move_session = SceneAxisMoveSession();
}

void SceneDocument::cancel_axis_rotate()
{
    m_axis_rotate_session = SceneAxisRotateSession();
}

void SceneDocument::cancel_uniform_scale()
{
    m_uniform_scale_session = SceneUniformScaleSession();
}

SceneEntityId SceneDocument::add_ragdoll(const RagdollSceneSpec& spec, const char* name)
{
    RagdollSceneEntity entity;
    entity.record = make_record(SceneEntityKindRagdoll, allocate_entity_id(), name);
    entity.record.selectable = true;
    entity.record.movable = true;
    entity.record.editable = true;
    entity.record.deletable = true;
    entity.ragdoll = spec;
    m_ragdolls.push_back(entity);
    return entity.record.id;
}

SceneEntityId SceneDocument::add_object(const SpawnedObjectSceneSpec& spec, const char* name, bool editable)
{
    PhysicsObjectSceneEntity entity;
    entity.record = make_record(SceneEntityKindPhysicsObject, allocate_entity_id(), name);
    entity.record.selectable = true;
    entity.record.movable = true;
    entity.record.editable = editable;
    entity.record.deletable = true;
    entity.object_spec = spec;
    m_objects.push_back(entity);
    return entity.record.id;
}

SceneEntityId SceneDocument::add_force(const ForceSceneSpec& spec, const char* name)
{
    ForceSceneEntity entity;
    entity.record = make_record(SceneEntityKindForce, allocate_entity_id(), name);
    entity.record.selectable = true;
    entity.record.movable = true;
    entity.record.editable = true;
    entity.record.deletable = true;
    entity.force_spec = spec;
    m_forces.push_back(entity);
    return entity.record.id;
}

bool SceneDocument::remove_entity(SceneEntityId id, SceneEntityKind kind)
{
    std::size_t entity_index = 0;

    if (m_axis_move_session.active && m_axis_move_session.entity_id == id && m_axis_move_session.entity_kind == kind)
    {
        cancel_axis_move();
    }

    if (m_axis_rotate_session.active && m_axis_rotate_session.entity_id == id && m_axis_rotate_session.entity_kind == kind)
    {
        cancel_axis_rotate();
    }

    if (m_uniform_scale_session.active && m_uniform_scale_session.entity_id == id && m_uniform_scale_session.entity_kind == kind)
    {
        cancel_uniform_scale();
    }

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                m_ragdolls.erase(m_ragdolls.begin() + entity_index);
                if (m_selected_entity.id == id && m_selected_entity.kind == kind)
                {
                    clear_selection();
                }
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                m_objects.erase(m_objects.begin() + entity_index);
                if (m_selected_entity.id == id && m_selected_entity.kind == kind)
                {
                    clear_selection();
                }
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                m_forces.erase(m_forces.begin() + entity_index);
                if (m_selected_entity.id == id && m_selected_entity.kind == kind)
                {
                    clear_selection();
                }
                return true;
            }
        }
    }

    return false;
}

SceneEntityId SceneDocument::duplicate_entity(SceneEntityId id, SceneEntityKind kind)
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                RagdollSceneEntity duplicate = m_ragdolls[entity_index];
                duplicate.record.id = allocate_entity_id();
                duplicate.record.name = duplicate.record.name + " Copy";
                m_ragdolls.push_back(duplicate);
                return duplicate.record.id;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                PhysicsObjectSceneEntity duplicate = m_objects[entity_index];
                duplicate.record.id = allocate_entity_id();
                duplicate.record.name = duplicate.record.name + " Copy";
                m_objects.push_back(duplicate);
                return duplicate.record.id;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                ForceSceneEntity duplicate = m_forces[entity_index];
                duplicate.record.id = allocate_entity_id();
                duplicate.record.name = duplicate.record.name + " Copy";
                m_forces.push_back(duplicate);
                return duplicate.record.id;
            }
        }
    }

    return 0;
}

bool SceneDocument::has_entity(SceneEntityId id, SceneEntityKind kind) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                return true;
            }
        }
    }

    return false;
}

bool SceneDocument::select_entity(SceneEntityId id, SceneEntityKind kind)
{
    if (id == 0 || kind == SceneEntityKindNone)
    {
        clear_selection();
        return true;
    }

    if (!has_entity(id, kind))
    {
        return false;
    }

    m_selected_entity.id = id;
    m_selected_entity.kind = kind;
    return true;
}

const SceneEntitySelection& SceneDocument::selected_entity() const
{
    return m_selected_entity;
}

bool SceneDocument::begin_axis_move(SceneMoveAxis axis)
{
    if (axis == SceneMoveAxisNone || m_selected_entity.id == 0 || !is_entity_movable(m_selected_entity.id, m_selected_entity.kind))
    {
        return false;
    }

    m_axis_move_session = SceneAxisMoveSession();
    m_axis_move_session.active = true;
    m_axis_move_session.entity_id = m_selected_entity.id;
    m_axis_move_session.entity_kind = m_selected_entity.kind;
    m_axis_move_session.axis = axis;

    if (!get_entity_position(m_selected_entity.id, m_selected_entity.kind, m_axis_move_session.committed_position))
    {
        cancel_axis_move();
        return false;
    }

    m_axis_move_session.preview_position[0] = m_axis_move_session.committed_position[0];
    m_axis_move_session.preview_position[1] = m_axis_move_session.committed_position[1];
    m_axis_move_session.preview_position[2] = m_axis_move_session.committed_position[2];
    return true;
}

bool SceneDocument::update_axis_move_preview(float axis_delta)
{
    int axis_index = -1;

    if (!m_axis_move_session.active)
    {
        return false;
    }

    if (m_axis_move_session.axis == SceneMoveAxisX)
    {
        axis_index = 0;
    }
    else if (m_axis_move_session.axis == SceneMoveAxisY)
    {
        axis_index = 1;
    }
    else if (m_axis_move_session.axis == SceneMoveAxisZ)
    {
        axis_index = 2;
    }

    if (axis_index < 0)
    {
        return false;
    }

    m_axis_move_session.preview_position[0] = m_axis_move_session.committed_position[0];
    m_axis_move_session.preview_position[1] = m_axis_move_session.committed_position[1];
    m_axis_move_session.preview_position[2] = m_axis_move_session.committed_position[2];
    m_axis_move_session.preview_position[axis_index] += axis_delta;
    return true;
}

bool SceneDocument::commit_axis_move()
{
    if (!m_axis_move_session.active)
    {
        return false;
    }

    const bool committed = set_entity_position(
        m_axis_move_session.entity_id,
        m_axis_move_session.entity_kind,
        m_axis_move_session.preview_position);

    cancel_axis_move();
    return committed;
}

const SceneAxisMoveSession& SceneDocument::axis_move_session() const
{
    return m_axis_move_session;
}

bool SceneDocument::begin_axis_rotate(SceneMoveAxis axis)
{
    if (axis == SceneMoveAxisNone || m_selected_entity.id == 0 || !is_entity_rotatable(m_selected_entity.id, m_selected_entity.kind))
    {
        return false;
    }

    m_axis_rotate_session = SceneAxisRotateSession();
    m_axis_rotate_session.active = true;
    m_axis_rotate_session.entity_id = m_selected_entity.id;
    m_axis_rotate_session.entity_kind = m_selected_entity.kind;
    m_axis_rotate_session.axis = axis;

    if (!get_entity_position(m_selected_entity.id, m_selected_entity.kind, m_axis_rotate_session.pivot_position) ||
        !get_entity_rotation(m_selected_entity.id, m_selected_entity.kind, m_axis_rotate_session.committed_rotation_degrees))
    {
        cancel_axis_rotate();
        return false;
    }

    m_axis_rotate_session.preview_rotation_degrees[0] = m_axis_rotate_session.committed_rotation_degrees[0];
    m_axis_rotate_session.preview_rotation_degrees[1] = m_axis_rotate_session.committed_rotation_degrees[1];
    m_axis_rotate_session.preview_rotation_degrees[2] = m_axis_rotate_session.committed_rotation_degrees[2];
    return true;
}

bool SceneDocument::update_axis_rotate_preview(float angle_delta_degrees)
{
    int axis_index = -1;

    if (!m_axis_rotate_session.active)
    {
        return false;
    }

    if (m_axis_rotate_session.axis == SceneMoveAxisX)
    {
        axis_index = 0;
    }
    else if (m_axis_rotate_session.axis == SceneMoveAxisY)
    {
        axis_index = 1;
    }
    else if (m_axis_rotate_session.axis == SceneMoveAxisZ)
    {
        axis_index = 2;
    }

    if (axis_index < 0)
    {
        return false;
    }

    m_axis_rotate_session.preview_rotation_degrees[0] = m_axis_rotate_session.committed_rotation_degrees[0];
    m_axis_rotate_session.preview_rotation_degrees[1] = m_axis_rotate_session.committed_rotation_degrees[1];
    m_axis_rotate_session.preview_rotation_degrees[2] = m_axis_rotate_session.committed_rotation_degrees[2];
    m_axis_rotate_session.preview_rotation_degrees[axis_index] += angle_delta_degrees;
    return true;
}

bool SceneDocument::commit_axis_rotate()
{
    if (!m_axis_rotate_session.active)
    {
        return false;
    }

    const bool committed = set_entity_rotation(
        m_axis_rotate_session.entity_id,
        m_axis_rotate_session.entity_kind,
        m_axis_rotate_session.preview_rotation_degrees);

    cancel_axis_rotate();
    return committed;
}

const SceneAxisRotateSession& SceneDocument::axis_rotate_session() const
{
    return m_axis_rotate_session;
}

bool SceneDocument::begin_uniform_scale()
{
    if (m_selected_entity.id == 0 || !is_entity_scalable(m_selected_entity.id, m_selected_entity.kind))
    {
        return false;
    }

    m_uniform_scale_session = SceneUniformScaleSession();
    m_uniform_scale_session.active = true;
    m_uniform_scale_session.entity_id = m_selected_entity.id;
    m_uniform_scale_session.entity_kind = m_selected_entity.kind;

    // Force radius lives in a tight 0-2 range, so scaling must feel far gentler
    // than a rigid body. A sub-1 sensitivity dampens the drag exponent.
    m_uniform_scale_session.sensitivity =
        (m_selected_entity.kind == SceneEntityKindForce) ? 0.3f : 1.0f;

    if (!get_entity_scale(m_selected_entity.id, m_selected_entity.kind, m_uniform_scale_session.committed_scale))
    {
        cancel_uniform_scale();
        return false;
    }

    m_uniform_scale_session.preview_scale[0] = m_uniform_scale_session.committed_scale[0];
    m_uniform_scale_session.preview_scale[1] = m_uniform_scale_session.committed_scale[1];
    m_uniform_scale_session.preview_scale[2] = m_uniform_scale_session.committed_scale[2];
    return true;
}

bool SceneDocument::update_uniform_scale_preview(float scale_factor)
{
    const float min_scale = 0.01f;
    int axis_index = 0;
    float effective_factor = scale_factor;

    if (!m_uniform_scale_session.active || scale_factor <= 0.0f)
    {
        return false;
    }

    // Dampen the drag response for gentler entities (e.g. force radius) by
    // compressing the multiplicative factor towards 1.0 via its exponent.
    if (m_uniform_scale_session.sensitivity != 1.0f)
    {
        effective_factor = std::pow(scale_factor, m_uniform_scale_session.sensitivity);
    }

    for (axis_index = 0; axis_index < 3; ++axis_index)
    {
        float scaled_value = m_uniform_scale_session.committed_scale[axis_index] * effective_factor;
        if (scaled_value < min_scale)
        {
            scaled_value = min_scale;
        }

        m_uniform_scale_session.preview_scale[axis_index] = scaled_value;
    }

    return true;
}

bool SceneDocument::commit_uniform_scale()
{
    if (!m_uniform_scale_session.active)
    {
        return false;
    }

    const bool committed = set_entity_scale(
        m_uniform_scale_session.entity_id,
        m_uniform_scale_session.entity_kind,
        m_uniform_scale_session.preview_scale);

    cancel_uniform_scale();
    return committed;
}

const SceneUniformScaleSession& SceneDocument::uniform_scale_session() const
{
    return m_uniform_scale_session;
}

const std::vector<RagdollSceneEntity>& SceneDocument::ragdolls() const
{
    return m_ragdolls;
}

std::vector<RagdollSceneEntity>& SceneDocument::ragdolls()
{
    return m_ragdolls;
}

const std::vector<PhysicsObjectSceneEntity>& SceneDocument::objects() const
{
    return m_objects;
}

std::vector<PhysicsObjectSceneEntity>& SceneDocument::objects()
{
    return m_objects;
}

const std::vector<ForceSceneEntity>& SceneDocument::forces() const
{
    return m_forces;
}

std::vector<ForceSceneEntity>& SceneDocument::forces()
{
    return m_forces;
}

SceneEntityId SceneDocument::allocate_entity_id()
{
    const SceneEntityId id = m_next_entity_id;
    ++m_next_entity_id;
    return id;
}

SceneEntityRecord SceneDocument::make_record(SceneEntityKind kind, SceneEntityId id, const char* name)
{
    SceneEntityRecord record;
    record.id = id;
    record.kind = kind;
    record.name = name ? name : "";
    return record;
}

bool SceneDocument::get_entity_position(SceneEntityId id, SceneEntityKind kind, float position[3]) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                position[0] = m_ragdolls[entity_index].ragdoll.position[0];
                position[1] = m_ragdolls[entity_index].ragdoll.position[1];
                position[2] = m_ragdolls[entity_index].ragdoll.position[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                position[0] = m_objects[entity_index].object_spec.position[0];
                position[1] = m_objects[entity_index].object_spec.position[1];
                position[2] = m_objects[entity_index].object_spec.position[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                position[0] = m_forces[entity_index].force_spec.position[0];
                position[1] = m_forces[entity_index].force_spec.position[1];
                position[2] = m_forces[entity_index].force_spec.position[2];
                return true;
            }
        }
    }

    return false;
}

bool SceneDocument::set_entity_position(SceneEntityId id, SceneEntityKind kind, const float position[3])
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                m_ragdolls[entity_index].ragdoll.position[0] = position[0];
                m_ragdolls[entity_index].ragdoll.position[1] = position[1];
                m_ragdolls[entity_index].ragdoll.position[2] = position[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                m_objects[entity_index].object_spec.position[0] = position[0];
                m_objects[entity_index].object_spec.position[1] = position[1];
                m_objects[entity_index].object_spec.position[2] = position[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                m_forces[entity_index].force_spec.position[0] = position[0];
                m_forces[entity_index].force_spec.position[1] = position[1];
                m_forces[entity_index].force_spec.position[2] = position[2];
                return true;
            }
        }
    }

    return false;
}

bool SceneDocument::get_entity_rotation(SceneEntityId id, SceneEntityKind kind, float rotation_degrees[3]) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                rotation_degrees[0] = m_objects[entity_index].object_spec.rotation_degrees[0];
                rotation_degrees[1] = m_objects[entity_index].object_spec.rotation_degrees[1];
                rotation_degrees[2] = m_objects[entity_index].object_spec.rotation_degrees[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                rotation_degrees[0] = m_forces[entity_index].force_spec.rotation_degrees[0];
                rotation_degrees[1] = m_forces[entity_index].force_spec.rotation_degrees[1];
                rotation_degrees[2] = m_forces[entity_index].force_spec.rotation_degrees[2];
                return true;
            }
        }
    }

    return false;
}

bool SceneDocument::set_entity_rotation(SceneEntityId id, SceneEntityKind kind, const float rotation_degrees[3])
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                m_objects[entity_index].object_spec.rotation_degrees[0] = rotation_degrees[0];
                m_objects[entity_index].object_spec.rotation_degrees[1] = rotation_degrees[1];
                m_objects[entity_index].object_spec.rotation_degrees[2] = rotation_degrees[2];
                return true;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                m_forces[entity_index].force_spec.rotation_degrees[0] = rotation_degrees[0];
                m_forces[entity_index].force_spec.rotation_degrees[1] = rotation_degrees[1];
                m_forces[entity_index].force_spec.rotation_degrees[2] = rotation_degrees[2];
                return true;
            }
        }
    }

    return false;
}

bool SceneDocument::get_entity_scale(SceneEntityId id, SceneEntityKind kind, float scale[3]) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindForce)
    {
        // A force has no geometric scale; we drive its cylinder radius instead.
        // Legacy single-ray forces (radius <= 0) start from a small cylinder so
        // the scale gesture has something meaningful to grow.
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                float radius = m_forces[entity_index].force_spec.radius;
                if (radius <= 0.0f)
                {
                    radius = 0.5f;
                }
                scale[0] = radius;
                scale[1] = radius;
                scale[2] = radius;
                return true;
            }
        }

        return false;
    }

    if (kind != SceneEntityKindPhysicsObject)
    {
        return false;
    }

    for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
    {
        if (m_objects[entity_index].record.id == id)
        {
            scale[0] = m_objects[entity_index].object_spec.scale[0];
            scale[1] = m_objects[entity_index].object_spec.scale[1];
            scale[2] = m_objects[entity_index].object_spec.scale[2];
            return true;
        }
    }

    return false;
}

bool SceneDocument::set_entity_scale(SceneEntityId id, SceneEntityKind kind, const float scale[3])
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindForce)
    {
        const float min_radius = 0.05f;
        float radius = scale[0];
        if (radius < min_radius)
        {
            radius = min_radius;
        }

        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                m_forces[entity_index].force_spec.radius = radius;
                return true;
            }
        }

        return false;
    }

    if (kind != SceneEntityKindPhysicsObject)
    {
        return false;
    }

    for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
    {
        if (m_objects[entity_index].record.id == id)
        {
            m_objects[entity_index].object_spec.scale[0] = scale[0];
            m_objects[entity_index].object_spec.scale[1] = scale[1];
            m_objects[entity_index].object_spec.scale[2] = scale[2];
            return true;
        }
    }

    return false;
}

bool SceneDocument::is_entity_movable(SceneEntityId id, SceneEntityKind kind) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindRagdoll)
    {
        for (entity_index = 0; entity_index < m_ragdolls.size(); ++entity_index)
        {
            if (m_ragdolls[entity_index].record.id == id)
            {
                return m_ragdolls[entity_index].record.movable;
            }
        }
    }
    else if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                return m_objects[entity_index].record.movable;
            }
        }
    }
    else if (kind == SceneEntityKindForce)
    {
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                return m_forces[entity_index].record.movable;
            }
        }
    }

    return false;
}

bool SceneDocument::is_entity_rotatable(SceneEntityId id, SceneEntityKind kind) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindPhysicsObject)
    {
        for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
        {
            if (m_objects[entity_index].record.id == id)
            {
                return m_objects[entity_index].record.editable;
            }
        }

        return false;
    }

    if (kind != SceneEntityKindForce)
    {
        return false;
    }

    for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
    {
        if (m_forces[entity_index].record.id == id)
        {
            return m_forces[entity_index].record.editable;
        }
    }

    return false;
}

bool SceneDocument::is_entity_scalable(SceneEntityId id, SceneEntityKind kind) const
{
    std::size_t entity_index = 0;

    if (kind == SceneEntityKindForce)
    {
        // Forces are "scalable" only in the sense that the scale gesture drives
        // their cylinder radius. Reuse the editable flag like objects do.
        for (entity_index = 0; entity_index < m_forces.size(); ++entity_index)
        {
            if (m_forces[entity_index].record.id == id)
            {
                return m_forces[entity_index].record.editable;
            }
        }

        return false;
    }

    if (kind != SceneEntityKindPhysicsObject)
    {
        return false;
    }

    for (entity_index = 0; entity_index < m_objects.size(); ++entity_index)
    {
        if (m_objects[entity_index].record.id == id)
        {
            return m_objects[entity_index].record.editable;
        }
    }

    return false;
}