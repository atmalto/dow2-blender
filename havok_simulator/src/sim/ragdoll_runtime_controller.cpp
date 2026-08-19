#include "ragdoll_runtime_controller.h"

#include <cmath>

#include <Common/Base/Math/QsTransform/hkQsTransform.h>

#include <Animation/Animation/Rig/hkaSkeletonUtils.h>
#include <Animation/Ragdoll/Controller/RigidBody/hkaRagdollRigidBodyController.h>
#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>

#include <Physics/Dynamics/Entity/hkpRigidBody.h>

namespace
{
    void zero_stress_output(hkArray<hkaKeyFrameHierarchyUtility::Output>& stress_output)
    {
        for (int output_index = 0; output_index < stress_output.getSize(); ++output_index)
        {
            stress_output[output_index].m_stressSquared = 0.0f;
        }
    }

    float max_stress_value(const hkArray<hkaKeyFrameHierarchyUtility::Output>& stress_output, int* bone_index)
    {
        float max_stress_squared = 0.0f;
        int max_index = -1;

        for (int output_index = 0; output_index < stress_output.getSize(); ++output_index)
        {
            if (stress_output[output_index].m_stressSquared > max_stress_squared)
            {
                max_stress_squared = stress_output[output_index].m_stressSquared;
                max_index = output_index;
            }
        }

        if (bone_index)
        {
            *bone_index = max_index;
        }

        return max_stress_squared > 0.0f ? static_cast<float>(std::sqrt(max_stress_squared)) : 0.0f;
    }
}

RagdollRuntimeController::RagdollRuntimeController()
    : m_ragdoll_instance(0)
    , m_controller(0)
    , m_is_holding(false)
    , m_impact_release_speed(3.0f)
{
    m_base_world_from_model.setIdentity();
    m_world_from_model.setIdentity();
}

RagdollRuntimeController::~RagdollRuntimeController()
{
    shutdown();
}

bool RagdollRuntimeController::initialize(hkaRagdollInstance* ragdoll_instance)
{
    hkArray<hkQsTransform> pose_world_space;
    const int bone_count = ragdoll_instance ? ragdoll_instance->getNumBones() : 0;

    shutdown();

    if (!ragdoll_instance || bone_count <= 0)
    {
        return false;
    }

    m_ragdoll_instance = ragdoll_instance;
    pose_world_space.setSize(bone_count);
    m_authored_pose_world_space.setSize(bone_count);
    m_target_pose_local_space.setSize(bone_count);
    m_stress_output.setSize(bone_count);

    m_ragdoll_instance->getPoseWorldSpace(pose_world_space.begin());
    for (int bone_index = 0; bone_index < bone_count; ++bone_index)
    {
        m_authored_pose_world_space[bone_index] = pose_world_space[bone_index];
    }
    m_base_world_from_model = pose_world_space[0];
    m_world_from_model = m_base_world_from_model;
    hkaSkeletonUtils::transformWorldPoseToLocalPose(
        bone_count,
        m_ragdoll_instance->getSkeleton()->m_parentIndices,
        m_base_world_from_model,
        pose_world_space.begin(),
        m_target_pose_local_space.begin());

    m_controller = new hkaRagdollRigidBodyController(m_ragdoll_instance);
    configure_control_data();
    zero_stress_output(m_stress_output);
    m_is_holding = true;
    reset_diagnostics();
    m_diagnostics.is_holding = true;
    m_controller->reinitialize();
    return true;
}

void RagdollRuntimeController::shutdown()
{
    if (m_controller)
    {
        delete m_controller;
        m_controller = 0;
    }

    m_ragdoll_instance = 0;
    m_authored_pose_world_space.clear();
    m_target_pose_local_space.clear();
    m_stress_output.clear();
    m_base_world_from_model.setIdentity();
    m_world_from_model.setIdentity();
    m_is_holding = false;
    reset_diagnostics();
}

void RagdollRuntimeController::set_world_from_model_position(const float position[3])
{
    hkVector4 translation_offset;

    if (!position)
    {
        return;
    }

    m_world_from_model = m_base_world_from_model;
    translation_offset.set(position[0], position[1], position[2]);
    m_world_from_model.m_translation.add4(translation_offset);
}

void RagdollRuntimeController::apply_pose_immediately()
{
    hkArray<hkQsTransform> pose_world_space;
    hkVector4 translation_offset;

    if (!m_ragdoll_instance || m_authored_pose_world_space.getSize() <= 0)
    {
        return;
    }

    pose_world_space.setSize(m_authored_pose_world_space.getSize());
    translation_offset.setSub4(m_world_from_model.m_translation, m_base_world_from_model.m_translation);

    for (int bone_index = 0; bone_index < m_authored_pose_world_space.getSize(); ++bone_index)
    {
        pose_world_space[bone_index] = m_authored_pose_world_space[bone_index];
        pose_world_space[bone_index].m_translation.add4(translation_offset);
    }

    m_ragdoll_instance->setPoseWorldSpace(pose_world_space.begin());

    if (m_controller)
    {
        m_controller->reinitialize();
    }
}

void RagdollRuntimeController::hold()
{
    m_is_holding = true;
    m_diagnostics.is_holding = true;

    if (m_controller)
    {
        m_controller->reinitialize();
    }
}

void RagdollRuntimeController::release()
{
    m_is_holding = false;
    m_diagnostics.is_holding = false;
}

bool RagdollRuntimeController::is_holding() const
{
    return m_is_holding;
}

void RagdollRuntimeController::set_impact_release_speed(float speed)
{
    m_impact_release_speed = speed;
}

float RagdollRuntimeController::impact_release_speed() const
{
    return m_impact_release_speed;
}

float RagdollRuntimeController::max_bone_linear_speed() const
{
    float max_speed = 0.0f;
    int bone_count = 0;
    int bone_index = 0;

    if (!m_ragdoll_instance)
    {
        return 0.0f;
    }

    bone_count = m_ragdoll_instance->getNumBones();
    for (bone_index = 0; bone_index < bone_count; ++bone_index)
    {
        const hkpRigidBody* rigid_body = m_ragdoll_instance->getRigidBodyOfBone(bone_index);
        float speed = 0.0f;

        if (!rigid_body)
        {
            continue;
        }

        const hkVector4& velocity = rigid_body->getLinearVelocity();
        speed = std::sqrt(velocity(0) * velocity(0) + velocity(1) * velocity(1) + velocity(2) * velocity(2));
        if (speed > max_speed)
        {
            max_speed = speed;
        }
    }

    return max_speed;
}

const RagdollRuntimeDiagnostics& RagdollRuntimeController::diagnostics() const
{
    return m_diagnostics;
}

void RagdollRuntimeController::step(hkReal delta_time)
{
    if (!m_is_holding || !m_controller || m_target_pose_local_space.getSize() <= 0)
    {
        return;
    }

    // Impact detection: driveToPose only ever drives bones up to its own clamped
    // velocities (positionMaxLinearVelocity 1.4 + snap 0.3 ~= 1.7 m/s). Any bone
    // moving faster than that at the start of a step carries an external impulse
    // from a collision or force during the previous world step. When that happens
    // we stop driving to the authored pose and let the ragdoll go fully dynamic so
    // the shove actually lands (Havok User Guide 4.4.1.6 "switch all bodies to
    // dynamic"; 5.1.5.1 "stop driving by just not calling driveToPose()").
    if (m_impact_release_speed > 0.0f && max_bone_linear_speed() > m_impact_release_speed)
    {
        release();
        return;
    }

    zero_stress_output(m_stress_output);
    m_controller->driveToPose(
        delta_time,
        m_target_pose_local_space.begin(),
        m_world_from_model,
        m_stress_output.begin());
    update_diagnostics();
}

void RagdollRuntimeController::configure_control_data()
{
    hkaKeyFrameHierarchyUtility::ControlData* control_data = 0;
    int body_index = 0;

    m_controller->m_controlDataPalette.setSize(1);
    control_data = &m_controller->m_controlDataPalette[0];

    *control_data = hkaKeyFrameHierarchyUtility::ControlData();
    control_data->m_velocityDamping = 0.0f;
    control_data->m_accelerationGain = 1.0f;
    control_data->m_velocityGain = 0.6f;
    control_data->m_positionGain = 0.05f;
    control_data->m_positionMaxLinearVelocity = 1.4f;
    control_data->m_positionMaxAngularVelocity = 1.8f;
    control_data->m_snapGain = 0.1f;
    control_data->m_snapMaxLinearVelocity = 0.3f;
    control_data->m_snapMaxAngularVelocity = 0.3f;
    control_data->m_snapMaxLinearDistance = 0.03f;
    control_data->m_snapMaxAngularDistance = 0.1f;

    m_controller->m_bodyIndexToPaletteIndex.setSize(m_target_pose_local_space.getSize());
    for (body_index = 0; body_index < m_controller->m_bodyIndexToPaletteIndex.getSize(); ++body_index)
    {
        m_controller->m_bodyIndexToPaletteIndex[body_index] = 0;
    }
}

void RagdollRuntimeController::reset_diagnostics()
{
    m_diagnostics = RagdollRuntimeDiagnostics();
    m_diagnostics.is_holding = m_is_holding;
}

void RagdollRuntimeController::update_diagnostics()
{
    m_diagnostics.is_holding = m_is_holding;
    m_diagnostics.max_stress = max_stress_value(m_stress_output, &m_diagnostics.max_stress_bone_index);
}