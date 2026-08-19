#ifndef HAVOK_SCENE_APP_RAGDOLL_RUNTIME_H
#define HAVOK_SCENE_APP_RAGDOLL_RUNTIME_H

#include <string>
#include <vector>

#include <Common/Base/hkBase.h>

#include "ragdoll_runtime_diagnostics.h"
#include "ragdoll_preview_data.h"
#include "ragdoll_runtime_controller.h"
#include "scene_document.h"

class hkLoader;
class hkRootLevelContainer;
class hkaRagdollInstance;
class hkpRigidBody;
class hkpWorld;

class RagdollRuntime
{
public:
    RagdollRuntime();
    ~RagdollRuntime();

    bool load(SceneEntityId entity_id, const RagdollSceneSpec& spec, std::string* error_message);
    void clear();

    SceneEntityId entity_id() const;
    const RagdollPreviewData& preview_data() const;
    hkaRagdollInstance* instance() const;
    const RagdollRuntimeDiagnostics& diagnostics() const;

    bool add_to_world(hkpWorld* world);
    void remove_from_world();

    void set_start_position(const float position[3]);
    void step(hkReal delta_time);

    void release();
    bool is_holding() const;

    // Applies a mass multiplier (e.g. 0.1) to every bone's live rigid body, scaling
    // mass and inertia together. The shipped/original masses are captured on first
    // call so repeated resets never compound. scale==1.0 restores originals exactly.
    void apply_mass_scale(float scale);

    int body_count() const;
    hkpRigidBody* body_at(int bone_index) const;

private:
    void apply_start_position();
    void capture_original_masses();

    SceneEntityId m_entity_id;
    hkLoader* m_loader;
    hkRootLevelContainer* m_container;
    hkaRagdollInstance* m_instance;
    RagdollPreviewData m_preview_data;
    RagdollRuntimeController m_controller;
    float m_start_position[3];
    std::vector<float> m_original_masses;
    std::vector<float> m_original_inertia_diag;
};

#endif