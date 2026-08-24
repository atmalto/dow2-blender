#include "simulation_controller.h"

#include <vector>

#include <Physics/Dynamics/World/hkpWorld.h>

#include "ragdoll_runtime_manager.h"
#include "simulation_world.h"

void SimulationController::set_ground_mode(GroundMode mode)
{
    if (m_ground_mode == mode)
    {
        return;
    }

    m_ground_mode = mode;
    update_ground_scene_object();
    reset();
}

SimulationController::GroundMode SimulationController::ground_mode() const
{
    return m_ground_mode;
}

void SimulationController::reset()
{
    m_scene_document.cancel_axis_move();
    m_scene_document.cancel_axis_rotate();
    m_scene_document.cancel_uniform_scale();
    if (m_simulation_world && m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->detach_from_world(m_simulation_world);
        m_simulation_world->destroy_world();
        m_simulation_world->create_world(m_scene_document, m_ragdoll_runtime_manager->runtimes());
    }
    m_runtime_matches_scene = true;
    rebuild_preview_bodies();
}

void SimulationController::step()
{
    if (!m_simulation_world || !m_simulation_world->world())
    {
        return;
    }

    step_ragdoll_runtimes();
    m_simulation_world->apply_continuous_force_entities(
        m_scene_document,
        m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->runtimes() : std::vector<RagdollRuntime*>());
    m_simulation_world->world()->stepDeltaTime(m_simulation_world->timestep());
    m_runtime_matches_scene = false;
    m_simulation_world->sync_render_state();
}

void SimulationController::step_ragdoll_runtimes()
{
    hkpWorld* world = m_simulation_world ? m_simulation_world->world() : 0;

    if (!world || !m_ragdoll_runtime_manager)
    {
        return;
    }

    world->markForWrite();
    m_ragdoll_runtime_manager->step_runtimes(m_simulation_world->timestep());
    world->unmarkForWrite();
}

void SimulationController::set_playing(bool playing)
{
    m_is_playing = playing;
}

bool SimulationController::is_playing() const
{
    return m_is_playing;
}

float SimulationController::timestep() const
{
    return m_simulation_world ? m_simulation_world->timestep() : m_timestep;
}

bool SimulationController::can_author_scene() const
{
    return !m_is_playing &&
        m_runtime_matches_scene &&
        !m_scene_document.axis_move_session().active &&
        !m_scene_document.axis_rotate_session().active &&
        !m_scene_document.uniform_scale_session().active;
}

const std::vector<BodyRenderState>& SimulationController::render_bodies() const
{
    static const std::vector<BodyRenderState> kEmptyRenderBodies;
    return m_simulation_world ? m_simulation_world->render_bodies() : kEmptyRenderBodies;
}

const std::vector<BodyRenderState>& SimulationController::preview_bodies() const
{
    return m_preview_bodies;
}

const SceneDocument& SimulationController::scene_document() const
{
    return m_scene_document;
}

bool SimulationController::resolve_runtime_entity_for_body(const hkpRigidBody* body, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const
{
    return m_simulation_world
        ? m_simulation_world->resolve_runtime_entity_for_body(body, entity_id, entity_kind)
        : false;
}