#include "simulation_controller.h"

#include "ragdoll_runtime_manager.h"
#include "simulation_world.h"
#include "transform_session_controller.h"

SimulationController::SimulationController()
    : m_ground_mode(GroundFlat)
    , m_is_playing(false)
    , m_runtime_matches_scene(true)
    , m_ragdoll_runtime_manager(new RagdollRuntimeManager())
    , m_simulation_world(new SimulationWorld())
    , m_transform_session_controller(0)
    , m_timestep(1.0f / 60.0f)
    , m_has_object_preview(false)
    , m_has_force_preview(false)
    , m_default_ground_entity_id(0)
{
    m_object_preview_spec.object_type = ObjectCube;
    m_object_preview_spec.body_type = BodyDynamic;
    m_object_preview_spec.position[0] = 0.0f;
    m_object_preview_spec.position[1] = 6.0f;
    m_object_preview_spec.position[2] = 0.0f;
    m_object_preview_spec.rotation_degrees[0] = 0.0f;
    m_object_preview_spec.rotation_degrees[1] = 0.0f;
    m_object_preview_spec.rotation_degrees[2] = 0.0f;
    m_object_preview_spec.scale[0] = 0.75f;
    m_object_preview_spec.scale[1] = 0.75f;
    m_object_preview_spec.scale[2] = 0.75f;
    m_object_preview_spec.restitution = 0.15f;
    m_object_preview_spec.mass = 10.0f;

    m_force_preview_spec.position[0] = 0.0f;
    m_force_preview_spec.position[1] = 10.0f;
    m_force_preview_spec.position[2] = 8.0f;
    m_force_preview_spec.rotation_degrees[0] = -90.0f;
    m_force_preview_spec.rotation_degrees[1] = 0.0f;
    m_force_preview_spec.rotation_degrees[2] = 0.0f;
    m_force_preview_spec.strength = 180.0f;
    m_force_preview_spec.mode = ForcePush;
    m_force_preview_spec.active = true;
    m_force_preview_spec.radius = 1.0f;

    m_transform_session_controller = new TransformSessionController(*this, m_scene_document);

    seed_default_scene_objects();
    m_simulation_world->initialize_runtime();
    m_simulation_world->set_timestep(m_timestep);
    reset();
}

SimulationController::~SimulationController()
{
    unload_ragdoll();
    if (m_simulation_world)
    {
        m_simulation_world->destroy_world();
        m_simulation_world->shutdown_runtime();
        delete m_simulation_world;
        m_simulation_world = 0;
    }
    delete m_ragdoll_runtime_manager;
    m_ragdoll_runtime_manager = 0;
    delete m_transform_session_controller;
    m_transform_session_controller = 0;
}