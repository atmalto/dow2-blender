#include "ragdoll_runtime.h"

#include <Common/Serialize/Util/hkLoader.h>
#include <Common/Serialize/Util/hkRootLevelContainer.h>

#include <Common/Base/Math/Matrix/hkMatrix3.h>

#include <Animation/Ragdoll/Instance/hkaRagdollInstance.h>

#include <Physics/Dynamics/Entity/hkpRigidBody.h>
#include <Physics/Dynamics/World/hkpWorld.h>

RagdollRuntime::RagdollRuntime()
    : m_entity_id(0)
    , m_loader(0)
    , m_container(0)
    , m_instance(0)
{
    m_start_position[0] = 0.0f;
    m_start_position[1] = 0.0f;
    m_start_position[2] = 0.0f;
}

RagdollRuntime::~RagdollRuntime()
{
    clear();
}

bool RagdollRuntime::load(SceneEntityId entity_id, const RagdollSceneSpec& spec, std::string* error_message)
{
    clear();

    m_entity_id = entity_id;
    m_loader = new hkLoader();
    m_container = m_loader->load(spec.asset_path.c_str());

    if (!m_container)
    {
        if (error_message)
        {
            *error_message = "Could not load HKX file.";
        }
        clear();
        return false;
    }

    m_instance = reinterpret_cast<hkaRagdollInstance*>(m_container->findObjectByType(hkaRagdollInstanceClass.getName()));
    if (!m_instance)
    {
        if (error_message)
        {
            *error_message = "Could not find hkaRagdollInstance in HKX.";
        }
        clear();
        return false;
    }

    if (!build_ragdoll_preview_data(m_entity_id, spec.asset_path.c_str(), *m_container, *m_instance, &m_preview_data))
    {
        if (error_message)
        {
            *error_message = "Could not build ragdoll preview snapshot.";
        }
        clear();
        return false;
    }

    if (!m_controller.initialize(m_instance))
    {
        if (error_message)
        {
            *error_message = "Could not initialize the ragdoll rigid-body controller.";
        }
        clear();
        return false;
    }

    set_start_position(spec.position);
    return true;
}

void RagdollRuntime::clear()
{
    remove_from_world();
    m_controller.shutdown();

    if (m_loader)
    {
        m_loader->removeReference();
        m_loader = 0;
    }

    m_container = 0;
    m_instance = 0;
    m_entity_id = 0;
    m_preview_data = RagdollPreviewData();
    m_start_position[0] = 0.0f;
    m_start_position[1] = 0.0f;
    m_start_position[2] = 0.0f;
}

SceneEntityId RagdollRuntime::entity_id() const
{
    return m_entity_id;
}

const RagdollPreviewData& RagdollRuntime::preview_data() const
{
    return m_preview_data;
}

hkaRagdollInstance* RagdollRuntime::instance() const
{
    return m_instance;
}

const RagdollRuntimeDiagnostics& RagdollRuntime::diagnostics() const
{
    return m_controller.diagnostics();
}

bool RagdollRuntime::add_to_world(hkpWorld* world)
{
    if (!world || !m_instance)
    {
        return false;
    }

    if (m_instance->getWorld() == world)
    {
        return true;
    }

    if (m_instance->getWorld())
    {
        m_instance->removeFromWorld();
    }

    if (m_instance->addToWorld(world, true) != HK_SUCCESS)
    {
        return false;
    }

    apply_start_position();
    m_controller.hold();
    return true;
}

void RagdollRuntime::remove_from_world()
{
    if (m_instance && m_instance->getWorld())
    {
        m_instance->removeFromWorld();
    }
}

void RagdollRuntime::set_start_position(const float position[3])
{
    if (!position)
    {
        return;
    }

    m_start_position[0] = position[0];
    m_start_position[1] = position[1];
    m_start_position[2] = position[2];
    apply_start_position();
}

void RagdollRuntime::step(hkReal delta_time)
{
    m_controller.step(delta_time);
}

void RagdollRuntime::release()
{
    m_controller.release();
}

bool RagdollRuntime::is_holding() const
{
    return m_controller.is_holding();
}

void RagdollRuntime::capture_original_masses()
{
    const int bone_count = body_count();
    int bone_index = 0;

    if (!m_original_masses.empty())
    {
        return;
    }

    m_original_masses.resize(bone_count, 0.0f);
    m_original_inertia_diag.resize(static_cast<std::size_t>(bone_count) * 3, 0.0f);

    for (bone_index = 0; bone_index < bone_count; ++bone_index)
    {
        hkpRigidBody* bone_body = body_at(bone_index);
        hkMatrix3 inertia;

        if (!bone_body)
        {
            continue;
        }

        m_original_masses[bone_index] = bone_body->getMass();
        bone_body->getInertiaLocal(inertia);
        m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 0] = inertia(0, 0);
        m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 1] = inertia(1, 1);
        m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 2] = inertia(2, 2);
    }
}

void RagdollRuntime::apply_mass_scale(float scale)
{
    const int bone_count = body_count();
    int bone_index = 0;

    if (bone_count <= 0 || scale <= 0.0f)
    {
        return;
    }

    capture_original_masses();

    for (bone_index = 0; bone_index < bone_count; ++bone_index)
    {
        hkpRigidBody* bone_body = body_at(bone_index);
        hkMatrix3 inertia;

        if (!bone_body || bone_index >= static_cast<int>(m_original_masses.size()))
        {
            continue;
        }

        // Scale mass and inertia by the same factor so rotational behaviour stays
        // consistent with the reduced mass. Always derive from the captured originals
        // so repeated resets never compound the scaling.
        bone_body->setMass(m_original_masses[bone_index] * scale);
        inertia.setDiagonal(
            m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 0] * scale,
            m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 1] * scale,
            m_original_inertia_diag[static_cast<std::size_t>(bone_index) * 3 + 2] * scale);
        bone_body->setInertiaLocal(inertia);
    }
}

int RagdollRuntime::body_count() const
{
    return m_instance ? m_instance->getNumBones() : 0;
}

hkpRigidBody* RagdollRuntime::body_at(int bone_index) const
{
    if (!m_instance || bone_index < 0 || bone_index >= m_instance->getNumBones())
    {
        return 0;
    }

    return m_instance->getRigidBodyOfBone(bone_index);
}

void RagdollRuntime::apply_start_position()
{
    m_controller.set_world_from_model_position(m_start_position);
    m_controller.apply_pose_immediately();
}