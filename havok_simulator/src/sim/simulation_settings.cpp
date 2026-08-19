#include "simulation_settings.h"

namespace
{
    const float kBaseGravity = 9.8f;

    const float kRagdollMassScaleMin = 0.05f;
    const float kRagdollMassScaleMax = 1.0f;
    const float kRagdollMassScaleDefault = 0.1f;

    const float kGravityScaleMin = 0.0f;
    const float kGravityScaleMax = 2.0f;
    const float kGravityScaleDefault = 1.0f;

    float clamp_range(float value, float minimum, float maximum)
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
}

SimulationSettings::SimulationSettings()
    : m_ragdoll_mass_scale(kRagdollMassScaleDefault)
    , m_gravity_scale(kGravityScaleDefault)
{
}

SimulationSettings& SimulationSettings::instance()
{
    static SimulationSettings settings;
    return settings;
}

float SimulationSettings::ragdoll_mass_scale() const
{
    return m_ragdoll_mass_scale;
}

void SimulationSettings::set_ragdoll_mass_scale(float scale)
{
    m_ragdoll_mass_scale = clamp_range(scale, kRagdollMassScaleMin, kRagdollMassScaleMax);
}

float SimulationSettings::gravity_scale() const
{
    return m_gravity_scale;
}

void SimulationSettings::set_gravity_scale(float scale)
{
    m_gravity_scale = clamp_range(scale, kGravityScaleMin, kGravityScaleMax);
}

float SimulationSettings::base_gravity()
{
    return kBaseGravity;
}
