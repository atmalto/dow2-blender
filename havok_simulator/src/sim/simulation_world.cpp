#include "simulation_world.h"

#include <cmath>

#include <Common/Base/hkBase.h>
#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Memory/Memory/Pool/hkPoolMemory.h>
#include <Common/Base/Memory/hkThreadMemory.h>
#include <Common/Base/System/Error/hkDefaultError.h>
#include <Common/Base/System/hkBaseSystem.h>
#include <Common/Base/Types/Geometry/hkGeometry.h>

#include <Physics/Collide/Agent/ConvexAgent/BoxBox/hkpBoxBoxAgent.h>
#include <Physics/Collide/Agent/ConvexAgent/SphereBox/hkpSphereBoxAgent.h>
#include <Physics/Collide/Agent/ConvexAgent/SphereSphere/hkpSphereSphereAgent.h>
#include <Physics/Collide/Dispatch/hkpAgentRegisterUtil.h>
#include <Physics/Collide/Query/CastUtil/hkpWorldRayCastInput.h>
#include <Physics/Collide/Query/CastUtil/hkpWorldRayCastOutput.h>
#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/Capsule/hkpCapsuleShape.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Collide/Shape/hkpShapeType.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/World/hkpWorld.h>
#include <Physics/Dynamics/World/hkpWorldObject.h>
#include <Physics/Internal/PreProcess/ConvexHull/hkpGeometryUtility.h>
#include <Physics/Utilities/Dynamics/Inertia/hkpInertiaTensorComputer.h>

#include "ragdoll_runtime.h"
#include "simulation_settings.h"

namespace
{
    const float kPi = 3.14159265f;

    hkPoolMemory* g_memory_manager = 0;
    hkThreadMemory* g_thread_memory = 0;
    char* g_stack_buffer = 0;

    float degrees_to_radians(float value)
    {
        return value * (kPi / 180.0f);
    }

    float max_abs_component(float a, float b)
    {
        const float abs_a = std::fabs(a);
        const float abs_b = std::fabs(b);
        return abs_a > abs_b ? abs_a : abs_b;
    }

    void set_color(BodyRenderState& state, float red, float green, float blue)
    {
        state.color[0] = red;
        state.color[1] = green;
        state.color[2] = blue;
    }

    void set_default_render_fields(BodyRenderState& state, bool is_dynamic, bool is_solid, bool is_preview)
    {
        state.is_dynamic = is_dynamic;
        state.is_solid = is_solid;
        state.is_preview = is_preview;
        state.entity_id = 0;
        state.entity_kind = SceneEntityKindNone;
        state.is_selected = false;
        state.position[0] = 0.0f;
        state.position[1] = 0.0f;
        state.position[2] = 0.0f;
        state.rotation[0] = 0.0f;
        state.rotation[1] = 0.0f;
        state.rotation[2] = 0.0f;
        state.rotation[3] = 1.0f;
        state.half_extents[0] = 0.0f;
        state.half_extents[1] = 0.0f;
        state.half_extents[2] = 0.0f;
        state.capsule_vertices[0] = 0.0f;
        state.capsule_vertices[1] = 0.0f;
        state.capsule_vertices[2] = 0.0f;
        state.capsule_vertices[3] = 0.0f;
        state.capsule_vertices[4] = 0.0f;
        state.capsule_vertices[5] = 0.0f;
        state.radius = 0.0f;
        state.mesh_vertices.clear();
    }

    bool build_convex_hull_mesh(const std::vector<ConvexHullVertex>& vertices, BodyRenderState* state)
    {
        std::vector<float> packed_vertices;
        hkStridedVertices strided_vertices;
        hkGeometry geometry;
        hkArray<hkVector4> plane_equations;
        std::size_t vertex_index = 0;
        float min_x = 0.0f;
        float max_x = 0.0f;
        float min_y = 0.0f;
        float max_y = 0.0f;
        float min_z = 0.0f;
        float max_z = 0.0f;

        if (!state || vertices.size() < 4)
        {
            return false;
        }

        packed_vertices.resize(vertices.size() * 3);
        min_x = max_x = vertices[0].x;
        min_y = max_y = vertices[0].y;
        min_z = max_z = vertices[0].z;

        for (vertex_index = 0; vertex_index < vertices.size(); ++vertex_index)
        {
            const ConvexHullVertex& vertex = vertices[vertex_index];
            packed_vertices[vertex_index * 3 + 0] = vertex.x;
            packed_vertices[vertex_index * 3 + 1] = vertex.y;
            packed_vertices[vertex_index * 3 + 2] = vertex.z;

            if (vertex.x < min_x)
            {
                min_x = vertex.x;
            }
            if (vertex.x > max_x)
            {
                max_x = vertex.x;
            }
            if (vertex.y < min_y)
            {
                min_y = vertex.y;
            }
            if (vertex.y > max_y)
            {
                max_y = vertex.y;
            }
            if (vertex.z < min_z)
            {
                min_z = vertex.z;
            }
            if (vertex.z > max_z)
            {
                max_z = vertex.z;
            }
        }

        strided_vertices.m_vertices = &packed_vertices[0];
        strided_vertices.m_numVertices = static_cast<int>(vertices.size());
        strided_vertices.m_striding = sizeof(float) * 3;
        hkpGeometryUtility::createConvexGeometry(strided_vertices, geometry, plane_equations);

        state->mesh_vertices.clear();
        for (int triangle_index = 0; triangle_index < geometry.m_triangles.getSize(); ++triangle_index)
        {
            const hkGeometry::Triangle& triangle = geometry.m_triangles[triangle_index];
            const int indices[3] = { triangle.m_a, triangle.m_b, triangle.m_c };

            for (int corner_index = 0; corner_index < 3; ++corner_index)
            {
                const hkVector4& point = geometry.m_vertices[indices[corner_index]];
                state->mesh_vertices.push_back(point(0));
                state->mesh_vertices.push_back(point(1));
                state->mesh_vertices.push_back(point(2));
            }
        }

        state->half_extents[0] = max_abs_component(min_x, max_x);
        state->half_extents[1] = max_abs_component(min_y, max_y);
        state->half_extents[2] = max_abs_component(min_z, max_z);
        if (state->half_extents[0] <= 0.001f)
        {
            state->half_extents[0] = 0.001f;
        }
        if (state->half_extents[1] <= 0.001f)
        {
            state->half_extents[1] = 0.001f;
        }
        if (state->half_extents[2] <= 0.001f)
        {
            state->half_extents[2] = 0.001f;
        }

        return !state->mesh_vertices.empty();
    }

    hkQuaternion make_quaternion_from_euler_degrees(float x_degrees, float y_degrees, float z_degrees)
    {
        const float half_x = degrees_to_radians(x_degrees) * 0.5f;
        const float half_y = degrees_to_radians(y_degrees) * 0.5f;
        const float half_z = degrees_to_radians(z_degrees) * 0.5f;
        const float cx = std::cos(half_x);
        const float sx = std::sin(half_x);
        const float cy = std::cos(half_y);
        const float sy = std::sin(half_y);
        const float cz = std::cos(half_z);
        const float sz = std::sin(half_z);
        hkQuaternion quaternion;

        quaternion.set(
            sx * cy * cz - cx * sy * sz,
            cx * sy * cz + sx * cy * sz,
            cx * cy * sz - sx * sy * cz,
            cx * cy * cz + sx * sy * sz);
        return quaternion;
    }

    void copy_quaternion(const hkQuaternion& quaternion, float output[4])
    {
        output[0] = quaternion(0);
        output[1] = quaternion(1);
        output[2] = quaternion(2);
        output[3] = quaternion(3);
    }

    void rotate_vector_by_quaternion(const hkQuaternion& quaternion, const float input[3], float output[3])
    {
        const float x = quaternion(0);
        const float y = quaternion(1);
        const float z = quaternion(2);
        const float w = quaternion(3);
        const float xx = x * x;
        const float yy = y * y;
        const float zz = z * z;
        const float xy = x * y;
        const float xz = x * z;
        const float yz = y * z;
        const float wx = w * x;
        const float wy = w * y;
        const float wz = w * z;

        output[0] = (1.0f - 2.0f * (yy + zz)) * input[0] + (2.0f * (xy - wz)) * input[1] + (2.0f * (xz + wy)) * input[2];
        output[1] = (2.0f * (xy + wz)) * input[0] + (1.0f - 2.0f * (xx + zz)) * input[1] + (2.0f * (yz - wx)) * input[2];
        output[2] = (2.0f * (xz - wy)) * input[0] + (2.0f * (yz + wx)) * input[1] + (1.0f - 2.0f * (xx + yy)) * input[2];
    }

    float dot_product(const float left[3], const float right[3])
    {
        return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
    }

    float clamp_float(float value, float minimum, float maximum)
    {
        if (value < minimum)
        {
            return minimum;
        }
        if (value > maximum)
        {
            return maximum;
        }
        return value;
    }

    bool distance_squared_between_ray_and_segment(
        const float ray_origin[3],
        const float ray_direction[3],
        const float segment_start[3],
        const float segment_end[3],
        float* ray_distance,
        float* distance_squared)
    {
        const float epsilon = 1.0e-5f;
        const float u[3] = { ray_direction[0], ray_direction[1], ray_direction[2] };
        const float v[3] = {
            segment_end[0] - segment_start[0],
            segment_end[1] - segment_start[1],
            segment_end[2] - segment_start[2]
        };
        const float w[3] = {
            ray_origin[0] - segment_start[0],
            ray_origin[1] - segment_start[1],
            ray_origin[2] - segment_start[2]
        };
        const float a = dot_product(u, u);
        const float b = dot_product(u, v);
        const float c = dot_product(v, v);
        const float d = dot_product(u, w);
        const float e = dot_product(v, w);
        const float determinant = a * c - b * b;
        float ray_numerator = 0.0f;
        float ray_denominator = determinant;
        float segment_numerator = 0.0f;
        float segment_denominator = determinant;
        float ray_parameter = 0.0f;
        float segment_parameter = 0.0f;
        float closest_delta[3];

        if (c <= epsilon)
        {
            ray_parameter = -d / a;
            if (ray_parameter < 0.0f)
            {
                ray_parameter = 0.0f;
            }

            closest_delta[0] = w[0] + ray_parameter * u[0];
            closest_delta[1] = w[1] + ray_parameter * u[1];
            closest_delta[2] = w[2] + ray_parameter * u[2];

            if (ray_distance)
            {
                *ray_distance = ray_parameter;
            }
            if (distance_squared)
            {
                *distance_squared = dot_product(closest_delta, closest_delta);
            }
            return true;
        }

        if (determinant <= epsilon)
        {
            ray_numerator = 0.0f;
            ray_denominator = 1.0f;
            segment_numerator = e;
            segment_denominator = c;
        }
        else
        {
            ray_numerator = b * e - c * d;
            segment_numerator = a * e - b * d;

            if (ray_numerator < 0.0f)
            {
                ray_numerator = 0.0f;
                ray_denominator = 1.0f;
                segment_numerator = e;
                segment_denominator = c;
            }
        }

        segment_parameter = segment_denominator > epsilon ? segment_numerator / segment_denominator : 0.0f;
        segment_parameter = clamp_float(segment_parameter, 0.0f, 1.0f);

        if (segment_parameter <= epsilon)
        {
            ray_parameter = -d / a;
        }
        else if (segment_parameter >= 1.0f - epsilon)
        {
            ray_parameter = (b - d) / a;
        }
        else
        {
            ray_parameter = ray_denominator > epsilon ? ray_numerator / ray_denominator : 0.0f;
        }

        if (ray_parameter < 0.0f)
        {
            ray_parameter = 0.0f;
            segment_parameter = clamp_float(e / c, 0.0f, 1.0f);
        }

        closest_delta[0] = w[0] + ray_parameter * u[0] - segment_parameter * v[0];
        closest_delta[1] = w[1] + ray_parameter * u[1] - segment_parameter * v[1];
        closest_delta[2] = w[2] + ray_parameter * u[2] - segment_parameter * v[2];

        if (ray_distance)
        {
            *ray_distance = ray_parameter;
        }
        if (distance_squared)
        {
            *distance_squared = dot_product(closest_delta, closest_delta);
        }
        return true;
    }

    void HK_CALL error_report(const char* message, void*)
    {
        (void)message;
    }

    BodyRenderState make_box_state(bool is_dynamic, bool is_solid, bool is_preview, float half_x, float half_y, float half_z)
    {
        BodyRenderState state;
        state.shape_type = BodyRenderState::ShapeBox;
        set_default_render_fields(state, is_dynamic, is_solid, is_preview);
        state.half_extents[0] = half_x;
        state.half_extents[1] = half_y;
        state.half_extents[2] = half_z;
        set_color(state, is_preview ? 0.96f : (is_dynamic ? 0.95f : 0.55f), is_preview ? 0.96f : (is_dynamic ? 0.74f : 0.62f), is_preview ? 0.96f : (is_dynamic ? 0.32f : 0.71f));
        return state;
    }

    BodyRenderState make_sphere_state(bool is_dynamic, bool is_solid, bool is_preview, float radius)
    {
        BodyRenderState state;
        state.shape_type = BodyRenderState::ShapeSphere;
        set_default_render_fields(state, is_dynamic, is_solid, is_preview);
        state.half_extents[0] = radius;
        state.half_extents[1] = radius;
        state.half_extents[2] = radius;
        state.radius = radius;
        set_color(state, is_preview ? 0.96f : 0.48f, is_preview ? 0.96f : 0.83f, is_preview ? 0.96f : 0.92f);
        return state;
    }

    BodyRenderState make_capsule_state(bool is_dynamic, const hkVector4& vertex_a, const hkVector4& vertex_b, float radius)
    {
        BodyRenderState state = make_sphere_state(is_dynamic, false, false, radius);
        state.shape_type = BodyRenderState::ShapeCapsule;
        state.capsule_vertices[0] = vertex_a(0);
        state.capsule_vertices[1] = vertex_a(1);
        state.capsule_vertices[2] = vertex_a(2);
        state.capsule_vertices[3] = vertex_b(0);
        state.capsule_vertices[4] = vertex_b(1);
        state.capsule_vertices[5] = vertex_b(2);
        set_color(state, 0.89f, 0.53f, 0.25f);
        return state;
    }

    BodyRenderState make_wedge_state(bool is_dynamic, bool is_solid, bool is_preview, float half_x, float half_y, float half_z)
    {
        BodyRenderState state = make_box_state(is_dynamic, is_solid, is_preview, half_x, half_y, half_z);
        state.shape_type = BodyRenderState::ShapeWedge;
        set_color(state, is_preview ? 0.96f : 0.73f, is_preview ? 0.96f : 0.56f, is_preview ? 0.96f : 0.30f);
        return state;
    }

    BodyRenderState make_convex_hull_state(bool is_dynamic, bool is_solid, bool is_preview, const std::vector<ConvexHullVertex>& vertices)
    {
        BodyRenderState state;
        state.shape_type = BodyRenderState::ShapeConvexHull;
        set_default_render_fields(state, is_dynamic, is_solid, is_preview);
        build_convex_hull_mesh(vertices, &state);
        set_color(state, is_preview ? 0.96f : 0.61f, is_preview ? 0.96f : 0.78f, is_preview ? 0.96f : 0.36f);
        return state;
    }

    const PhysicsObjectSceneEntity* find_object_entity(const SceneDocument& scene_document, SceneEntityId entity_id)
    {
        const std::vector<PhysicsObjectSceneEntity>& objects = scene_document.objects();

        for (std::size_t object_index = 0; object_index < objects.size(); ++object_index)
        {
            if (objects[object_index].record.id == entity_id)
            {
                return &objects[object_index];
            }
        }

        return 0;
    }

    const ForceSceneEntity* find_force_entity(const SceneDocument& scene_document, SceneEntityId entity_id)
    {
        const std::vector<ForceSceneEntity>& forces = scene_document.forces();

        for (std::size_t force_index = 0; force_index < forces.size(); ++force_index)
        {
            if (forces[force_index].record.id == entity_id)
            {
                return &forces[force_index];
            }
        }

        return 0;
    }

    const RagdollSceneEntity* find_ragdoll_entity(const SceneDocument& scene_document, SceneEntityId entity_id)
    {
        const std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();

        for (std::size_t ragdoll_index = 0; ragdoll_index < ragdolls.size(); ++ragdoll_index)
        {
            if (ragdolls[ragdoll_index].record.id == entity_id)
            {
                return &ragdolls[ragdoll_index];
            }
        }

        return 0;
    }

    bool can_uniform_scale_object(const PhysicsObjectSceneEntity& object)
    {
        if (!object.record.editable)
        {
            return false;
        }

        return object.object_spec.object_type == 0 ||
            object.object_spec.object_type == 1 ||
            object.object_spec.object_type == 2;
    }

    void fill_render_transform(const hkpRigidBody* body, BodyRenderState& state)
    {
        const hkQuaternion& rotation = body->getRotation();
        const hkVector4& position = body->getPosition();

        state.position[0] = position(0);
        state.position[1] = position(1);
        state.position[2] = position(2);
        state.rotation[0] = rotation(0);
        state.rotation[1] = rotation(1);
        state.rotation[2] = rotation(2);
        state.rotation[3] = rotation(3);
    }
}

int SimulationWorld::s_runtime_refcount = 0;

SimulationWorld::SimulationWorld()
    : m_timestep(1.0f / 60.0f)
    , m_world(0)
{
}

SimulationWorld::~SimulationWorld()
{
}

void SimulationWorld::initialize_runtime()
{
    if (s_runtime_refcount == 0)
    {
        g_memory_manager = new hkPoolMemory();
        g_thread_memory = new hkThreadMemory(g_memory_manager, 16);
        hkBaseSystem::init(g_memory_manager, g_thread_memory, error_report);
        g_memory_manager->removeReference();

        const int stack_size = 0x100000;
        g_stack_buffer = hkAllocate<char>(stack_size, HK_MEMORY_CLASS_BASE);
        hkThreadMemory::getInstance().setStackArea(g_stack_buffer, stack_size);
    }

    ++s_runtime_refcount;
}

void SimulationWorld::shutdown_runtime()
{
    --s_runtime_refcount;

    if (s_runtime_refcount == 0)
    {
        hkThreadMemory::getInstance().setStackArea(0, 0);
        hkDeallocate<char>(g_stack_buffer);
        g_stack_buffer = 0;

        hkBaseSystem::quit();

        g_thread_memory = 0;
        g_memory_manager = 0;
    }
}

void SimulationWorld::destroy_world()
{
    if (m_world)
    {
        m_world->markForWrite();

        for (std::size_t body_index = 0; body_index < m_owned_bodies.size(); ++body_index)
        {
            m_world->removeEntity(m_owned_bodies[body_index]);
            m_owned_bodies[body_index]->removeReference();
        }

        m_world->unmarkForWrite();
        m_world->removeReference();
        m_world = 0;
    }

    m_owned_bodies.clear();
    m_runtime_bodies.clear();
    m_runtime_body_lookup.clear();
    m_runtime_entities.clear();
    m_render_bodies.clear();
}

void SimulationWorld::create_world(const SceneDocument& scene_document, const std::vector<RagdollRuntime*>& ragdoll_runtimes)
{
    const float gravity_magnitude = SimulationSettings::base_gravity() * SimulationSettings::instance().gravity_scale();
    hkpWorldCinfo world_info;
    world_info.m_gravity.set(0.0f, -gravity_magnitude, 0.0f);
    world_info.m_simulationType = hkpWorldCinfo::SIMULATION_TYPE_CONTINUOUS;

    m_world = new hkpWorld(world_info);

    m_world->markForWrite();
    hkpAgentRegisterUtil::registerAllAgents(m_world->getCollisionDispatcher());

    create_spawned_objects(scene_document);
    create_force_entities(scene_document, scene_document.selected_entity());
    add_loaded_ragdolls(scene_document, ragdoll_runtimes, scene_document.selected_entity());

    m_world->unmarkForWrite();
    sync_render_state();
}

void SimulationWorld::remove_loaded_ragdolls_from_world(const std::vector<RagdollRuntime*>& ragdoll_runtimes)
{
    for (std::size_t runtime_index = 0; runtime_index < ragdoll_runtimes.size(); ++runtime_index)
    {
        if (ragdoll_runtimes[runtime_index])
        {
            ragdoll_runtimes[runtime_index]->remove_from_world();
        }
    }
}

void SimulationWorld::set_timestep(float timestep)
{
    m_timestep = timestep;
}

float SimulationWorld::timestep() const
{
    return m_timestep;
}

hkpWorld* SimulationWorld::world()
{
    return m_world;
}

const hkpWorld* SimulationWorld::world() const
{
    return m_world;
}

const std::vector<BodyRenderState>& SimulationWorld::render_bodies() const
{
    return m_render_bodies;
}

std::vector<BodyRenderState>& SimulationWorld::render_bodies()
{
    return m_render_bodies;
}

void SimulationWorld::sync_render_state()
{
    for (std::size_t body_index = 0; body_index < m_runtime_bodies.size(); ++body_index)
    {
        fill_render_transform(m_runtime_bodies[body_index].body, m_render_bodies[m_runtime_bodies[body_index].render_index]);
    }
}

void SimulationWorld::refresh_selection_highlight(const SceneEntitySelection& selected)
{
    for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
    {
        BodyRenderState& render_state = m_render_bodies[body_index];
        render_state.is_selected =
            selected.id != 0 &&
            render_state.entity_id == selected.id &&
            render_state.entity_kind == selected.kind;
    }
}

bool SimulationWorld::resolve_runtime_entity_for_body(const hkpRigidBody* body, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const
{
    const RuntimeBodyBinding* binding = find_runtime_body_binding(body);
    if (!binding || binding->entity_kind == SceneEntityKindNone)
    {
        return false;
    }

    if (entity_id)
    {
        *entity_id = binding->entity_id;
    }
    if (entity_kind)
    {
        *entity_kind = binding->entity_kind;
    }

    return true;
}

bool SimulationWorld::pick_entity_from_ray(const float ray_origin[3], const float ray_direction[3], SceneEntityId* entity_id, SceneEntityKind* entity_kind) const
{
    hkpWorldRayCastInput input;
    hkpWorldRayCastOutput output;
    hkpRigidBody* body = 0;
    const float ray_length = 500.0f;
    float hit_distance = ray_length;
    SceneEntityId force_entity_id = 0;
    SceneEntityKind force_entity_kind = SceneEntityKindNone;

    if (!m_world)
    {
        return false;
    }

    input.m_from.set(ray_origin[0], ray_origin[1], ray_origin[2]);
    input.m_to.set(
        ray_origin[0] + ray_direction[0] * ray_length,
        ray_origin[1] + ray_direction[1] * ray_length,
        ray_origin[2] + ray_direction[2] * ray_length);

    output.reset();
    m_world->castRay(input, output);

    if (output.hasHit())
    {
        hit_distance = output.m_hitFraction * ray_length;
    }

    if (pick_force_entity_from_ray(ray_origin, ray_direction, hit_distance, &force_entity_id, &force_entity_kind))
    {
        if (entity_id)
        {
            *entity_id = force_entity_id;
        }
        if (entity_kind)
        {
            *entity_kind = force_entity_kind;
        }
        return true;
    }

    if (!output.hasHit() || !output.m_rootCollidable)
    {
        return false;
    }

    body = static_cast<hkpRigidBody*>(hkGetWorldObject(output.m_rootCollidable));
    if (!body)
    {
        return false;
    }

    return resolve_runtime_entity_for_body(body, entity_id, entity_kind);
}

bool SimulationWorld::apply_push_force(const std::vector<RagdollRuntime*>& ragdoll_runtimes, const ForceSpec& spec, std::string* error_message)
{
    hkpRigidBody* rigid_body = 0;
    float hit_point[3] = { 0.0f, 0.0f, 0.0f };
    float direction[3] = { 0.0f, 0.0f, 0.0f };
    RagdollRuntime* owning_ragdoll = 0;
    hkVector4 impulse;
    hkVector4 point;

    if (!find_force_target(ragdoll_runtimes, spec, &rigid_body, hit_point, direction, error_message))
    {
        return false;
    }

    owning_ragdoll = find_ragdoll_runtime_owning_body(ragdoll_runtimes, rigid_body);
    if (owning_ragdoll)
    {
        owning_ragdoll->release();
    }

    impulse.set(direction[0] * spec.strength, direction[1] * spec.strength, direction[2] * spec.strength);
    point.set(hit_point[0], hit_point[1], hit_point[2]);

    m_world->markForWrite();
    rigid_body->applyPointImpulse(impulse, point);
    m_world->unmarkForWrite();

    sync_render_state();
    return true;
}

void SimulationWorld::apply_continuous_force_entities(const SceneDocument& scene_document, const std::vector<RagdollRuntime*>& ragdoll_runtimes)
{
    const std::vector<ForceSceneEntity>& forces = scene_document.forces();

    for (std::size_t force_index = 0; force_index < forces.size(); ++force_index)
    {
        hkpRigidBody* rigid_body = 0;
        float hit_point[3] = { 0.0f, 0.0f, 0.0f };
        float direction[3] = { 0.0f, 0.0f, 0.0f };
        float signed_strength = 0.0f;
        RagdollRuntime* owning_ragdoll = 0;
        hkVector4 force;
        hkVector4 point;

        if (!forces[force_index].force_spec.active)
        {
            continue;
        }

        if (!find_force_target(ragdoll_runtimes, forces[force_index].force_spec, &rigid_body, hit_point, direction, 0))
        {
            continue;
        }

        signed_strength = forces[force_index].force_spec.mode == 1
            ? -forces[force_index].force_spec.strength
            : forces[force_index].force_spec.strength;

        owning_ragdoll = find_ragdoll_runtime_owning_body(ragdoll_runtimes, rigid_body);
        if (owning_ragdoll)
        {
            owning_ragdoll->release();
        }

        force.set(direction[0] * signed_strength, direction[1] * signed_strength, direction[2] * signed_strength);
        point.set(hit_point[0], hit_point[1], hit_point[2]);

        m_world->markForWrite();
        rigid_body->applyForce(m_timestep, force, point);
        m_world->unmarkForWrite();
    }
}

bool SimulationWorld::apply_entity_runtime_position(
    const SceneDocument& scene_document,
    const std::vector<RagdollRuntime*>& ragdoll_runtimes,
    SceneEntityId id,
    SceneEntityKind kind,
    const float position[3])
{
    if (kind == SceneEntityKindRagdoll)
    {
        for (std::size_t runtime_index = 0; runtime_index < ragdoll_runtimes.size(); ++runtime_index)
        {
            if (ragdoll_runtimes[runtime_index] && ragdoll_runtimes[runtime_index]->entity_id() == id)
            {
                ragdoll_runtimes[runtime_index]->set_start_position(position);
                sync_render_state();
                return true;
            }
        }

        return false;
    }

    if (kind == SceneEntityKindPhysicsObject)
    {
        const RuntimeEntityBinding* runtime_entity = find_runtime_entity_binding(id, kind);
        const PhysicsObjectSceneEntity* object = find_object_entity(scene_document, id);
        hkVector4 world_position;
        hkVector4 zero_velocity;

        if (object && object->object_spec.body_type == 1)
        {
            for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
            {
                BodyRenderState& render_state = m_render_bodies[body_index];
                if (render_state.entity_id == id && render_state.entity_kind == SceneEntityKindPhysicsObject)
                {
                    render_state.position[0] = position[0];
                    render_state.position[1] = position[1];
                    render_state.position[2] = position[2];
                    return true;
                }
            }

            return false;
        }

        if (!runtime_entity || runtime_entity->runtime_body_count <= 0)
        {
            return false;
        }

        RuntimeBodyBinding& runtime_body = m_runtime_bodies[runtime_entity->first_runtime_body_index];
        if (!runtime_body.body || !m_world)
        {
            return false;
        }

        world_position.set(position[0], position[1], position[2]);
        zero_velocity.set(0.0f, 0.0f, 0.0f);

        m_world->markForWrite();
        runtime_body.body->setPosition(world_position);
        runtime_body.body->setLinearVelocity(zero_velocity);
        runtime_body.body->setAngularVelocity(zero_velocity);
        runtime_body.body->activate();
        m_world->unmarkForWrite();

        sync_render_state();
        return true;
    }

    if (kind == SceneEntityKindForce)
    {
        for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
        {
            BodyRenderState& render_state = m_render_bodies[body_index];
            if (render_state.entity_id == id && render_state.entity_kind == SceneEntityKindForce)
            {
                render_state.position[0] = position[0];
                render_state.position[1] = position[1];
                render_state.position[2] = position[2];
                return true;
            }
        }
    }

    return false;
}

bool SimulationWorld::apply_entity_runtime_rotation(
    const SceneDocument& scene_document,
    SceneEntityId id,
    SceneEntityKind kind,
    const float rotation_degrees[3])
{
    if (kind == SceneEntityKindPhysicsObject)
    {
        const PhysicsObjectSceneEntity* object = find_object_entity(scene_document, id);
        hkQuaternion rotation = make_quaternion_from_euler_degrees(
            rotation_degrees[0],
            rotation_degrees[1],
            rotation_degrees[2]);
        hkVector4 zero_velocity;

        if (!object)
        {
            return false;
        }

        if (object->object_spec.body_type == 1)
        {
            for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
            {
                BodyRenderState& render_state = m_render_bodies[body_index];
                if (render_state.entity_id == id && render_state.entity_kind == SceneEntityKindPhysicsObject)
                {
                    copy_quaternion(rotation, render_state.rotation);
                    return true;
                }
            }

            return false;
        }

        const RuntimeEntityBinding* runtime_entity = find_runtime_entity_binding(id, kind);
        if (!runtime_entity || runtime_entity->runtime_body_count <= 0)
        {
            return false;
        }

        RuntimeBodyBinding& runtime_body = m_runtime_bodies[runtime_entity->first_runtime_body_index];
        if (!runtime_body.body || !m_world)
        {
            return false;
        }

        zero_velocity.set(0.0f, 0.0f, 0.0f);

        m_world->markForWrite();
        runtime_body.body->setRotation(rotation);
        runtime_body.body->setLinearVelocity(zero_velocity);
        runtime_body.body->setAngularVelocity(zero_velocity);
        runtime_body.body->activate();
        m_world->unmarkForWrite();

        sync_render_state();
        return true;
    }

    if (kind == SceneEntityKindForce)
    {
        const ForceSceneEntity* force = find_force_entity(scene_document, id);
        ForceSpec preview_spec;

        if (!force)
        {
            return false;
        }

        preview_spec = force->force_spec;
        preview_spec.rotation_degrees[0] = rotation_degrees[0];
        preview_spec.rotation_degrees[1] = rotation_degrees[1];
        preview_spec.rotation_degrees[2] = rotation_degrees[2];

        for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
        {
            BodyRenderState& render_state = m_render_bodies[body_index];
            if (render_state.entity_id == id && render_state.entity_kind == SceneEntityKindForce)
            {
                apply_force_spec_to_render_state(preview_spec, &render_state);
                return true;
            }
        }
    }

    return false;
}

bool SimulationWorld::apply_entity_runtime_scale(
    const SceneDocument& scene_document,
    SceneEntityId id,
    SceneEntityKind kind,
    const float scale[3])
{
    const PhysicsObjectSceneEntity* object = 0;
    SpawnedObjectSpec preview_spec;
    BodyRenderState preview_state;

    if (kind != SceneEntityKindPhysicsObject)
    {
        return false;
    }

    object = find_object_entity(scene_document, id);
    if (!object || !can_uniform_scale_object(*object))
    {
        return false;
    }

    preview_spec = object->object_spec;
    preview_spec.scale[0] = scale[0];
    preview_spec.scale[1] = scale[1];
    preview_spec.scale[2] = scale[2];

    if (preview_spec.scale[0] <= 0.0f || preview_spec.scale[1] <= 0.0f || preview_spec.scale[2] <= 0.0f)
    {
        return false;
    }

    if (preview_spec.object_type == 1)
    {
        preview_spec.scale[1] = preview_spec.scale[0];
        preview_spec.scale[2] = preview_spec.scale[0];
    }

    if (!build_render_state_from_spec(preview_spec, false, &preview_state))
    {
        return false;
    }

    for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
    {
        BodyRenderState& render_state = m_render_bodies[body_index];
        if (render_state.entity_id == id && render_state.entity_kind == kind)
        {
            const bool was_selected = render_state.is_selected;
            preview_state.entity_id = id;
            preview_state.entity_kind = kind;
            preview_state.is_selected = was_selected;
            render_state = preview_state;
            return true;
        }
    }

    return false;
}

bool SimulationWorld::build_render_state_from_spec(const SpawnedObjectSpec& spec, bool is_preview, BodyRenderState* state) const
{
    if (!state)
    {
        return false;
    }

    const bool is_dynamic = spec.body_type == 0;
    hkQuaternion rotation = make_quaternion_from_euler_degrees(
        spec.rotation_degrees[0],
        spec.rotation_degrees[1],
        spec.rotation_degrees[2]);

    if (spec.object_type == 0)
    {
        *state = make_box_state(is_dynamic, !is_preview, is_preview, spec.scale[0], spec.scale[1], spec.scale[2]);
    }
    else if (spec.object_type == 1)
    {
        *state = make_sphere_state(is_dynamic, !is_preview, is_preview, spec.scale[0]);
    }
    else if (spec.object_type == 3)
    {
        *state = make_convex_hull_state(is_dynamic, !is_preview, is_preview, spec.convex_hull_vertices);
        if (state->mesh_vertices.empty())
        {
            return false;
        }
    }
    else
    {
        *state = make_wedge_state(is_dynamic, !is_preview, is_preview, spec.scale[0], spec.scale[1], spec.scale[2]);
    }

    state->position[0] = spec.position[0];
    state->position[1] = spec.position[1];
    state->position[2] = spec.position[2];
    copy_quaternion(rotation, state->rotation);
    return true;
}

void SimulationWorld::apply_force_spec_to_render_state(const ForceSpec& spec, BodyRenderState* state)
{
    const SceneEntityId entity_id = state ? state->entity_id : 0;
    const SceneEntityKind entity_kind = state ? state->entity_kind : SceneEntityKindNone;
    const bool is_selected = state ? state->is_selected : false;
    const bool is_preview = state ? state->is_preview : false;

    if (!state)
    {
        return;
    }

    *state = build_force_render_state(spec, is_preview);
    state->entity_id = entity_id;
    state->entity_kind = entity_kind;
    state->is_selected = is_selected;
}

BodyRenderState SimulationWorld::build_force_render_state(const ForceSpec& spec, bool is_preview)
{
    BodyRenderState state;
    const hkQuaternion rotation = make_quaternion_from_euler_degrees(
        spec.rotation_degrees[0],
        spec.rotation_degrees[1],
        spec.rotation_degrees[2]);

    state.shape_type = BodyRenderState::ShapeArrow;
    set_default_render_fields(state, false, false, is_preview);
    state.position[0] = spec.position[0];
    state.position[1] = spec.position[1];
    state.position[2] = spec.position[2];
    copy_quaternion(rotation, state.rotation);
    state.half_extents[0] = 4.0f;
    state.half_extents[1] = spec.strength * 0.01f;
    state.half_extents[2] = 120.0f;

    if (spec.mode == 1)
    {
        set_color(state, 0.24f, 0.72f, 0.96f);
    }
    else
    {
        set_color(state, 0.95f, 0.22f, 0.22f);
    }

    return state;
}

void SimulationWorld::create_spawned_objects(const SceneDocument& scene_document)
{
    const std::vector<PhysicsObjectSceneEntity>& objects = scene_document.objects();

    for (std::size_t object_index = 0; object_index < objects.size(); ++object_index)
    {
        hkpRigidBody* rigid_body = 0;
        BodyRenderState state;

        if (!create_body_from_spec(objects[object_index].object_spec, &rigid_body, &state, 0))
        {
            continue;
        }

        add_body(objects[object_index].record.id, SceneEntityKindPhysicsObject, rigid_body, state, scene_document.selected_entity());
    }
}

void SimulationWorld::create_force_entities(const SceneDocument& scene_document, const SceneEntitySelection& selected)
{
    const std::vector<ForceSceneEntity>& forces = scene_document.forces();

    for (std::size_t force_index = 0; force_index < forces.size(); ++force_index)
    {
        BodyRenderState state = build_force_render_state(forces[force_index].force_spec, false);
        state.entity_id = forces[force_index].record.id;
        state.entity_kind = SceneEntityKindForce;
        state.is_selected = selected.id == state.entity_id && selected.kind == state.entity_kind;
        m_render_bodies.push_back(state);
    }
}

void SimulationWorld::add_loaded_ragdolls(
    const SceneDocument& scene_document,
    const std::vector<RagdollRuntime*>& ragdoll_runtimes,
    const SceneEntitySelection& selected)
{
    for (std::size_t runtime_index = 0; runtime_index < ragdoll_runtimes.size(); ++runtime_index)
    {
        RagdollRuntime* runtime_state = ragdoll_runtimes[runtime_index];
        const RagdollSceneEntity* ragdoll = runtime_state ? find_ragdoll_entity(scene_document, runtime_state->entity_id()) : 0;
        RuntimeEntityBinding runtime_entity;

        if (!runtime_state || !runtime_state->instance() || !ragdoll)
        {
            continue;
        }

        if (!runtime_state->add_to_world(m_world))
        {
            continue;
        }

        runtime_state->apply_mass_scale(SimulationSettings::instance().ragdoll_mass_scale());

        runtime_entity.entity_id = ragdoll->record.id;
        runtime_entity.entity_kind = SceneEntityKindRagdoll;
        runtime_entity.first_runtime_body_index = static_cast<int>(m_runtime_bodies.size());
        runtime_entity.runtime_body_count = 0;
        runtime_entity.first_render_index = static_cast<int>(m_render_bodies.size());
        runtime_entity.render_body_count = 0;

        for (int bone_index = 0; bone_index < runtime_state->body_count(); ++bone_index)
        {
            hkpRigidBody* rigid_body = runtime_state->body_at(bone_index);
            BodyRenderState state;
            const hkpShape* shape = rigid_body ? rigid_body->getCollidable()->getShape() : 0;

            if (!rigid_body || !shape)
            {
                continue;
            }

            switch (shape->getType())
            {
            case HK_SHAPE_BOX:
                {
                    const hkpBoxShape* box_shape = static_cast<const hkpBoxShape*>(shape);
                    const hkVector4& half_extents = box_shape->getHalfExtents();
                    state = make_box_state(true, true, false, half_extents(0), half_extents(1), half_extents(2));
                }
                break;
            case HK_SHAPE_SPHERE:
                {
                    const hkpSphereShape* sphere_shape = static_cast<const hkpSphereShape*>(shape);
                    state = make_sphere_state(true, true, false, sphere_shape->getRadius());
                }
                break;
            case HK_SHAPE_CAPSULE:
                {
                    const hkpCapsuleShape* capsule_shape = static_cast<const hkpCapsuleShape*>(shape);
                    state = make_capsule_state(true, capsule_shape->getVertex(0), capsule_shape->getVertex(1), capsule_shape->getRadius());
                }
                break;
            default:
                continue;
            }

            add_render_body(ragdoll->record.id, SceneEntityKindRagdoll, rigid_body, state, selected);
            ++runtime_entity.runtime_body_count;
            ++runtime_entity.render_body_count;
        }

        if (runtime_entity.render_body_count > 0)
        {
            m_runtime_entities.push_back(runtime_entity);
        }
    }
}

void SimulationWorld::add_body(
    SceneEntityId entity_id,
    SceneEntityKind entity_kind,
    hkpRigidBody* body,
    const BodyRenderState& state,
    const SceneEntitySelection& selected)
{
    m_world->addEntity(body);
    m_owned_bodies.push_back(body);
    add_render_body(entity_id, entity_kind, body, state, selected);

    if (entity_kind != SceneEntityKindNone)
    {
        RuntimeEntityBinding runtime_entity;
        runtime_entity.entity_id = entity_id;
        runtime_entity.entity_kind = entity_kind;
        runtime_entity.first_runtime_body_index = static_cast<int>(m_runtime_bodies.size()) - 1;
        runtime_entity.runtime_body_count = 1;
        runtime_entity.first_render_index = static_cast<int>(m_render_bodies.size()) - 1;
        runtime_entity.render_body_count = 1;
        m_runtime_entities.push_back(runtime_entity);
    }
}

void SimulationWorld::add_render_body(
    SceneEntityId entity_id,
    SceneEntityKind entity_kind,
    hkpRigidBody* body,
    const BodyRenderState& state,
    const SceneEntitySelection& selected)
{
    BodyRenderState render_state = state;
    const int render_index = static_cast<int>(m_render_bodies.size());
    RuntimeBodyBinding binding;

    render_state.entity_id = entity_id;
    render_state.entity_kind = entity_kind;
    render_state.is_selected = selected.id == entity_id && selected.kind == entity_kind;
    m_render_bodies.push_back(render_state);

    binding.entity_id = entity_id;
    binding.entity_kind = entity_kind;
    binding.body = body;
    binding.render_index = render_index;
    m_runtime_body_lookup[body] = m_runtime_bodies.size();
    m_runtime_bodies.push_back(binding);
}

bool SimulationWorld::create_body_from_spec(
    const SpawnedObjectSpec& spec,
    hkpRigidBody** body,
    BodyRenderState* state,
    std::string* error_message)
{
    hkpShape* shape = 0;
    const bool is_dynamic = spec.body_type == 0;

    if (!body || !state)
    {
        return false;
    }

    if (spec.object_type == 0)
    {
        hkVector4 half_extents(spec.scale[0], spec.scale[1], spec.scale[2]);
        shape = new hkpBoxShape(half_extents);
    }
    else if (spec.object_type == 1)
    {
        shape = new hkpSphereShape(spec.scale[0]);
    }
    else if (spec.object_type == 3)
    {
        std::vector<float> packed_vertices(spec.convex_hull_vertices.size() * 3);
        hkStridedVertices strided_vertices;
        hkGeometry geometry;
        hkArray<hkVector4> plane_equations;

        for (std::size_t vertex_index = 0; vertex_index < spec.convex_hull_vertices.size(); ++vertex_index)
        {
            const ConvexHullVertex& vertex = spec.convex_hull_vertices[vertex_index];
            packed_vertices[vertex_index * 3 + 0] = vertex.x;
            packed_vertices[vertex_index * 3 + 1] = vertex.y;
            packed_vertices[vertex_index * 3 + 2] = vertex.z;
        }

        strided_vertices.m_vertices = &packed_vertices[0];
        strided_vertices.m_numVertices = static_cast<int>(spec.convex_hull_vertices.size());
        strided_vertices.m_striding = sizeof(float) * 3;
        hkpGeometryUtility::createConvexGeometry(strided_vertices, geometry, plane_equations);
        shape = new hkpConvexVerticesShape(strided_vertices, plane_equations, spec.shape_radius);
    }
    else
    {
        float wedge_vertices[18] = {
            -spec.scale[0], -spec.scale[1], -spec.scale[2],
            -spec.scale[0], -spec.scale[1],  spec.scale[2],
             spec.scale[0], -spec.scale[1], -spec.scale[2],
             spec.scale[0], -spec.scale[1],  spec.scale[2],
            -spec.scale[0],  spec.scale[1], -spec.scale[2],
            -spec.scale[0],  spec.scale[1],  spec.scale[2]
        };
        hkStridedVertices strided_vertices;
        hkGeometry geometry;
        hkArray<hkVector4> plane_equations;

        strided_vertices.m_vertices = wedge_vertices;
        strided_vertices.m_numVertices = 6;
        strided_vertices.m_striding = sizeof(float) * 3;

        hkpGeometryUtility::createConvexGeometry(strided_vertices, geometry, plane_equations);
        shape = new hkpConvexVerticesShape(strided_vertices, plane_equations);
    }

    if (!shape)
    {
        if (error_message)
        {
            *error_message = "Could not create Havok shape for object.";
        }
        return false;
    }

    hkpRigidBodyCinfo body_info;
    body_info.m_shape = shape;
    body_info.m_motionType = is_dynamic ? hkpMotion::MOTION_DYNAMIC : hkpMotion::MOTION_FIXED;
    body_info.m_position.set(spec.position[0], spec.position[1], spec.position[2]);
    body_info.m_rotation = make_quaternion_from_euler_degrees(
        spec.rotation_degrees[0],
        spec.rotation_degrees[1],
        spec.rotation_degrees[2]);
    body_info.m_restitution = spec.restitution;
    body_info.m_friction = 0.7f;
    body_info.m_mass = 0.0f;

    if (is_dynamic)
    {
        body_info.m_mass = spec.mass;
        hkpInertiaTensorComputer::setShapeVolumeMassProperties(shape, spec.mass, body_info);
    }

    *body = new hkpRigidBody(body_info);
    shape->removeReference();

    if (!build_render_state_from_spec(spec, false, state))
    {
        if (error_message)
        {
            *error_message = "Could not build render state for object.";
        }
        (*body)->removeReference();
        *body = 0;
        return false;
    }

    fill_render_transform(*body, *state);
    return true;
}

bool SimulationWorld::find_force_target(
    const std::vector<RagdollRuntime*>& ragdoll_runtimes,
    const ForceSpec& spec,
    hkpRigidBody** body,
    float hit_point[3],
    float direction[3],
    std::string* error_message) const
{
    (void)ragdoll_runtimes;

    if (!m_world || !body)
    {
        return false;
    }

    const hkQuaternion rotation = make_quaternion_from_euler_degrees(
        spec.rotation_degrees[0],
        spec.rotation_degrees[1],
        spec.rotation_degrees[2]);
    const float local_forward[3] = { 0.0f, 0.0f, -1.0f };
    hkpWorldRayCastInput input;
    hkpWorldRayCastOutput output;

    rotate_vector_by_quaternion(rotation, local_forward, direction);

    input.m_from.set(spec.position[0], spec.position[1], spec.position[2]);
    input.m_to.set(
        spec.position[0] + direction[0] * 200.0f,
        spec.position[1] + direction[1] * 200.0f,
        spec.position[2] + direction[2] * 200.0f);

    output.reset();
    m_world->castRay(input, output);

    if (!output.hasHit() || !output.m_rootCollidable)
    {
        if (error_message)
        {
            *error_message = "Force ray did not hit a dynamic rigid body.";
        }
        return false;
    }

    *body = static_cast<hkpRigidBody*>(hkGetWorldObject(output.m_rootCollidable));
    if (!*body)
    {
        if (error_message)
        {
            *error_message = "Force ray did not resolve to a rigid body.";
        }
        return false;
    }

    if ((*body)->getMotionType() == hkpMotion::MOTION_FIXED)
    {
        if (error_message)
        {
            *error_message = "Force ray hit a static body. Aim at a dynamic object or ragdoll body.";
        }
        return false;
    }

    hit_point[0] = spec.position[0] + (input.m_to(0) - input.m_from(0)) * output.m_hitFraction;
    hit_point[1] = spec.position[1] + (input.m_to(1) - input.m_from(1)) * output.m_hitFraction;
    hit_point[2] = spec.position[2] + (input.m_to(2) - input.m_from(2)) * output.m_hitFraction;
    return true;
}

RagdollRuntime* SimulationWorld::find_ragdoll_runtime_owning_body(
    const std::vector<RagdollRuntime*>& ragdoll_runtimes,
    const hkpRigidBody* body) const
{
    if (!body)
    {
        return 0;
    }

    for (std::size_t runtime_index = 0; runtime_index < ragdoll_runtimes.size(); ++runtime_index)
    {
        RagdollRuntime* runtime_state = ragdoll_runtimes[runtime_index];

        if (!runtime_state)
        {
            continue;
        }

        for (int bone_index = 0; bone_index < runtime_state->body_count(); ++bone_index)
        {
            if (runtime_state->body_at(bone_index) == body)
            {
                return runtime_state;
            }
        }
    }

    return 0;
}

const SimulationWorld::RuntimeBodyBinding* SimulationWorld::find_runtime_body_binding(const hkpRigidBody* body) const
{
    std::map<const hkpRigidBody*, std::size_t>::const_iterator lookup;

    if (!body)
    {
        return 0;
    }

    lookup = m_runtime_body_lookup.find(body);
    if (lookup == m_runtime_body_lookup.end())
    {
        return 0;
    }

    return &m_runtime_bodies[lookup->second];
}

const SimulationWorld::RuntimeEntityBinding* SimulationWorld::find_runtime_entity_binding(SceneEntityId entity_id, SceneEntityKind entity_kind) const
{
    for (std::size_t entity_index = 0; entity_index < m_runtime_entities.size(); ++entity_index)
    {
        if (m_runtime_entities[entity_index].entity_id == entity_id &&
            m_runtime_entities[entity_index].entity_kind == entity_kind)
        {
            return &m_runtime_entities[entity_index];
        }
    }

    return 0;
}

bool SimulationWorld::pick_force_entity_from_ray(
    const float ray_origin[3],
    const float ray_direction[3],
    float max_distance,
    SceneEntityId* entity_id,
    SceneEntityKind* entity_kind) const
{
    SceneEntityId best_id = 0;
    float best_distance = max_distance;

    for (std::size_t body_index = 0; body_index < m_render_bodies.size(); ++body_index)
    {
        const BodyRenderState& render_state = m_render_bodies[body_index];
        hkQuaternion rotation;
        const float local_direction[3] = { 0.0f, 0.0f, -1.0f };
        float world_direction[3];
        float segment_end[3];
        float ray_distance = 0.0f;
        float distance_squared = 0.0f;
        float pick_radius = render_state.half_extents[1] * 0.18f;
        const float pick_length = render_state.half_extents[0];

        if (render_state.entity_kind != SceneEntityKindForce ||
            render_state.entity_id == 0 ||
            render_state.shape_type != BodyRenderState::ShapeArrow)
        {
            continue;
        }

        if (pick_radius < 0.45f)
        {
            pick_radius = 0.45f;
        }
        else if (pick_radius > 0.9f)
        {
            pick_radius = 0.9f;
        }

        rotation.set(
            render_state.rotation[0],
            render_state.rotation[1],
            render_state.rotation[2],
            render_state.rotation[3]);
        rotate_vector_by_quaternion(rotation, local_direction, world_direction);

        segment_end[0] = render_state.position[0] + world_direction[0] * pick_length;
        segment_end[1] = render_state.position[1] + world_direction[1] * pick_length;
        segment_end[2] = render_state.position[2] + world_direction[2] * pick_length;

        distance_squared_between_ray_and_segment(
            ray_origin,
            ray_direction,
            render_state.position,
            segment_end,
            &ray_distance,
            &distance_squared);

        if (ray_distance <= best_distance && distance_squared <= pick_radius * pick_radius)
        {
            best_distance = ray_distance;
            best_id = render_state.entity_id;
        }
    }

    if (best_id == 0)
    {
        return false;
    }

    if (entity_id)
    {
        *entity_id = best_id;
    }
    if (entity_kind)
    {
        *entity_kind = SceneEntityKindForce;
    }

    return true;
}