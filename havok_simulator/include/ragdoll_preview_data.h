#ifndef HAVOK_SCENE_APP_RAGDOLL_PREVIEW_DATA_H
#define HAVOK_SCENE_APP_RAGDOLL_PREVIEW_DATA_H

#include <string>
#include <vector>

#include "body_render_state.h"
#include "scene_entity.h"

class hkaRagdollInstance;
class hkRootLevelContainer;

enum RagdollPreviewSkeletonKind
{
    RagdollPreviewSkeletonAnimation = 0,
    RagdollPreviewSkeletonRagdoll
};

enum RagdollPreviewBodyShapeType
{
    RagdollPreviewBodyShapeNone = 0,
    RagdollPreviewBodyShapeSphere,
    RagdollPreviewBodyShapeCapsule,
    RagdollPreviewBodyShapeBox,
    RagdollPreviewBodyShapeUnknown
};

enum RagdollPreviewConstraintType
{
    RagdollPreviewConstraintNone = 0,
    RagdollPreviewConstraintRagdoll,
    RagdollPreviewConstraintLimitedHinge,
    RagdollPreviewConstraintUnknown
};

struct RagdollPreviewBone
{
    RagdollPreviewBone()
        : bone_index(-1)
        , parent_index(-1)
    {
        translation[0] = translation[1] = translation[2] = 0.0f;
        rotation[0] = rotation[1] = rotation[2] = 0.0f;
        rotation[3] = 1.0f;
        scale[0] = scale[1] = scale[2] = 1.0f;
    }

    int bone_index;
    int parent_index;
    std::string name;
    float translation[3];
    float rotation[4];
    float scale[3];
};

struct RagdollPreviewBody
{
    RagdollPreviewBody()
        : is_present(false)
        , has_render_state(false)
        , bone_index(-1)
        , shape_type(RagdollPreviewBodyShapeNone)
        , mass(0.0f)
        , friction(0.0f)
        , restitution(0.0f)
        , motion_type(0)
        , linear_damping(0.0f)
        , angular_damping(0.0f)
        , collision_filter_info(0u)
        , quality_type(0)
    {
        int index = 0;
        radius = 0.0f;
        for (index = 0; index < 6; ++index)
        {
            capsule_vertices[index] = 0.0f;
        }
        for (index = 0; index < 3; ++index)
        {
            half_extents[index] = 0.0f;
            position[index] = 0.0f;
        }
        rotation[0] = rotation[1] = rotation[2] = 0.0f;
        rotation[3] = 1.0f;
    }

    bool is_present;
    bool has_render_state;
    int bone_index;
    std::string name;
    RagdollPreviewBodyShapeType shape_type;
    float radius;
    float capsule_vertices[6];
    float half_extents[3];
    float position[3];
    float rotation[4];
    float mass;
    float friction;
    float restitution;
    int motion_type;
    float linear_damping;
    float angular_damping;
    unsigned int collision_filter_info;
    int quality_type;
    BodyRenderState render_state;
};

struct RagdollPreviewJoint
{
    RagdollPreviewJoint()
        : is_present(false)
        , bone_index(-1)
        , parent_bone_index(-1)
        , constraint_type(RagdollPreviewConstraintNone)
        , twist_min_radians(0.0f)
        , twist_max_radians(0.0f)
        , cone_angle_radians(0.0f)
        , plane_min_radians(0.0f)
        , plane_max_radians(0.0f)
        , hinge_min_radians(0.0f)
        , hinge_max_radians(0.0f)
        , friction_torque(0.0f)
    {
        int index = 0;
        for (index = 0; index < 3; ++index)
        {
            pivot_a[index] = 0.0f;
            pivot_b[index] = 0.0f;
            twist_axis_a[index] = 0.0f;
            twist_axis_b[index] = 0.0f;
            plane_axis_a[index] = 0.0f;
            plane_axis_b[index] = 0.0f;
        }
    }

    bool is_present;
    int bone_index;
    int parent_bone_index;
    std::string name;
    std::string parent_name;
    std::string child_name;
    RagdollPreviewConstraintType constraint_type;
    float pivot_a[3];
    float pivot_b[3];
    float twist_axis_a[3];
    float twist_axis_b[3];
    float plane_axis_a[3];
    float plane_axis_b[3];
    float twist_min_radians;
    float twist_max_radians;
    float cone_angle_radians;
    float plane_min_radians;
    float plane_max_radians;
    float hinge_min_radians;
    float hinge_max_radians;
    float friction_torque;
};

struct RagdollPreviewData
{
    RagdollPreviewData()
        : entity_id(0)
    {
    }

    SceneEntityId entity_id;
    std::string asset_path;
    std::string skeleton_name;
    std::vector<RagdollPreviewBone> bones;
    std::vector<RagdollPreviewBody> bodies;
    std::vector<RagdollPreviewJoint> joints;
    std::string animation_skeleton_name;
    std::vector<RagdollPreviewBone> animation_bones;
};

bool build_ragdoll_preview_data(
    SceneEntityId entity_id,
    const char* asset_path,
    const hkRootLevelContainer& container,
    const hkaRagdollInstance& instance,
    RagdollPreviewData* preview_data);

const char* ragdoll_preview_body_shape_label(RagdollPreviewBodyShapeType type);
const char* ragdoll_preview_constraint_type_label(RagdollPreviewConstraintType type);
const char* ragdoll_preview_motion_type_label(int motion_type);

#endif