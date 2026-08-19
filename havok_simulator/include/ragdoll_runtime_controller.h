#ifndef HAVOK_SCENE_APP_RAGDOLL_RUNTIME_CONTROLLER_H
#define HAVOK_SCENE_APP_RAGDOLL_RUNTIME_CONTROLLER_H

#include <Common/Base/hkBase.h>
#include <Common/Base/Container/Array/hkArray.h>
#include <Common/Base/Math/QsTransform/hkQsTransform.h>

#include <Animation/Ragdoll/Controller/RigidBody/hkaKeyFrameHierarchyUtility.h>

#include "ragdoll_runtime_diagnostics.h"

class hkaRagdollInstance;
class hkaRagdollRigidBodyController;

class RagdollRuntimeController
{
public:
    RagdollRuntimeController();
    ~RagdollRuntimeController();

    bool initialize(hkaRagdollInstance* ragdoll_instance);
    void shutdown();

    void set_world_from_model_position(const float position[3]);
    void apply_pose_immediately();

    void hold();
    void release();
    bool is_holding() const;
    const RagdollRuntimeDiagnostics& diagnostics() const;

    void set_impact_release_speed(float speed);
    float impact_release_speed() const;

    void step(hkReal delta_time);

private:
    void configure_control_data();
    void reset_diagnostics();
    void update_diagnostics();
    float max_bone_linear_speed() const;

    hkaRagdollInstance* m_ragdoll_instance;
    hkaRagdollRigidBodyController* m_controller;
    hkArray<hkQsTransform> m_authored_pose_world_space;
    hkArray<hkQsTransform> m_target_pose_local_space;
    hkArray<hkaKeyFrameHierarchyUtility::Output> m_stress_output;
    hkQsTransform m_base_world_from_model;
    hkQsTransform m_world_from_model;
    bool m_is_holding;
    float m_impact_release_speed;
    RagdollRuntimeDiagnostics m_diagnostics;
};

#endif