#include "ragdoll_preview_data.h"

#include <Common/Base/hkBase.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Animation/Animation/hkaAnimationContainer.h>
#include <Animation/Animation/Rig/hkaSkeleton.h>
#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>

#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Math/QsTransform/hkQsTransform.h>

#include <Physics/Collide/Shape/Convex/Box/hkpBoxShape.h>
#include <Physics/Collide/Shape/Convex/Capsule/hkpCapsuleShape.h>
#include <Physics/Collide/Shape/Convex/Sphere/hkpSphereShape.h>
#include <Physics/Collide/Shape/hkpShapeType.h>
#include <Physics/ConstraintSolver/Constraint/Atom/hkpConstraintAtom.h>
#include <Physics/Dynamics/Constraint/Bilateral/LimitedHinge/hkpLimitedHingeConstraintData.h>
#include <Physics/Dynamics/Constraint/Bilateral/Ragdoll/hkpRagdollConstraintData.h>
#include <Physics/Dynamics/Constraint/hkpConstraintData.h>
#include <Physics/Dynamics/Constraint/hkpConstraintInstance.h>
#include <Physics/Dynamics/Entity/hkpRigidBody.h>

namespace
{
    const char* safe_name(const char* value, const char* fallback)
    {
        return value && value[0] ? value : fallback;
    }

    void initialize_render_state(BodyRenderState* state, bool is_dynamic, bool is_solid, bool is_preview)
    {
        if (!state)
        {
            return;
        }

        state->is_dynamic = is_dynamic;
        state->is_solid = is_solid;
        state->is_preview = is_preview;
        state->entity_id = 0;
        state->entity_kind = SceneEntityKindNone;
        state->is_selected = false;
        state->position[0] = 0.0f;
        state->position[1] = 0.0f;
        state->position[2] = 0.0f;
        state->rotation[0] = 0.0f;
        state->rotation[1] = 0.0f;
        state->rotation[2] = 0.0f;
        state->rotation[3] = 1.0f;
        state->half_extents[0] = 0.0f;
        state->half_extents[1] = 0.0f;
        state->half_extents[2] = 0.0f;
        state->capsule_vertices[0] = 0.0f;
        state->capsule_vertices[1] = 0.0f;
        state->capsule_vertices[2] = 0.0f;
        state->capsule_vertices[3] = 0.0f;
        state->capsule_vertices[4] = 0.0f;
        state->capsule_vertices[5] = 0.0f;
        state->radius = 0.0f;
        state->color[0] = 0.0f;
        state->color[1] = 0.0f;
        state->color[2] = 0.0f;
        state->mesh_vertices.clear();
    }

    void set_render_color(BodyRenderState* state, float red, float green, float blue)
    {
        if (!state)
        {
            return;
        }

        state->color[0] = red;
        state->color[1] = green;
        state->color[2] = blue;
    }

    void copy_vector3(const hkVector4& value, float output[3])
    {
        output[0] = value(0);
        output[1] = value(1);
        output[2] = value(2);
    }

    void copy_rotation_columns(const hkTransform& transform, float twist_axis[3], float plane_axis[3])
    {
        copy_vector3(transform.getRotation().getColumn(0), twist_axis);
        copy_vector3(transform.getRotation().getColumn(1), plane_axis);
    }

    void copy_quaternion(const hkQuaternion& quaternion, float output[4])
    {
        output[0] = quaternion(0);
        output[1] = quaternion(1);
        output[2] = quaternion(2);
        output[3] = quaternion(3);
    }

    void copy_transform(const hkQsTransform& transform, float translation[3], float rotation[4], float scale[3])
    {
        translation[0] = transform.m_translation(0);
        translation[1] = transform.m_translation(1);
        translation[2] = transform.m_translation(2);
        rotation[0] = transform.m_rotation(0);
        rotation[1] = transform.m_rotation(1);
        rotation[2] = transform.m_rotation(2);
        rotation[3] = transform.m_rotation(3);
        scale[0] = transform.m_scale(0);
        scale[1] = transform.m_scale(1);
        scale[2] = transform.m_scale(2);
    }

    const hkaSkeleton* find_animation_skeleton(const hkRootLevelContainer& container, const hkaSkeleton* ragdoll_skeleton)
    {
        const hkaAnimationContainer* animation_container = static_cast<const hkaAnimationContainer*>(
            container.findObjectByType(hkaAnimationContainerClass.getName()));
        const hkaSkeleton* best_skeleton = 0;
        int best_bone_count = -1;

        if (animation_container)
        {
            for (int skeleton_index = 0; skeleton_index < animation_container->m_numSkeletons; ++skeleton_index)
            {
                const hkaSkeleton* skeleton = animation_container->m_skeletons[skeleton_index];
                if (!skeleton || skeleton == ragdoll_skeleton)
                {
                    continue;
                }

                if (skeleton->m_numBones > best_bone_count)
                {
                    best_skeleton = skeleton;
                    best_bone_count = skeleton->m_numBones;
                }
            }
        }

        if (best_skeleton)
        {
            return best_skeleton;
        }

        const void* previous_object = 0;
        while (const void* object = container.findObjectByType(hkaSkeletonClass.getName(), previous_object))
        {
            const hkaSkeleton* skeleton = static_cast<const hkaSkeleton*>(object);
            previous_object = object;

            if (!skeleton || skeleton == ragdoll_skeleton)
            {
                continue;
            }

            if (skeleton->m_numBones > best_bone_count)
            {
                best_skeleton = skeleton;
                best_bone_count = skeleton->m_numBones;
            }
        }

        return best_skeleton;
    }

    bool build_reference_skeleton_preview(const hkaSkeleton& skeleton, std::vector<RagdollPreviewBone>* bones)
    {
        hkArray<hkQsTransform> world_pose;

        if (!bones || skeleton.m_numBones <= 0 || !skeleton.m_referencePose || !skeleton.m_parentIndices)
        {
            return false;
        }

        bones->clear();
        bones->resize(skeleton.m_numBones);
        world_pose.setSize(skeleton.m_numBones);

        for (int bone_index = 0; bone_index < skeleton.m_numBones; ++bone_index)
        {
            const int parent_index = skeleton.m_parentIndices[bone_index];

            if (parent_index >= 0 && parent_index < bone_index)
            {
                world_pose[bone_index].setMul(world_pose[parent_index], skeleton.m_referencePose[bone_index]);
            }
            else
            {
                world_pose[bone_index] = skeleton.m_referencePose[bone_index];
            }

            RagdollPreviewBone& bone = (*bones)[bone_index];
            bone.bone_index = bone_index;
            bone.parent_index = parent_index;
            bone.name = skeleton.m_bones && skeleton.m_bones[bone_index]
                ? safe_name(skeleton.m_bones[bone_index]->m_name, "Bone")
                : "Bone";
            copy_transform(world_pose[bone_index], bone.translation, bone.rotation, bone.scale);
        }

        return true;
    }

    RagdollPreviewBodyShapeType preview_shape_type_from_havok(hkpShapeType shape_type)
    {
        switch (shape_type)
        {
        case HK_SHAPE_SPHERE:
            return RagdollPreviewBodyShapeSphere;
        case HK_SHAPE_CAPSULE:
            return RagdollPreviewBodyShapeCapsule;
        case HK_SHAPE_BOX:
            return RagdollPreviewBodyShapeBox;
        default:
            return RagdollPreviewBodyShapeUnknown;
        }
    }

    bool build_render_state_from_body(const hkpRigidBody& rigid_body, BodyRenderState* render_state)
    {
        const hkpShape* shape = rigid_body.getCollidable()->getShape();

        if (!shape || !render_state)
        {
            return false;
        }

        switch (shape->getType())
        {
        case HK_SHAPE_BOX:
            {
                const hkpBoxShape* box_shape = static_cast<const hkpBoxShape*>(shape);
                const hkVector4& half_extents = box_shape->getHalfExtents();
                render_state->shape_type = BodyRenderState::ShapeBox;
                initialize_render_state(render_state, true, true, false);
                render_state->half_extents[0] = half_extents(0);
                render_state->half_extents[1] = half_extents(1);
                render_state->half_extents[2] = half_extents(2);
                set_render_color(render_state, 0.95f, 0.74f, 0.32f);
                return true;
            }
        case HK_SHAPE_SPHERE:
            {
                const hkpSphereShape* sphere_shape = static_cast<const hkpSphereShape*>(shape);
                const float radius = sphere_shape->getRadius();
                render_state->shape_type = BodyRenderState::ShapeSphere;
                initialize_render_state(render_state, true, true, false);
                render_state->half_extents[0] = radius;
                render_state->half_extents[1] = radius;
                render_state->half_extents[2] = radius;
                render_state->radius = radius;
                set_render_color(render_state, 0.48f, 0.83f, 0.92f);
                return true;
            }
        case HK_SHAPE_CAPSULE:
            {
                const hkpCapsuleShape* capsule_shape = static_cast<const hkpCapsuleShape*>(shape);
                render_state->shape_type = BodyRenderState::ShapeCapsule;
                initialize_render_state(render_state, true, false, false);
                render_state->radius = capsule_shape->getRadius();
                render_state->capsule_vertices[0] = capsule_shape->getVertex(0)(0);
                render_state->capsule_vertices[1] = capsule_shape->getVertex(0)(1);
                render_state->capsule_vertices[2] = capsule_shape->getVertex(0)(2);
                render_state->capsule_vertices[3] = capsule_shape->getVertex(1)(0);
                render_state->capsule_vertices[4] = capsule_shape->getVertex(1)(1);
                render_state->capsule_vertices[5] = capsule_shape->getVertex(1)(2);
                render_state->half_extents[0] = render_state->radius;
                render_state->half_extents[1] = render_state->radius;
                render_state->half_extents[2] = render_state->radius;
                set_render_color(render_state, 0.89f, 0.53f, 0.25f);
                return true;
            }
        default:
            return false;
        }
    }

    void fill_render_transform(const hkpRigidBody& rigid_body, BodyRenderState* render_state)
    {
        if (!render_state)
        {
            return;
        }

        render_state->position[0] = rigid_body.getPosition()(0);
        render_state->position[1] = rigid_body.getPosition()(1);
        render_state->position[2] = rigid_body.getPosition()(2);
        render_state->rotation[0] = rigid_body.getRotation()(0);
        render_state->rotation[1] = rigid_body.getRotation()(1);
        render_state->rotation[2] = rigid_body.getRotation()(2);
        render_state->rotation[3] = rigid_body.getRotation()(3);
    }
}

bool build_ragdoll_preview_data(
    SceneEntityId entity_id,
    const char* asset_path,
    const hkRootLevelContainer& container,
    const hkaRagdollInstance& instance,
    RagdollPreviewData* preview_data)
{
    const hkaSkeleton* skeleton = instance.getSkeleton();
    const hkaSkeleton* animation_skeleton = find_animation_skeleton(container, skeleton);
    hkArray<hkQsTransform> pose_world_space;
    int bone_index = 0;

    if (!preview_data || !skeleton)
    {
        return false;
    }

    preview_data->entity_id = entity_id;
    preview_data->asset_path = asset_path ? asset_path : "";
    preview_data->skeleton_name = safe_name(skeleton->m_name, "Skeleton");
    preview_data->bones.clear();
    preview_data->bodies.clear();
    preview_data->joints.clear();
    preview_data->animation_skeleton_name = animation_skeleton ? safe_name(animation_skeleton->m_name, "Animation Skeleton") : "";
    preview_data->animation_bones.clear();

    if (animation_skeleton)
    {
        build_reference_skeleton_preview(*animation_skeleton, &preview_data->animation_bones);
    }

    pose_world_space.setSize(instance.getNumBones());
    instance.getPoseWorldSpace(pose_world_space.begin());

    preview_data->bones.resize(instance.getNumBones());
    preview_data->bodies.resize(instance.getNumBones());
    preview_data->joints.resize(instance.getNumBones());

    for (bone_index = 0; bone_index < instance.getNumBones(); ++bone_index)
    {
        const int parent_index = instance.getParentOfBone(bone_index);
        const char* bone_name = skeleton->m_bones && skeleton->m_bones[bone_index]
            ? safe_name(skeleton->m_bones[bone_index]->m_name, "Bone")
            : "Bone";
        RagdollPreviewBone& bone = preview_data->bones[bone_index];
        RagdollPreviewBody& body = preview_data->bodies[bone_index];
        RagdollPreviewJoint& joint = preview_data->joints[bone_index];
        hkpRigidBody* rigid_body = instance.getRigidBodyOfBone(bone_index);
        hkpConstraintInstance* constraint = instance.getConstraintOfBone(bone_index);

        bone.bone_index = bone_index;
        bone.parent_index = parent_index;
        bone.name = bone_name;
        bone.translation[0] = pose_world_space[bone_index].m_translation(0);
        bone.translation[1] = pose_world_space[bone_index].m_translation(1);
        bone.translation[2] = pose_world_space[bone_index].m_translation(2);
        bone.rotation[0] = pose_world_space[bone_index].m_rotation(0);
        bone.rotation[1] = pose_world_space[bone_index].m_rotation(1);
        bone.rotation[2] = pose_world_space[bone_index].m_rotation(2);
        bone.rotation[3] = pose_world_space[bone_index].m_rotation(3);
        bone.scale[0] = pose_world_space[bone_index].m_scale(0);
        bone.scale[1] = pose_world_space[bone_index].m_scale(1);
        bone.scale[2] = pose_world_space[bone_index].m_scale(2);

        if (rigid_body)
        {
            const hkpShape* shape = rigid_body->getCollidable()->getShape();
            body.is_present = true;
            body.bone_index = bone_index;
            body.name = bone_name;
            body.shape_type = shape ? preview_shape_type_from_havok(shape->getType()) : RagdollPreviewBodyShapeUnknown;
            body.mass = rigid_body->getMass();
            body.friction = rigid_body->getFriction();
            body.restitution = rigid_body->getRestitution();
            body.motion_type = static_cast<int>(rigid_body->getMotionType());
            body.linear_damping = rigid_body->getLinearDamping();
            body.angular_damping = rigid_body->getAngularDamping();
            body.collision_filter_info = rigid_body->getCollisionFilterInfo();
            body.quality_type = static_cast<int>(rigid_body->getQualityType());

            if (shape)
            {
                if (shape->getType() == HK_SHAPE_CAPSULE)
                {
                    const hkpCapsuleShape* capsule_shape = static_cast<const hkpCapsuleShape*>(shape);
                    body.radius = capsule_shape->getRadius();
                    body.capsule_vertices[0] = capsule_shape->getVertex(0)(0);
                    body.capsule_vertices[1] = capsule_shape->getVertex(0)(1);
                    body.capsule_vertices[2] = capsule_shape->getVertex(0)(2);
                    body.capsule_vertices[3] = capsule_shape->getVertex(1)(0);
                    body.capsule_vertices[4] = capsule_shape->getVertex(1)(1);
                    body.capsule_vertices[5] = capsule_shape->getVertex(1)(2);
                }
                else if (shape->getType() == HK_SHAPE_BOX)
                {
                    const hkpBoxShape* box_shape = static_cast<const hkpBoxShape*>(shape);
                    body.half_extents[0] = box_shape->getHalfExtents()(0);
                    body.half_extents[1] = box_shape->getHalfExtents()(1);
                    body.half_extents[2] = box_shape->getHalfExtents()(2);
                }
                else if (shape->getType() == HK_SHAPE_SPHERE)
                {
                    const hkpSphereShape* sphere_shape = static_cast<const hkpSphereShape*>(shape);
                    body.radius = sphere_shape->getRadius();
                }
            }

            body.has_render_state = build_render_state_from_body(*rigid_body, &body.render_state);
            if (body.has_render_state)
            {
                body.render_state.entity_id = entity_id;
                body.render_state.entity_kind = SceneEntityKindRagdoll;
                fill_render_transform(*rigid_body, &body.render_state);
            }

            body.position[0] = rigid_body->getPosition()(0);
            body.position[1] = rigid_body->getPosition()(1);
            body.position[2] = rigid_body->getPosition()(2);
            copy_quaternion(rigid_body->getRotation(), body.rotation);
        }

        if (constraint)
        {
            const hkpConstraintData* constraint_data = constraint->getData();
            joint.is_present = true;
            joint.bone_index = bone_index;
            joint.parent_bone_index = parent_index;
            joint.name = safe_name(constraint->getName(), bone_name);
            joint.child_name = bone_name;
            joint.parent_name = parent_index >= 0 && parent_index < instance.getNumBones()
                ? preview_data->bones[parent_index].name
                : "";

            if (constraint_data)
            {
                switch (constraint_data->getType())
                {
                case hkpConstraintData::CONSTRAINT_TYPE_RAGDOLL:
                    {
                        const hkpRagdollConstraintData* ragdoll_data = static_cast<const hkpRagdollConstraintData*>(constraint_data);
                        joint.constraint_type = RagdollPreviewConstraintRagdoll;
                        copy_vector3(ragdoll_data->m_atoms.m_transforms.m_transformA.getTranslation(), joint.pivot_a);
                        copy_vector3(ragdoll_data->m_atoms.m_transforms.m_transformB.getTranslation(), joint.pivot_b);
                        copy_rotation_columns(ragdoll_data->m_atoms.m_transforms.m_transformA, joint.twist_axis_a, joint.plane_axis_a);
                        copy_rotation_columns(ragdoll_data->m_atoms.m_transforms.m_transformB, joint.twist_axis_b, joint.plane_axis_b);
                        joint.twist_min_radians = ragdoll_data->getTwistMinAngularLimit();
                        joint.twist_max_radians = ragdoll_data->getTwistMaxAngularLimit();
                        joint.cone_angle_radians = ragdoll_data->getConeAngularLimit();
                        joint.plane_min_radians = ragdoll_data->getPlaneMinAngularLimit();
                        joint.plane_max_radians = ragdoll_data->getPlaneMaxAngularLimit();
                        joint.friction_torque = ragdoll_data->getMaxFrictionTorque();
                        break;
                    }
                case hkpConstraintData::CONSTRAINT_TYPE_LIMITEDHINGE:
                case hkpConstraintData::CONSTRAINT_TYPE_HINGE_LIMITS:
                    {
                        const hkpLimitedHingeConstraintData* hinge_data = static_cast<const hkpLimitedHingeConstraintData*>(constraint_data);
                        joint.constraint_type = RagdollPreviewConstraintLimitedHinge;
                        copy_vector3(hinge_data->m_atoms.m_transforms.m_transformA.getTranslation(), joint.pivot_a);
                        copy_vector3(hinge_data->m_atoms.m_transforms.m_transformB.getTranslation(), joint.pivot_b);
                        copy_rotation_columns(hinge_data->m_atoms.m_transforms.m_transformA, joint.twist_axis_a, joint.plane_axis_a);
                        copy_rotation_columns(hinge_data->m_atoms.m_transforms.m_transformB, joint.twist_axis_b, joint.plane_axis_b);
                        joint.hinge_min_radians = hinge_data->getMinAngularLimit();
                        joint.hinge_max_radians = hinge_data->getMaxAngularLimit();
                        joint.friction_torque = hinge_data->getMaxFrictionTorque();
                        break;
                    }
                default:
                    joint.constraint_type = RagdollPreviewConstraintUnknown;
                    break;
                }
            }
            else
            {
                joint.constraint_type = RagdollPreviewConstraintUnknown;
            }
        }
    }

    return true;
}

const char* ragdoll_preview_body_shape_label(RagdollPreviewBodyShapeType type)
{
    switch (type)
    {
    case RagdollPreviewBodyShapeSphere:
        return "sphere";
    case RagdollPreviewBodyShapeCapsule:
        return "capsule";
    case RagdollPreviewBodyShapeBox:
        return "box";
    case RagdollPreviewBodyShapeUnknown:
        return "unknown";
    default:
        return "none";
    }
}

const char* ragdoll_preview_constraint_type_label(RagdollPreviewConstraintType type)
{
    switch (type)
    {
    case RagdollPreviewConstraintRagdoll:
        return "ragdoll";
    case RagdollPreviewConstraintLimitedHinge:
        return "limited_hinge";
    case RagdollPreviewConstraintUnknown:
        return "unknown";
    default:
        return "none";
    }
}

const char* ragdoll_preview_motion_type_label(int motion_type)
{
    switch (motion_type)
    {
    case hkpMotion::MOTION_DYNAMIC:
        return "MOTION_DYNAMIC";
    case hkpMotion::MOTION_SPHERE_INERTIA:
        return "MOTION_SPHERE_INERTIA";
    case hkpMotion::MOTION_BOX_INERTIA:
        return "MOTION_BOX_INERTIA";
    case hkpMotion::MOTION_KEYFRAMED:
        return "MOTION_KEYFRAMED";
    case hkpMotion::MOTION_FIXED:
        return "MOTION_FIXED";
    case hkpMotion::MOTION_THIN_BOX_INERTIA:
        return "MOTION_THIN_BOX_INERTIA";
    default:
        return "MOTION_UNKNOWN";
    }
}