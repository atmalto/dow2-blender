#ifndef HAVOK_SCENE_APP_RAGDOLL_RUNTIME_DIAGNOSTICS_H
#define HAVOK_SCENE_APP_RAGDOLL_RUNTIME_DIAGNOSTICS_H

struct RagdollRuntimeDiagnostics
{
    RagdollRuntimeDiagnostics()
        : is_holding(false)
        , max_stress(0.0f)
        , max_stress_bone_index(-1)
    {
    }

    bool is_holding;
    float max_stress;
    int max_stress_bone_index;
};

#endif