#include "physics_import.h"

#include <algorithm>
#include <cmath>
#include <stdio.h>

#include <Common/Base/hkBase.h>
#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Math/Matrix/hkTransform.h>
#include <Common/Base/System/Io/IStream/hkIStream.h>

#include <Physics/Collide/Agent/Collidable/hkpCollidable.h>
#include <Physics/Collide/Shape/Compound/Collection/List/hkpListShape.h>
#include <Physics/Collide/Shape/Compound/Tree/Mopp/hkpMoppBvTreeShape.h>
#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTransform/hkpConvexTransformShape.h>
#include <Physics/Collide/Shape/Convex/ConvexTranslate/hkpConvexTranslateShape.h>
#include <Physics/Collide/Shape/Convex/ConvexVertices/hkpConvexVerticesShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Collide/Shape/Misc/Transform/hkpTransformShape.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/Motion/hkpMotion.h>
#include <Physics/Dynamics/World/hkpPhysicsSystem.h>
#include <Physics/Utilities/Serialize/hkpHavokSnapshot.h>
#include <Physics/Utilities/Serialize/hkpPhysicsData.h>

#include "simulation_controller.h"

namespace
{
    const float kPi = 3.14159265f;

    class LoadedPhysicsSnapshot
    {
    public:
        LoadedPhysicsSnapshot()
            : m_allocated_data(HK_NULL)
        {
        }

        ~LoadedPhysicsSnapshot()
        {
            if (m_allocated_data != HK_NULL)
            {
                m_allocated_data->removeReference();
                m_allocated_data = HK_NULL;
            }
        }

        hkpPhysicsData* load(const char* input_file)
        {
            hkIstream input(input_file);
            if (!input.isOk())
            {
                fprintf(stderr, "Error: cannot open input HKX file %s\n", input_file);
                return HK_NULL;
            }

            hkpPhysicsData* physics_data = hkpHavokSnapshot::load(input.getStreamReader(), &m_allocated_data);
            if (physics_data == HK_NULL)
            {
                fprintf(stderr, "Error: failed to load physics data from %s\n", input_file);
            }
            return physics_data;
        }

    private:
        hkPackfileReader::AllocatedData* m_allocated_data;
    };

    struct ExtractedShape
    {
        enum Kind
        {
            KindNone,
            KindBox,
            KindSphere,
            KindConvexHull
        };

        ExtractedShape()
            : kind(KindNone)
            , sphere_radius(0.0f)
            , shape_radius(0.05f)
        {
            local_transform.setIdentity();
            box_half_extents.set(0.0f, 0.0f, 0.0f);
        }

        Kind kind;
        hkTransform local_transform;
        hkVector4 box_half_extents;
        float sphere_radius;
        float shape_radius;
        std::vector<ConvexHullVertex> hull_vertices;
    };

    float radians_to_degrees(float value)
    {
        return value * (180.0f / kPi);
    }

    float max_abs_component(float a, float b)
    {
        const float abs_a = std::fabs(a);
        const float abs_b = std::fabs(b);
        return abs_a > abs_b ? abs_a : abs_b;
    }

    void quaternion_to_euler_degrees(const hkQuaternion& quaternion, float output[3])
    {
        const float x = quaternion(0);
        const float y = quaternion(1);
        const float z = quaternion(2);
        const float w = quaternion(3);
        const float sinr_cosp = 2.0f * (w * x + y * z);
        const float cosr_cosp = 1.0f - 2.0f * (x * x + y * y);
        const float sinp = 2.0f * (w * y - z * x);
        const float siny_cosp = 2.0f * (w * z + x * y);
        const float cosy_cosp = 1.0f - 2.0f * (y * y + z * z);
        float pitch = 0.0f;

        output[0] = radians_to_degrees(std::atan2(sinr_cosp, cosr_cosp));

        if (sinp >= 1.0f)
        {
            pitch = kPi * 0.5f;
        }
        else if (sinp <= -1.0f)
        {
            pitch = -kPi * 0.5f;
        }
        else
        {
            pitch = std::asin(sinp);
        }

        output[1] = radians_to_degrees(pitch);
        output[2] = radians_to_degrees(std::atan2(siny_cosp, cosy_cosp));
    }

    void append_vertex(const hkVector4& point, std::vector<ConvexHullVertex>& vertices)
    {
        vertices.push_back(ConvexHullVertex(point(0), point(1), point(2)));
    }

    hkTransform make_translation_transform(const hkVector4& translation)
    {
        hkTransform transform;
        transform.setIdentity();
        transform.setTranslation(translation);
        return transform;
    }

    float extract_shape_radius(const hkpShape* shape)
    {
        if (shape == HK_NULL)
        {
            return 0.05f;
        }

        switch (shape->getType())
        {
        case HK_SHAPE_CONVEX_VERTICES:
            return static_cast<const hkpConvexVerticesShape*>(shape)->getRadius();
        case HK_SHAPE_CONVEX_TRANSLATE:
            return extract_shape_radius(static_cast<const hkpConvexTranslateShape*>(shape)->getChildShape());
        case HK_SHAPE_TRANSFORM:
            return extract_shape_radius(static_cast<const hkpTransformShape*>(shape)->getChildShape());
        case HK_SHAPE_CONVEX_TRANSFORM:
            return extract_shape_radius(static_cast<const hkpConvexTransformShape*>(shape)->getChildShape());
        case HK_SHAPE_MOPP:
            return extract_shape_radius(static_cast<const hkpMoppBvTreeShape*>(shape)->getChild());
        case HK_SHAPE_LIST:
            {
                const hkpListShape* list_shape = static_cast<const hkpListShape*>(shape);
                if (list_shape->getNumChildShapes() > 0)
                {
                    return extract_shape_radius(list_shape->getChildShapeInl(0));
                }
            }
            break;
        default:
            break;
        }

        return 0.05f;
    }

    void append_box_vertices(const hkVector4& half_extents, const hkTransform& transform, std::vector<ConvexHullVertex>& vertices)
    {
        const float x = half_extents(0);
        const float y = half_extents(1);
        const float z = half_extents(2);
        const float corners[8][3] = {
            { -x, -y, -z },
            { -x, -y,  z },
            { -x,  y, -z },
            { -x,  y,  z },
            {  x, -y, -z },
            {  x, -y,  z },
            {  x,  y, -z },
            {  x,  y,  z }
        };
        int corner_index = 0;

        for (corner_index = 0; corner_index < 8; ++corner_index)
        {
            hkVector4 point;
            hkVector4 transformed;

            point.set(corners[corner_index][0], corners[corner_index][1], corners[corner_index][2]);
            transformed.setTransformedPos(transform, point);
            append_vertex(transformed, vertices);
        }
    }

    void append_sphere_vertices(float radius, const hkTransform& transform, std::vector<ConvexHullVertex>& vertices)
    {
        const float points[6][3] = {
            {  radius, 0.0f, 0.0f },
            { -radius, 0.0f, 0.0f },
            { 0.0f,  radius, 0.0f },
            { 0.0f, -radius, 0.0f },
            { 0.0f, 0.0f,  radius },
            { 0.0f, 0.0f, -radius }
        };
        int point_index = 0;

        for (point_index = 0; point_index < 6; ++point_index)
        {
            hkVector4 point;
            hkVector4 transformed;

            point.set(points[point_index][0], points[point_index][1], points[point_index][2]);
            transformed.setTransformedPos(transform, point);
            append_vertex(transformed, vertices);
        }
    }

    bool collect_original_convex_vertices(const hkpConvexVerticesShape* shape, std::vector<ConvexHullVertex>& vertices)
    {
        hkArray<hkVector4> original_vertices;
        int vertex_index = 0;

        if (!shape)
        {
            return false;
        }

        shape->getOriginalVertices(original_vertices);
        for (vertex_index = 0; vertex_index < original_vertices.getSize(); ++vertex_index)
        {
            append_vertex(original_vertices[vertex_index], vertices);
        }

        return !vertices.empty();
    }

    bool collect_transformed_vertices(const hkpShape* shape, const hkTransform& transform, std::vector<ConvexHullVertex>& vertices)
    {
        if (shape == HK_NULL)
        {
            return false;
        }

        switch (shape->getType())
        {
        case HK_SHAPE_BOX:
            append_box_vertices(static_cast<const hkpBoxShape*>(shape)->getHalfExtents(), transform, vertices);
            return true;

        case HK_SHAPE_SPHERE:
            append_sphere_vertices(static_cast<const hkpSphereShape*>(shape)->getRadius(), transform, vertices);
            return true;

        case HK_SHAPE_CONVEX_VERTICES:
            {
                const hkpConvexVerticesShape* convex_shape = static_cast<const hkpConvexVerticesShape*>(shape);
                hkArray<hkVector4> original_vertices;
                int vertex_index = 0;

                convex_shape->getOriginalVertices(original_vertices);
                for (vertex_index = 0; vertex_index < original_vertices.getSize(); ++vertex_index)
                {
                    hkVector4 transformed;
                    transformed.setTransformedPos(transform, original_vertices[vertex_index]);
                    append_vertex(transformed, vertices);
                }

                return original_vertices.getSize() > 0;
            }

        case HK_SHAPE_CONVEX_TRANSLATE:
            {
                const hkpConvexTranslateShape* translate_shape = static_cast<const hkpConvexTranslateShape*>(shape);
                hkTransform local_transform = make_translation_transform(translate_shape->getTranslation());
                hkTransform combined_transform;
                combined_transform.setMul(transform, local_transform);
                return collect_transformed_vertices(translate_shape->getChildShape(), combined_transform, vertices);
            }

        case HK_SHAPE_TRANSFORM:
            {
                const hkpTransformShape* transform_shape = static_cast<const hkpTransformShape*>(shape);
                hkTransform combined_transform;
                combined_transform.setMul(transform, transform_shape->getTransform());
                return collect_transformed_vertices(transform_shape->getChildShape(), combined_transform, vertices);
            }

        case HK_SHAPE_CONVEX_TRANSFORM:
            {
                const hkpConvexTransformShape* transform_shape = static_cast<const hkpConvexTransformShape*>(shape);
                hkTransform combined_transform;
                combined_transform.setMul(transform, transform_shape->getTransform());
                return collect_transformed_vertices(transform_shape->getChildShape(), combined_transform, vertices);
            }

        case HK_SHAPE_LIST:
            {
                const hkpListShape* list_shape = static_cast<const hkpListShape*>(shape);
                bool found = false;
                int child_index = 0;

                for (child_index = 0; child_index < list_shape->getNumChildShapes(); ++child_index)
                {
                    if (collect_transformed_vertices(list_shape->getChildShapeInl(child_index), transform, vertices))
                    {
                        found = true;
                    }
                }

                return found;
            }

        case HK_SHAPE_MOPP:
            return collect_transformed_vertices(static_cast<const hkpMoppBvTreeShape*>(shape)->getChild(), transform, vertices);

        default:
            return false;
        }
    }

    bool extract_direct_shape(const hkpShape* shape, const hkTransform& local_transform, ExtractedShape* result)
    {
        if (shape == HK_NULL || !result)
        {
            return false;
        }

        switch (shape->getType())
        {
        case HK_SHAPE_BOX:
            result->kind = ExtractedShape::KindBox;
            result->local_transform = local_transform;
            result->box_half_extents = static_cast<const hkpBoxShape*>(shape)->getHalfExtents();
            return true;

        case HK_SHAPE_SPHERE:
            result->kind = ExtractedShape::KindSphere;
            result->local_transform = local_transform;
            result->sphere_radius = static_cast<const hkpSphereShape*>(shape)->getRadius();
            return true;

        case HK_SHAPE_CONVEX_VERTICES:
            result->kind = ExtractedShape::KindConvexHull;
            result->local_transform = local_transform;
            result->shape_radius = static_cast<const hkpConvexVerticesShape*>(shape)->getRadius();
            return collect_original_convex_vertices(static_cast<const hkpConvexVerticesShape*>(shape), result->hull_vertices);

        case HK_SHAPE_CONVEX_TRANSLATE:
            {
                const hkpConvexTranslateShape* translate_shape = static_cast<const hkpConvexTranslateShape*>(shape);
                hkTransform translation_transform = make_translation_transform(translate_shape->getTranslation());
                hkTransform combined_transform;
                combined_transform.setMul(local_transform, translation_transform);
                return extract_direct_shape(translate_shape->getChildShape(), combined_transform, result);
            }

        case HK_SHAPE_TRANSFORM:
            {
                const hkpTransformShape* transform_shape = static_cast<const hkpTransformShape*>(shape);
                hkTransform combined_transform;
                combined_transform.setMul(local_transform, transform_shape->getTransform());
                return extract_direct_shape(transform_shape->getChildShape(), combined_transform, result);
            }

        case HK_SHAPE_CONVEX_TRANSFORM:
            {
                const hkpConvexTransformShape* transform_shape = static_cast<const hkpConvexTransformShape*>(shape);
                hkTransform combined_transform;
                combined_transform.setMul(local_transform, transform_shape->getTransform());
                return extract_direct_shape(transform_shape->getChildShape(), combined_transform, result);
            }

        default:
            return false;
        }
    }

    void compute_scale_from_vertices(const std::vector<ConvexHullVertex>& vertices, float scale[3])
    {
        std::size_t vertex_index = 0;
        float min_x = 0.0f;
        float max_x = 0.0f;
        float min_y = 0.0f;
        float max_y = 0.0f;
        float min_z = 0.0f;
        float max_z = 0.0f;

        if (vertices.empty())
        {
            scale[0] = 1.0f;
            scale[1] = 1.0f;
            scale[2] = 1.0f;
            return;
        }

        min_x = max_x = vertices[0].x;
        min_y = max_y = vertices[0].y;
        min_z = max_z = vertices[0].z;

        for (vertex_index = 1; vertex_index < vertices.size(); ++vertex_index)
        {
            const ConvexHullVertex& vertex = vertices[vertex_index];

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

        scale[0] = max_abs_component(min_x, max_x);
        scale[1] = max_abs_component(min_y, max_y);
        scale[2] = max_abs_component(min_z, max_z);

        if (scale[0] <= 0.001f)
        {
            scale[0] = 0.001f;
        }
        if (scale[1] <= 0.001f)
        {
            scale[1] = 0.001f;
        }
        if (scale[2] <= 0.001f)
        {
            scale[2] = 0.001f;
        }
    }

    bool import_rigid_body(const hkpRigidBody* rigid_body, ImportedPhysicsObject* imported_object)
    {
        const hkpShape* shape = 0;
        SpawnedObjectSceneSpec spec;
        ExtractedShape extracted_shape;
        hkTransform identity;
        hkTransform final_transform;
        hkQuaternion final_rotation;
        hkVector4 final_position;
        const char* rigid_body_name = 0;

        if (!rigid_body || !imported_object)
        {
            return false;
        }

        shape = rigid_body->getCollidable() ? rigid_body->getCollidable()->getShape() : HK_NULL;
        if (shape == HK_NULL)
        {
            return false;
        }

        spec.body_type = rigid_body->getMotionType() == hkpMotion::MOTION_FIXED
            ? SimulationController::BodyStatic
            : SimulationController::BodyDynamic;
        spec.restitution = rigid_body->getRestitution();
        spec.mass = spec.body_type == SimulationController::BodyDynamic ? rigid_body->getMass() : 0.0f;
        if (spec.body_type == SimulationController::BodyDynamic && spec.mass <= 0.0f)
        {
            spec.mass = 1.0f;
        }

        identity.setIdentity();
        if (extract_direct_shape(shape, identity, &extracted_shape))
        {
            final_transform.setMul(rigid_body->getTransform(), extracted_shape.local_transform);

            if (extracted_shape.kind == ExtractedShape::KindBox)
            {
                spec.object_type = SimulationController::ObjectCube;
                spec.scale[0] = extracted_shape.box_half_extents(0);
                spec.scale[1] = extracted_shape.box_half_extents(1);
                spec.scale[2] = extracted_shape.box_half_extents(2);
            }
            else if (extracted_shape.kind == ExtractedShape::KindSphere)
            {
                spec.object_type = SimulationController::ObjectSphere;
                spec.scale[0] = extracted_shape.sphere_radius;
                spec.scale[1] = extracted_shape.sphere_radius;
                spec.scale[2] = extracted_shape.sphere_radius;
            }
            else
            {
                spec.object_type = SimulationController::ObjectConvexHull;
                spec.shape_radius = extracted_shape.shape_radius;
                spec.convex_hull_vertices = extracted_shape.hull_vertices;
                compute_scale_from_vertices(spec.convex_hull_vertices, spec.scale);
            }
        }
        else
        {
            std::vector<ConvexHullVertex> hull_vertices;
            if (!collect_transformed_vertices(shape, identity, hull_vertices) || hull_vertices.empty())
            {
                return false;
            }

            final_transform = rigid_body->getTransform();
            spec.object_type = SimulationController::ObjectConvexHull;
            spec.shape_radius = extract_shape_radius(shape);
            spec.convex_hull_vertices = hull_vertices;
            compute_scale_from_vertices(spec.convex_hull_vertices, spec.scale);
        }

        final_rotation.set(final_transform.getRotation());
        final_position = final_transform.getTranslation();
        spec.position[0] = final_position(0);
        spec.position[1] = final_position(1);
        spec.position[2] = final_position(2);
        quaternion_to_euler_degrees(final_rotation, spec.rotation_degrees);

        rigid_body_name = rigid_body->getName();
        imported_object->name = (rigid_body_name && rigid_body_name[0] != '\0') ? rigid_body_name : "Rigid Body";
        imported_object->editable = spec.object_type != SimulationController::ObjectConvexHull;
        imported_object->object_spec = spec;
        return true;
    }
}

bool load_imported_physics_systems(
    const char* input_file,
    std::vector<ImportedPhysicsSystem>& systems_out,
    std::string* error_message)
{
    LoadedPhysicsSnapshot snapshot;
    hkpPhysicsData* physics_data = HK_NULL;
    const hkArray<hkpPhysicsSystem*>* physics_systems = 0;
    bool found_objects = false;
    int system_index = 0;

    systems_out.clear();

    if (!input_file || input_file[0] == '\0')
    {
        if (error_message)
        {
            *error_message = "Choose a physics HKX file to import.";
        }
        return false;
    }

    physics_data = snapshot.load(input_file);
    if (physics_data == HK_NULL)
    {
        if (error_message)
        {
            *error_message = "Could not load Havok physics data from the selected HKX file.";
        }
        return false;
    }

    physics_systems = &physics_data->getPhysicsSystems();
    if (physics_systems->getSize() <= 0)
    {
        if (error_message)
        {
            *error_message = "No physics systems were found in the selected HKX file.";
        }
        return false;
    }

    for (system_index = 0; system_index < physics_systems->getSize(); ++system_index)
    {
        const hkpPhysicsSystem* physics_system = (*physics_systems)[system_index];
        ImportedPhysicsSystem imported_system;
        const hkArray<hkpRigidBody*>* rigid_bodies = 0;
        const char* system_name = 0;
        int rigid_body_index = 0;

        if (physics_system == HK_NULL)
        {
            continue;
        }

        system_name = physics_system->getName();
        imported_system.name = (system_name && system_name[0] != '\0') ? system_name : "Physics System";
        rigid_bodies = &physics_system->getRigidBodies();
        for (rigid_body_index = 0; rigid_body_index < rigid_bodies->getSize(); ++rigid_body_index)
        {
            ImportedPhysicsObject imported_object;
            if (import_rigid_body((*rigid_bodies)[rigid_body_index], &imported_object))
            {
                imported_system.objects.push_back(imported_object);
                found_objects = true;
            }
            else
            {
                ++imported_system.skipped_body_count;
            }
        }

        systems_out.push_back(imported_system);
    }

    if (!found_objects)
    {
        if (error_message)
        {
            *error_message = "The selected HKX file did not contain any importable box, sphere, or convex-hull rigid bodies.";
        }
        return false;
    }

    return true;
}