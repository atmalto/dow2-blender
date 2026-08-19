#include "simulation_controller.h"

#include <algorithm>
#include <cmath>
#include <sstream>

#include <Common/Base/hkBase.h>
#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Memory/Memory/Pool/hkPoolMemory.h>
#include <Common/Base/Memory/hkThreadMemory.h>
#include <Common/Base/Math/QsTransform/hkQsTransform.h>
#include <Common/Base/System/Error/hkDefaultError.h>
#include <Common/Base/System/hkBaseSystem.h>

#include <Physics/Collide/Agent/ConvexAgent/BoxBox/hkpBoxBoxAgent.h>
#include <Physics/Collide/Agent/ConvexAgent/SphereBox/hkpSphereBoxAgent.h>
#include <Physics/Collide/Agent/ConvexAgent/SphereSphere/hkpSphereSphereAgent.h>
#include <Physics/Collide/Dispatch/hkpAgentRegisterUtil.h>
#include <Physics/Collide/Shape/Convex/Capsule/hkpCapsuleShape.h>
#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Collide/Query/CastUtil/hkpWorldRayCastInput.h>
#include <Physics/Collide/Query/CastUtil/hkpWorldRayCastOutput.h>
#include <Physics/Collide/Shape/hkpShapeType.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/World/hkpWorld.h>
#include <Physics/Dynamics/World/hkpWorldObject.h>
#include <Physics/Utilities/Dynamics/Inertia/hkpInertiaTensorComputer.h>
#include <Physics/Internal/PreProcess/ConvexHull/hkpGeometryUtility.h>

#include <Common/Base/Types/Geometry/hkGeometry.h>

#include "physics_import.h"
#include "ragdoll_preview_data.h"
#include "ragdoll_runtime.h"
#include "ragdoll_runtime_manager.h"
#include "scene_persistence.h"
#include "scene_presets.h"
#include "simulation_settings.h"
#include "transform_session_controller.h"
#include "simulation_world.h"
#include "viewport_widget.h"

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
        int triangle_index = 0;

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
        for (triangle_index = 0; triangle_index < geometry.m_triangles.getSize(); ++triangle_index)
        {
            const hkGeometry::Triangle& triangle = geometry.m_triangles[triangle_index];
            const int indices[3] = { triangle.m_a, triangle.m_b, triangle.m_c };
            int corner_index = 0;
            for (corner_index = 0; corner_index < 3; ++corner_index)
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

    std::string make_numbered_name(const char* prefix, SceneEntityId id)
    {
        std::ostringstream stream;
        stream << prefix << " " << id;
        return stream.str();
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
        const float u[3] = {
            ray_direction[0],
            ray_direction[1],
            ray_direction[2]
        };
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

    BodyRenderState make_arrow_state(const SimulationController::ForceSpec& spec, bool is_preview)
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
        if (spec.mode == SimulationController::ForcePull)
        {
            set_color(state, 0.24f, 0.72f, 0.96f);
        }
        else
        {
            set_color(state, 0.95f, 0.22f, 0.22f);
        }
        return state;
    }

    void apply_force_spec_to_render_state(const SimulationController::ForceSpec& spec, BodyRenderState* state)
    {
        const SceneEntityId entity_id = state ? state->entity_id : 0;
        const SceneEntityKind entity_kind = state ? state->entity_kind : SceneEntityKindNone;
        const bool is_selected = state ? state->is_selected : false;
        const bool is_preview = state ? state->is_preview : false;

        if (!state)
        {
            return;
        }

        *state = make_arrow_state(spec, is_preview);
        state->entity_id = entity_id;
        state->entity_kind = entity_kind;
        state->is_selected = is_selected;
    }

    bool make_render_state_from_shape(const hkpRigidBody* body, BodyRenderState& state)
    {
        const hkpShape* shape = body->getCollidable()->getShape();
        if (!shape)
        {
            return false;
        }

        switch (shape->getType())
        {
        case HK_SHAPE_BOX:
            {
                const hkpBoxShape* box_shape = static_cast<const hkpBoxShape*>(shape);
                const hkVector4& half_extents = box_shape->getHalfExtents();
                state = make_box_state(true, true, false, half_extents(0), half_extents(1), half_extents(2));
                return true;
            }
        case HK_SHAPE_SPHERE:
            {
                const hkpSphereShape* sphere_shape = static_cast<const hkpSphereShape*>(shape);
                state = make_sphere_state(true, true, false, sphere_shape->getRadius());
                return true;
            }
        case HK_SHAPE_CAPSULE:
            {
                const hkpCapsuleShape* capsule_shape = static_cast<const hkpCapsuleShape*>(shape);
                state = make_capsule_state(true, capsule_shape->getVertex(0), capsule_shape->getVertex(1), capsule_shape->getRadius());
                return true;
            }
        default:
            return false;
        }
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

int SimulationController::s_runtime_refcount = 0;

SimulationController::SimulationController()
    : m_ground_mode(GroundFlat)
    , m_is_playing(false)
    , m_runtime_matches_scene(true)
    , m_ragdoll_runtime_manager(new RagdollRuntimeManager())
    , m_simulation_world(new SimulationWorld())
    , m_transform_session_controller(0)
    , m_timestep(1.0f / 60.0f)
    , m_world(0)
    , m_ground_shape(0)
    , m_box_shape(0)
    , m_sphere_shape(0)
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

void SimulationController::clear_scene()
{
    clear_scene_contents();
    reset();
}

bool SimulationController::create_scene_from_preset(ScenePresetId preset_id, std::string* error_message)
{
    ScenePresetDefinition definition;
    std::size_t object_index = 0;
    std::size_t force_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before creating a new scene.";
        }
        return false;
    }

    if (!build_scene_preset(preset_id, &definition))
    {
        if (error_message)
        {
            *error_message = "The selected scene preset is not available.";
        }
        return false;
    }

    clear_scene_contents();
    m_ground_mode = static_cast<GroundMode>(definition.ground_mode);

    for (object_index = 0; object_index < definition.objects.size(); ++object_index)
    {
        SpawnedObjectSpec normalized_spec;
        SceneEntityId entity_id = 0;

        if (!normalize_object_spec(definition.objects[object_index].spec, &normalized_spec, error_message))
        {
            clear_scene_contents();
            reset();
            return false;
        }

        entity_id = m_scene_document.add_object(
            normalized_spec,
            definition.objects[object_index].name.c_str(),
            definition.objects[object_index].editable);
        if (static_cast<int>(object_index) == definition.ground_object_index)
        {
            m_default_ground_entity_id = entity_id;
        }
    }

    for (force_index = 0; force_index < definition.forces.size(); ++force_index)
    {
        m_scene_document.add_force(
            definition.forces[force_index].spec,
            definition.forces[force_index].name.c_str());
    }

    m_scene_document.clear_selection();
    reset();
    return true;
}

void SimulationController::clear_scene_contents()
{
    m_is_playing = false;
    m_has_object_preview = false;
    m_has_force_preview = false;
    m_default_ground_entity_id = 0;

    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->clear_runtimes(m_simulation_world);
    }

    m_scene_document.clear();
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

bool SimulationController::load_ragdoll(const char* path, std::string* error_message)
{
    SceneEntityId entity_id = 0;

    if (!m_ragdoll_runtime_manager ||
        !m_ragdoll_runtime_manager->load_ragdoll(m_scene_document, path, &entity_id, error_message))
    {
        return false;
    }

    RagdollSceneEntity* ragdoll = active_ragdoll_entity();
    if (ragdoll)
    {
        ragdoll->record.name = make_numbered_name("Ragdoll", entity_id);
    }

    reset();
    return true;
}

bool SimulationController::has_ragdoll() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->has_ragdoll(m_scene_document) : false;
}

const std::string& SimulationController::ragdoll_path() const
{
    static const std::string empty_path;
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->ragdoll_path(m_scene_document) : empty_path;
}

void SimulationController::set_ragdoll_start_position(float x, float y, float z)
{
    const float position[3] = { x, y, z };

    if (m_ragdoll_runtime_manager &&
        m_ragdoll_runtime_manager->set_active_start_position(m_scene_document, position) &&
        m_simulation_world)
    {
        m_simulation_world->sync_render_state();
    }
}

void SimulationController::get_ragdoll_start_position(float& x, float& y, float& z) const
{
    if (!m_ragdoll_runtime_manager)
    {
        x = 0.0f;
        y = 0.0f;
        z = 0.0f;
        return;
    }

    m_ragdoll_runtime_manager->get_active_start_position(m_scene_document, x, y, z);
}

int SimulationController::ragdoll_count() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->ragdoll_count(m_scene_document) : 0;
}

bool SimulationController::get_ragdoll_preview_data(SceneEntityId entity_id, RagdollPreviewData* preview_data) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_preview_data(entity_id, preview_data)
        : false;
}

bool SimulationController::get_selected_ragdoll_preview_data(RagdollPreviewData* preview_data) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_selected_preview_data(m_scene_document, preview_data)
        : false;
}

bool SimulationController::get_ragdoll_runtime_diagnostics(SceneEntityId entity_id, RagdollRuntimeDiagnostics* diagnostics) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_runtime_diagnostics(entity_id, diagnostics)
        : false;
}

bool SimulationController::get_selected_ragdoll_runtime_diagnostics(RagdollRuntimeDiagnostics* diagnostics) const
{
    return m_ragdoll_runtime_manager
        ? m_ragdoll_runtime_manager->get_selected_runtime_diagnostics(m_scene_document, diagnostics)
        : false;
}

bool SimulationController::get_selected_ragdoll_spec(RagdollSceneSpec* spec) const
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    const RagdollSceneEntity* ragdoll = 0;

    if (!spec || selected.kind != SceneEntityKindRagdoll)
    {
        return false;
    }

    ragdoll = find_ragdoll_entity(selected.id);
    if (!ragdoll)
    {
        return false;
    }

    *spec = ragdoll->ragdoll;
    return true;
}

bool SimulationController::update_selected_ragdoll(const RagdollSceneSpec& spec, std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    RagdollSceneEntity* ragdoll = 0;

    if (!can_author_scene() || selected.kind != SceneEntityKindRagdoll)
    {
        if (error_message)
        {
            *error_message = "Select a ragdoll and reset simulation before editing.";
        }
        return false;
    }

    ragdoll = active_ragdoll_entity();
    if (!ragdoll)
    {
        return false;
    }

    ragdoll->ragdoll = spec;
    reset();
    return true;
}

bool SimulationController::add_object(const SpawnedObjectSpec& spec, std::string* error_message)
{
    SpawnedObjectSpec normalized_spec;
    SceneEntityId entity_id = 0;

    if (!normalize_object_spec(spec, &normalized_spec, error_message))
    {
        return false;
    }

    entity_id = m_scene_document.add_object(normalized_spec, "Object", true);
    PhysicsObjectSceneEntity* object = find_object_entity(entity_id);
    if (object)
    {
        object->record.name = make_numbered_name("Rigid Body", entity_id);
    }
    m_scene_document.select_entity(entity_id, SceneEntityKindPhysicsObject);
    reset();
    return true;
}

bool SimulationController::import_physics_systems(const std::vector<ImportedPhysicsSystem>& systems, const std::vector<int>& selected_systems, std::string* error_message)
{
    SceneEntityId last_entity_id = 0;
    int imported_count = 0;
    std::size_t selected_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before importing physics.";
        }
        return false;
    }

    for (selected_index = 0; selected_index < selected_systems.size(); ++selected_index)
    {
        const int system_index = selected_systems[selected_index];
        const ImportedPhysicsSystem* system = 0;
        std::size_t object_index = 0;

        if (system_index < 0 || system_index >= static_cast<int>(systems.size()))
        {
            continue;
        }

        system = &systems[system_index];
        for (object_index = 0; object_index < system->objects.size(); ++object_index)
        {
            const ImportedPhysicsObject& imported_object = system->objects[object_index];
            SpawnedObjectSpec normalized_spec;
            SceneEntityId entity_id = 0;
            PhysicsObjectSceneEntity* object_entity = 0;

            if (!normalize_object_spec(imported_object.object_spec, &normalized_spec, error_message))
            {
                return false;
            }

            entity_id = m_scene_document.add_object(normalized_spec, imported_object.name.c_str(), imported_object.editable);
            object_entity = find_object_entity(entity_id);
            if (object_entity)
            {
                object_entity->record.name = system->name + " / " + imported_object.name;
            }
            last_entity_id = entity_id;
            ++imported_count;
        }
    }

    if (imported_count <= 0 || last_entity_id == 0)
    {
        if (error_message)
        {
            *error_message = "None of the selected physics systems produced importable scene objects.";
        }
        return false;
    }

    m_scene_document.select_entity(last_entity_id, SceneEntityKindPhysicsObject);
    reset();
    return true;
}

int SimulationController::spawned_object_count() const
{
    return static_cast<int>(m_scene_document.objects().size());
}

bool SimulationController::get_selected_object_spec(SpawnedObjectSpec* spec) const
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    const PhysicsObjectSceneEntity* object = 0;

    if (!spec || selected.kind != SceneEntityKindPhysicsObject)
    {
        return false;
    }

    object = find_object_entity(selected.id);
    if (!object)
    {
        return false;
    }

    *spec = object->object_spec;
    return true;
}

bool SimulationController::update_selected_object(const SpawnedObjectSpec& spec, std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    PhysicsObjectSceneEntity* object = 0;
    SpawnedObjectSpec normalized_spec;

    if (!can_author_scene() || selected.kind != SceneEntityKindPhysicsObject)
    {
        if (error_message)
        {
            *error_message = "Select an object and reset simulation before editing.";
        }
        return false;
    }

    if (!normalize_object_spec(spec, &normalized_spec, error_message))
    {
        return false;
    }

    object = find_object_entity(selected.id);
    if (!object)
    {
        return false;
    }

    if (!object->record.editable)
    {
        if (error_message)
        {
            *error_message = "The selected imported convex hull does not have a parametric editor.";
        }
        return false;
    }

    object->object_spec = normalized_spec;
    reset();
    return true;
}

bool SimulationController::add_force_entity(const ForceSpec& spec, std::string* error_message)
{
    ForceSpec committed_spec = spec;
    SceneEntityId entity_id = 0;

    (void)error_message;

    entity_id = m_scene_document.add_force(committed_spec, "Force");
    ForceSceneEntity* force = find_force_entity(entity_id);
    if (force)
    {
        force->record.name = make_numbered_name("Force", entity_id);
    }
    m_scene_document.select_entity(entity_id, SceneEntityKindForce);
    reset();
    return true;
}

int SimulationController::force_count() const
{
    return static_cast<int>(m_scene_document.forces().size());
}

bool SimulationController::get_selected_force_spec(ForceSpec* spec) const
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    const ForceSceneEntity* force = 0;

    if (!spec || selected.kind != SceneEntityKindForce)
    {
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    *spec = force->force_spec;
    return true;
}

bool SimulationController::update_selected_force(const ForceSpec& spec, std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    ForceSceneEntity* force = 0;

    if (!can_author_scene() || selected.kind != SceneEntityKindForce)
    {
        if (error_message)
        {
            *error_message = "Select a force and reset simulation before editing.";
        }
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    force->force_spec = spec;
    reset();
    return true;
}

bool SimulationController::set_selected_force_preview(const ForceSpec& spec, std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    ForceSceneEntity* force = 0;
    std::size_t body_index = 0;

    if (selected.kind != SceneEntityKindForce)
    {
        if (error_message)
        {
            *error_message = "Select a force before previewing force edits.";
        }
        return false;
    }

    force = find_force_entity(selected.id);
    if (!force)
    {
        return false;
    }

    force->force_spec = spec;

    for (body_index = 0; m_simulation_world && body_index < m_simulation_world->render_bodies().size(); ++body_index)
    {
        BodyRenderState& render_state = m_simulation_world->render_bodies()[body_index];
        if (render_state.entity_id == selected.id && render_state.entity_kind == SceneEntityKindForce)
        {
            SimulationWorld::apply_force_spec_to_render_state(spec, &render_state);
            return true;
        }
    }

    return false;
}

bool SimulationController::build_persisted_scene(PersistedSceneData* scene) const
{
    std::size_t ragdoll_index = 0;
    std::size_t object_index = 0;
    std::size_t force_index = 0;

    if (!scene)
    {
        return false;
    }

    *scene = PersistedSceneData();

    for (ragdoll_index = 0; ragdoll_index < m_scene_document.ragdolls().size(); ++ragdoll_index)
    {
        PersistedSceneRagdoll persisted_ragdoll;
        const RagdollSceneEntity& ragdoll = m_scene_document.ragdolls()[ragdoll_index];

        persisted_ragdoll.name = ragdoll.record.name;
        persisted_ragdoll.spec = ragdoll.ragdoll;
        scene->ragdolls.push_back(persisted_ragdoll);
    }

    for (object_index = 0; object_index < m_scene_document.objects().size(); ++object_index)
    {
        PersistedSceneObject persisted_object;
        const PhysicsObjectSceneEntity& object = m_scene_document.objects()[object_index];

        persisted_object.name = object.record.name;
        persisted_object.editable = object.record.editable;
        persisted_object.spec = object.object_spec;
        scene->objects.push_back(persisted_object);
    }

    for (force_index = 0; force_index < m_scene_document.forces().size(); ++force_index)
    {
        PersistedSceneForce persisted_force;
        const ForceSceneEntity& force = m_scene_document.forces()[force_index];

        persisted_force.name = force.record.name;
        persisted_force.spec = force.force_spec;
        scene->forces.push_back(persisted_force);
    }

    return true;
}

bool SimulationController::load_persisted_scene(const PersistedSceneData& scene, std::vector<std::string>* warnings, std::string* error_message)
{
    std::size_t object_index = 0;
    std::size_t force_index = 0;
    std::size_t ragdoll_index = 0;

    if (!can_author_scene())
    {
        if (error_message)
        {
            *error_message = "Reset simulation before loading a scene.";
        }
        return false;
    }

    clear_scene_contents();

    for (object_index = 0; object_index < scene.objects.size(); ++object_index)
    {
        SpawnedObjectSpec normalized_spec;
        const PersistedSceneObject& persisted_object = scene.objects[object_index];

        if (!normalize_object_spec(persisted_object.spec, &normalized_spec, error_message))
        {
            clear_scene_contents();
            reset();
            return false;
        }

        m_scene_document.add_object(normalized_spec, persisted_object.name.c_str(), persisted_object.editable);
    }

    for (force_index = 0; force_index < scene.forces.size(); ++force_index)
    {
        const PersistedSceneForce& persisted_force = scene.forces[force_index];
        m_scene_document.add_force(persisted_force.spec, persisted_force.name.c_str());
    }

    for (ragdoll_index = 0; ragdoll_index < scene.ragdolls.size(); ++ragdoll_index)
    {
        const PersistedSceneRagdoll& persisted_ragdoll = scene.ragdolls[ragdoll_index];
        SceneEntityId entity_id = m_scene_document.add_ragdoll(persisted_ragdoll.spec, persisted_ragdoll.name.c_str());
        if (!m_ragdoll_runtime_manager ||
            !m_ragdoll_runtime_manager->load_runtime(entity_id, persisted_ragdoll.spec, error_message))
        {
            m_scene_document.remove_entity(entity_id, SceneEntityKindRagdoll);

            if (warnings)
            {
                warnings->push_back(std::string("Skipped ragdoll '") + persisted_ragdoll.name + "' because its HKX reference could not be loaded.");
            }

            if (error_message)
            {
                error_message->clear();
            }
            continue;
        }

    }

    m_scene_document.clear_selection();
    reset();
    return true;
}

bool SimulationController::delete_selected_entity()
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    if (!can_author_scene() || selected.id == 0)
    {
        return false;
    }

    if (selected.kind == SceneEntityKindRagdoll && m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->delete_runtime_for_entity(selected.id);
    }

    if (!m_scene_document.remove_entity(selected.id, selected.kind))
    {
        return false;
    }

    reset();
    return true;
}

bool SimulationController::duplicate_selected_entity(std::string* error_message)
{
    const SceneEntitySelection selected = m_scene_document.selected_entity();
    SceneEntityId duplicate_id = 0;

    if (!can_author_scene() || selected.id == 0)
    {
        return false;
    }

    duplicate_id = m_scene_document.duplicate_entity(selected.id, selected.kind);
    if (duplicate_id == 0)
    {
        return false;
    }

    if (selected.kind == SceneEntityKindRagdoll)
    {
        const RagdollSceneEntity* duplicate = find_ragdoll_entity(duplicate_id);

        if (!duplicate || !m_ragdoll_runtime_manager ||
            !m_ragdoll_runtime_manager->load_runtime(duplicate_id, duplicate->ragdoll, error_message))
        {
            m_scene_document.remove_entity(duplicate_id, SceneEntityKindRagdoll);
            return false;
        }
    }

    m_scene_document.select_entity(duplicate_id, selected.kind);
    reset();
    return true;
}

void SimulationController::set_object_preview(const SpawnedObjectSpec& spec)
{
    m_has_object_preview = true;
    m_object_preview_spec = spec;

    if (m_object_preview_spec.object_type == ObjectSphere)
    {
        m_object_preview_spec.scale[1] = m_object_preview_spec.scale[0];
        m_object_preview_spec.scale[2] = m_object_preview_spec.scale[0];
    }

    rebuild_preview_bodies();
}

void SimulationController::clear_object_preview()
{
    m_has_object_preview = false;
    rebuild_preview_bodies();
}

bool SimulationController::apply_push_force(const ForceSpec& spec, std::string* error_message)
{
    if (!m_simulation_world)
    {
        return false;
    }

    if (!m_ragdoll_runtime_manager ||
        !m_simulation_world->apply_push_force(m_ragdoll_runtime_manager->runtimes(), spec, error_message))
    {
        return false;
    }

    m_runtime_matches_scene = false;
    return true;
}

void SimulationController::set_force_preview(const ForceSpec& spec)
{
    m_has_force_preview = true;
    m_force_preview_spec = spec;
    rebuild_preview_bodies();
}

void SimulationController::clear_force_preview()
{
    m_has_force_preview = false;
    rebuild_preview_bodies();
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
    return m_simulation_world ? m_simulation_world->render_bodies() : m_render_bodies;
}

const std::vector<BodyRenderState>& SimulationController::preview_bodies() const
{
    return m_preview_bodies;
}

const SceneDocument& SimulationController::scene_document() const
{
    return m_scene_document;
}

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

bool SimulationController::resolve_runtime_entity_for_body(const hkpRigidBody* body, SceneEntityId* entity_id, SceneEntityKind* entity_kind) const
{
    return m_simulation_world
        ? m_simulation_world->resolve_runtime_entity_for_body(body, entity_id, entity_kind)
        : false;
}

void SimulationController::initialize_runtime()
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

void SimulationController::shutdown_runtime()
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

void SimulationController::destroy_world()
{
    remove_loaded_ragdoll_from_world();

    if (m_world)
    {
        m_world->markForWrite();

        std::size_t body_index = 0;
        for (body_index = 0; body_index < m_owned_bodies.size(); ++body_index)
        {
            m_world->removeEntity(m_owned_bodies[body_index]);
            m_owned_bodies[body_index]->removeReference();
        }

        m_world->unmarkForWrite();
        m_world->removeReference();
        m_world = 0;
    }

    if (m_sphere_shape)
    {
        m_sphere_shape->removeReference();
        m_sphere_shape = 0;
    }

    if (m_box_shape)
    {
        m_box_shape->removeReference();
        m_box_shape = 0;
    }

    if (m_ground_shape)
    {
        m_ground_shape->removeReference();
        m_ground_shape = 0;
    }

    m_owned_bodies.clear();
    m_runtime_bodies.clear();
    m_runtime_body_lookup.clear();
    m_runtime_entities.clear();
    m_render_bodies.clear();
}

void SimulationController::create_world()
{
    const float gravity_magnitude = SimulationSettings::base_gravity() * SimulationSettings::instance().gravity_scale();
    hkpWorldCinfo world_info;
    world_info.m_gravity.set(0.0f, -gravity_magnitude, 0.0f);
    world_info.m_simulationType = hkpWorldCinfo::SIMULATION_TYPE_CONTINUOUS;

    m_world = new hkpWorld(world_info);

    m_world->markForWrite();
    hkpAgentRegisterUtil::registerAllAgents(m_world->getCollisionDispatcher());

    create_spawned_objects();
    create_force_entities();
    add_loaded_ragdoll();
    refresh_selection_highlight();

    m_world->unmarkForWrite();
    m_runtime_matches_scene = true;
    sync_render_state();
    rebuild_preview_bodies();
}

void SimulationController::seed_default_scene_objects()
{
    SpawnedObjectSpec ground_spec;
    SpawnedObjectSpec box_spec;
    SpawnedObjectSpec sphere_spec;

    ground_spec.object_type = ObjectCube;
    ground_spec.body_type = BodyStatic;
    ground_spec.position[0] = 0.0f;
    ground_spec.position[1] = -0.5f;
    ground_spec.position[2] = 0.0f;
    ground_spec.rotation_degrees[0] = 0.0f;
    ground_spec.rotation_degrees[1] = 0.0f;
    ground_spec.rotation_degrees[2] = 0.0f;
    ground_spec.scale[0] = 12.0f;
    ground_spec.scale[1] = 0.5f;
    ground_spec.scale[2] = 12.0f;
    ground_spec.restitution = 0.0f;
    ground_spec.mass = 0.0f;

    box_spec.object_type = ObjectCube;
    box_spec.body_type = BodyDynamic;
    box_spec.position[0] = -1.5f;
    box_spec.position[1] = 6.0f;
    box_spec.position[2] = 0.0f;
    box_spec.rotation_degrees[0] = 0.0f;
    box_spec.rotation_degrees[1] = 0.0f;
    box_spec.rotation_degrees[2] = 0.0f;
    box_spec.scale[0] = 0.75f;
    box_spec.scale[1] = 0.75f;
    box_spec.scale[2] = 0.75f;
    box_spec.restitution = 0.1f;
    box_spec.mass = 12.0f;

    sphere_spec.object_type = ObjectSphere;
    sphere_spec.body_type = BodyDynamic;
    sphere_spec.position[0] = 1.25f;
    sphere_spec.position[1] = 8.0f;
    sphere_spec.position[2] = 0.0f;
    sphere_spec.rotation_degrees[0] = 0.0f;
    sphere_spec.rotation_degrees[1] = 0.0f;
    sphere_spec.rotation_degrees[2] = 0.0f;
    sphere_spec.scale[0] = 0.65f;
    sphere_spec.scale[1] = 0.65f;
    sphere_spec.scale[2] = 0.65f;
    sphere_spec.restitution = 0.25f;
    sphere_spec.mass = 6.0f;

    m_default_ground_entity_id = m_scene_document.add_object(ground_spec, "Ground", true);
    m_scene_document.add_object(box_spec, "Starter Box", true);
    m_scene_document.add_object(sphere_spec, "Starter Sphere", true);
    update_ground_scene_object();
    m_scene_document.clear_selection();
}

void SimulationController::update_ground_scene_object()
{
    PhysicsObjectSceneEntity* ground = find_object_entity(m_default_ground_entity_id);

    if (!ground)
    {
        return;
    }

    ground->object_spec.object_type = ObjectCube;
    ground->object_spec.body_type = BodyStatic;
    ground->object_spec.position[0] = 0.0f;
    ground->object_spec.position[1] = -0.5f;
    ground->object_spec.position[2] = 0.0f;
    ground->object_spec.rotation_degrees[0] = 0.0f;
    ground->object_spec.rotation_degrees[1] = 0.0f;
    ground->object_spec.rotation_degrees[2] = 0.0f;
    ground->object_spec.scale[0] = 12.0f;
    ground->object_spec.scale[1] = 0.5f;
    ground->object_spec.scale[2] = 12.0f;
    ground->object_spec.restitution = 0.0f;
    ground->object_spec.mass = 0.0f;

    if (m_ground_mode == GroundSlanted)
    {
        ground->object_spec.position[0] = -1.5f;
        ground->object_spec.rotation_degrees[2] = 20.0f;
    }
}

void SimulationController::create_ground_body()
{
    hkVector4 half_extents(12.0f, 0.5f, 12.0f);
    m_ground_shape = new hkpBoxShape(half_extents);

    hkpRigidBodyCinfo body_info;
    body_info.m_shape = m_ground_shape;
    body_info.m_motionType = hkpMotion::MOTION_FIXED;
    body_info.m_position.set(0.0f, -0.5f, 0.0f);

    if (m_ground_mode == GroundSlanted)
    {
        hkQuaternion slope_rotation;
        slope_rotation.setAxisAngle(hkVector4(0.0f, 0.0f, 1.0f), HK_REAL_PI / 9.0f);
        body_info.m_rotation = slope_rotation;
        body_info.m_position.set(-1.5f, -0.5f, 0.0f);
    }

    BodyRenderState state = make_box_state(false, true, false, 12.0f, 0.5f, 12.0f);
    hkpRigidBody* ground = new hkpRigidBody(body_info);
    add_body(0, SceneEntityKindNone, ground, state);
}

void SimulationController::create_dynamic_box()
{
    hkVector4 half_extents(0.75f, 0.75f, 0.75f);
    m_box_shape = new hkpBoxShape(half_extents);

    hkpRigidBodyCinfo body_info;
    body_info.m_shape = m_box_shape;
    body_info.m_motionType = hkpMotion::MOTION_DYNAMIC;
    body_info.m_position.set(-1.5f, 6.0f, 0.0f);
    body_info.m_restitution = 0.1f;
    body_info.m_friction = 0.8f;
    body_info.m_mass = 12.0f;
    hkpMassProperties mass_properties;
    hkpInertiaTensorComputer::computeBoxVolumeMassProperties(half_extents, body_info.m_mass, mass_properties);
    hkpInertiaTensorComputer::setMassProperties(mass_properties, body_info);

    BodyRenderState state = make_box_state(true, true, false, 0.75f, 0.75f, 0.75f);
    hkpRigidBody* rigid_body = new hkpRigidBody(body_info);
    add_body(0, SceneEntityKindNone, rigid_body, state);
}

void SimulationController::create_dynamic_sphere()
{
    const hkReal radius = 0.65f;
    m_sphere_shape = new hkpSphereShape(radius);

    hkpRigidBodyCinfo body_info;
    body_info.m_shape = m_sphere_shape;
    body_info.m_motionType = hkpMotion::MOTION_DYNAMIC;
    body_info.m_position.set(1.25f, 8.0f, 0.0f);
    body_info.m_restitution = 0.25f;
    body_info.m_friction = 0.6f;
    body_info.m_mass = 6.0f;
    hkpMassProperties mass_properties;
    hkpInertiaTensorComputer::computeSphereVolumeMassProperties(radius, body_info.m_mass, mass_properties);
    hkpInertiaTensorComputer::setMassProperties(mass_properties, body_info);

    BodyRenderState state = make_sphere_state(true, true, false, radius);
    hkpRigidBody* rigid_body = new hkpRigidBody(body_info);
    add_body(0, SceneEntityKindNone, rigid_body, state);
}

void SimulationController::create_spawned_objects()
{
    const std::vector<PhysicsObjectSceneEntity>& objects = m_scene_document.objects();

    for (std::size_t object_index = 0; object_index < objects.size(); ++object_index)
    {
        hkpRigidBody* rigid_body = 0;
        BodyRenderState state;

        if (!create_body_from_spec(objects[object_index].object_spec, &rigid_body, &state, 0))
        {
            continue;
        }

        add_body(objects[object_index].record.id, SceneEntityKindPhysicsObject, rigid_body, state);
    }
}

void SimulationController::create_force_entities()
{
    const std::vector<ForceSceneEntity>& forces = m_scene_document.forces();
    const SceneEntitySelection& selected = m_scene_document.selected_entity();
    std::size_t force_index = 0;

    for (force_index = 0; force_index < forces.size(); ++force_index)
    {
        BodyRenderState state = make_arrow_state(forces[force_index].force_spec, false);
        state.entity_id = forces[force_index].record.id;
        state.entity_kind = SceneEntityKindForce;
        state.is_selected = selected.id == state.entity_id && selected.kind == state.entity_kind;
        m_render_bodies.push_back(state);
    }
}

void SimulationController::apply_continuous_force_entities()
{
    const std::vector<ForceSceneEntity>& forces = m_scene_document.forces();
    std::size_t force_index = 0;

    for (force_index = 0; force_index < forces.size(); ++force_index)
    {
        hkpRigidBody* rigid_body = 0;
        float hit_point[3] = { 0.0f, 0.0f, 0.0f };
        float direction[3] = { 0.0f, 0.0f, 0.0f };
        hkVector4 force;
        hkVector4 point;
        float signed_strength = 0.0f;
        RagdollRuntime* owning_ragdoll = 0;

        if (!forces[force_index].force_spec.active)
        {
            continue;
        }

        if (!find_force_target(forces[force_index].force_spec, &rigid_body, hit_point, direction, 0))
        {
            continue;
        }

        signed_strength = forces[force_index].force_spec.mode == ForcePull
            ? -forces[force_index].force_spec.strength
            : forces[force_index].force_spec.strength;

        owning_ragdoll = find_ragdoll_runtime_owning_body(rigid_body);
        if (owning_ragdoll)
        {
            // A force aimed at the ragdoll must first break the pose hold, otherwise
            // driveToPose re-imposes the authored velocities every frame and cancels
            // the push (Havok User Guide 5.1.5.3). Once released the ragdoll is fully
            // dynamic and obeys the same momentum rules as any other body: the force
            // is applied at the hit point with real Newtons. With the global ragdoll
            // mass scale making the bones a sane weight, ordinary force values move it.
            owning_ragdoll->release();
        }

        force.set(direction[0] * signed_strength, direction[1] * signed_strength, direction[2] * signed_strength);
        point.set(hit_point[0], hit_point[1], hit_point[2]);

        m_world->markForWrite();
        rigid_body->applyForce(m_timestep, force, point);
        m_world->unmarkForWrite();
    }
}

RagdollRuntime* SimulationController::find_ragdoll_runtime_owning_body(const hkpRigidBody* body)
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_runtime_owning_body(body) : 0;
}

void SimulationController::add_loaded_ragdoll()
{
    std::size_t runtime_index = 0;

    if (!m_world || !m_ragdoll_runtime_manager)
    {
        return;
    }

    const std::vector<RagdollRuntime*>& ragdoll_runtimes = m_ragdoll_runtime_manager->runtimes();

    for (runtime_index = 0; runtime_index < ragdoll_runtimes.size(); ++runtime_index)
    {
        RagdollRuntime* runtime_state = ragdoll_runtimes[runtime_index];
        const RagdollSceneEntity* ragdoll = runtime_state ? find_ragdoll_entity(runtime_state->entity_id()) : 0;
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

            if (!rigid_body)
            {
                continue;
            }

            if (!make_render_state_from_shape(rigid_body, state))
            {
                continue;
            }

            add_render_body(ragdoll->record.id, SceneEntityKindRagdoll, rigid_body, state);
            ++runtime_entity.runtime_body_count;
            ++runtime_entity.render_body_count;
        }

        if (runtime_entity.render_body_count > 0)
        {
            m_runtime_entities.push_back(runtime_entity);
        }
    }
}

void SimulationController::sync_render_state()
{
    if (m_simulation_world)
    {
        m_simulation_world->sync_render_state();
    }
}

void SimulationController::add_body(SceneEntityId entity_id, SceneEntityKind entity_kind, hkpRigidBody* body, const BodyRenderState& state)
{
    m_world->addEntity(body);
    m_owned_bodies.push_back(body);
    add_render_body(entity_id, entity_kind, body, state);

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

void SimulationController::add_render_body(SceneEntityId entity_id, SceneEntityKind entity_kind, hkpRigidBody* body, const BodyRenderState& state)
{
    BodyRenderState render_state = state;
    const int render_index = static_cast<int>(m_render_bodies.size());
    const SceneEntitySelection& selected = m_scene_document.selected_entity();

    render_state.entity_id = entity_id;
    render_state.entity_kind = entity_kind;
    render_state.is_selected = selected.id == entity_id && selected.kind == entity_kind;
    m_render_bodies.push_back(render_state);

    RuntimeBodyBinding binding;
    binding.entity_id = entity_id;
    binding.entity_kind = entity_kind;
    binding.body = body;
    binding.render_index = render_index;
    m_runtime_body_lookup[body] = m_runtime_bodies.size();
    m_runtime_bodies.push_back(binding);
}

void SimulationController::remove_loaded_ragdoll_from_world()
{
    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->detach_from_world(m_simulation_world);
    }
}

void SimulationController::release_ragdoll_runtime_at(std::size_t runtime_index)
{
    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->release_runtime_at(runtime_index);
    }
}

void SimulationController::unload_ragdoll()
{
    if (m_ragdoll_runtime_manager)
    {
        m_ragdoll_runtime_manager->clear_scene_ragdolls(m_scene_document, m_simulation_world);
    }
}

const RagdollSceneEntity* SimulationController::primary_ragdoll_entity() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_entity(m_scene_document) : 0;
}

RagdollSceneEntity* SimulationController::primary_ragdoll_entity()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_entity(m_scene_document) : 0;
}

const RagdollSceneEntity* SimulationController::active_ragdoll_entity() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_entity(m_scene_document) : 0;
}

RagdollSceneEntity* SimulationController::active_ragdoll_entity()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_entity(m_scene_document) : 0;
}

const RagdollSceneEntity* SimulationController::find_ragdoll_entity(SceneEntityId entity_id) const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_entity(m_scene_document, entity_id) : 0;
}

const ForceSceneEntity* SimulationController::find_force_entity(SceneEntityId entity_id) const
{
    const std::vector<ForceSceneEntity>& forces = m_scene_document.forces();
    std::size_t force_index = 0;

    for (force_index = 0; force_index < forces.size(); ++force_index)
    {
        if (forces[force_index].record.id == entity_id)
        {
            return &forces[force_index];
        }
    }

    return 0;
}

ForceSceneEntity* SimulationController::find_force_entity(SceneEntityId entity_id)
{
    std::vector<ForceSceneEntity>& forces = m_scene_document.forces();
    std::size_t force_index = 0;

    for (force_index = 0; force_index < forces.size(); ++force_index)
    {
        if (forces[force_index].record.id == entity_id)
        {
            return &forces[force_index];
        }
    }

    return 0;
}

const PhysicsObjectSceneEntity* SimulationController::find_object_entity(SceneEntityId entity_id) const
{
    const std::vector<PhysicsObjectSceneEntity>& objects = m_scene_document.objects();
    std::size_t object_index = 0;

    for (object_index = 0; object_index < objects.size(); ++object_index)
    {
        if (objects[object_index].record.id == entity_id)
        {
            return &objects[object_index];
        }
    }

    return 0;
}

PhysicsObjectSceneEntity* SimulationController::find_object_entity(SceneEntityId entity_id)
{
    std::vector<PhysicsObjectSceneEntity>& objects = m_scene_document.objects();
    std::size_t object_index = 0;

    for (object_index = 0; object_index < objects.size(); ++object_index)
    {
        if (objects[object_index].record.id == entity_id)
        {
            return &objects[object_index];
        }
    }

    return 0;
}

RagdollRuntime* SimulationController::find_ragdoll_runtime(SceneEntityId entity_id)
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_runtime(entity_id) : 0;
}

const RagdollRuntime* SimulationController::find_ragdoll_runtime(SceneEntityId entity_id) const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->find_runtime(entity_id) : 0;
}

RagdollRuntime* SimulationController::primary_ragdoll_runtime()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_runtime() : 0;
}

RagdollRuntime* SimulationController::active_ragdoll_runtime()
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_runtime(m_scene_document) : 0;
}

const RagdollRuntime* SimulationController::primary_ragdoll_runtime() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->primary_runtime() : 0;
}

const RagdollRuntime* SimulationController::active_ragdoll_runtime() const
{
    return m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->active_runtime(m_scene_document) : 0;
}

const SimulationController::RuntimeBodyBinding* SimulationController::find_runtime_body_binding(const hkpRigidBody* body) const
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

const SimulationController::RuntimeEntityBinding* SimulationController::find_runtime_entity_binding(SceneEntityId entity_id, SceneEntityKind entity_kind) const
{
    std::size_t entity_index = 0;

    for (entity_index = 0; entity_index < m_runtime_entities.size(); ++entity_index)
    {
        if (m_runtime_entities[entity_index].entity_id == entity_id &&
            m_runtime_entities[entity_index].entity_kind == entity_kind)
        {
            return &m_runtime_entities[entity_index];
        }
    }

    return 0;
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

bool SimulationController::pick_force_entity_from_ray(
    const float ray_origin[3],
    const float ray_direction[3],
    float max_distance,
    SceneEntityId* entity_id,
    SceneEntityKind* entity_kind) const
{
    SceneEntityId best_id = 0;
    float best_distance = max_distance;
    std::size_t body_index = 0;

    for (body_index = 0; body_index < m_render_bodies.size(); ++body_index)
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

bool SimulationController::normalize_object_spec(
    const SpawnedObjectSpec& spec,
    SpawnedObjectSpec* normalized_spec,
    std::string* error_message) const
{
    if (!normalized_spec)
    {
        return false;
    }

    *normalized_spec = spec;

    if (normalized_spec->object_type == ObjectConvexHull)
    {
        if (normalized_spec->convex_hull_vertices.size() < 4)
        {
            if (error_message)
            {
                *error_message = "Convex hull objects require at least four vertices.";
            }
            return false;
        }
    }

    if (normalized_spec->scale[0] <= 0.0f || normalized_spec->scale[1] <= 0.0f || normalized_spec->scale[2] <= 0.0f)
    {
        if (error_message)
        {
            *error_message = "Object scale must be positive on every axis.";
        }
        return false;
    }

    if (normalized_spec->body_type == BodyDynamic && normalized_spec->mass <= 0.0f)
    {
        if (error_message)
        {
            *error_message = "Dynamic objects require a positive mass.";
        }
        return false;
    }

    if (normalized_spec->body_type == BodyStatic)
    {
        normalized_spec->mass = 0.0f;
    }

    if (normalized_spec->object_type == ObjectSphere)
    {
        normalized_spec->scale[1] = normalized_spec->scale[0];
        normalized_spec->scale[2] = normalized_spec->scale[0];
    }

    return true;
}

bool SimulationController::apply_entity_runtime_position(SceneEntityId id, SceneEntityKind kind, const float position[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_position(
            m_scene_document,
            m_ragdoll_runtime_manager ? m_ragdoll_runtime_manager->runtimes() : std::vector<RagdollRuntime*>(),
            id,
            kind,
            position)
        : false;
}

bool SimulationController::apply_entity_runtime_rotation(SceneEntityId id, SceneEntityKind kind, const float rotation_degrees[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_rotation(m_scene_document, id, kind, rotation_degrees)
        : false;
}

bool SimulationController::apply_entity_runtime_scale(SceneEntityId id, SceneEntityKind kind, const float scale[3])
{
    return m_simulation_world
        ? m_simulation_world->apply_entity_runtime_scale(m_scene_document, id, kind, scale)
        : false;
}

bool SimulationController::create_body_from_spec(
    const SpawnedObjectSpec& spec,
    hkpRigidBody** body,
    BodyRenderState* state,
    std::string* error_message)
{
    if (!body || !state)
    {
        return false;
    }

    const bool is_dynamic = spec.body_type == BodyDynamic;
    hkpShape* shape = 0;

    if (spec.object_type == ObjectCube)
    {
        hkVector4 half_extents(spec.scale[0], spec.scale[1], spec.scale[2]);
        shape = new hkpBoxShape(half_extents);
    }
    else if (spec.object_type == ObjectSphere)
    {
        shape = new hkpSphereShape(spec.scale[0]);
    }
    else if (spec.object_type == ObjectConvexHull)
    {
        std::vector<float> packed_vertices(spec.convex_hull_vertices.size() * 3);
        hkStridedVertices strided_vertices;
        hkGeometry geometry;
        hkArray<hkVector4> plane_equations;
        std::size_t vertex_index = 0;

        for (vertex_index = 0; vertex_index < spec.convex_hull_vertices.size(); ++vertex_index)
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

bool SimulationController::build_render_state_from_spec(const SpawnedObjectSpec& spec, bool is_preview, BodyRenderState* state) const
{
    if (!state)
    {
        return false;
    }

    const bool is_dynamic = spec.body_type == BodyDynamic;
    hkQuaternion rotation = make_quaternion_from_euler_degrees(
        spec.rotation_degrees[0],
        spec.rotation_degrees[1],
        spec.rotation_degrees[2]);

    if (spec.object_type == ObjectCube)
    {
        *state = make_box_state(is_dynamic, !is_preview, is_preview, spec.scale[0], spec.scale[1], spec.scale[2]);
    }
    else if (spec.object_type == ObjectSphere)
    {
        *state = make_sphere_state(is_dynamic, !is_preview, is_preview, spec.scale[0]);
    }
    else if (spec.object_type == ObjectConvexHull)
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

bool SimulationController::find_force_target(
    const ForceSpec& spec,
    hkpRigidBody** body,
    float hit_point[3],
    float direction[3],
    std::string* error_message) const
{
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