#ifndef HAVOK_SCENE_APP_SIMULATION_SETTINGS_H
#define HAVOK_SCENE_APP_SIMULATION_SETTINGS_H

// Global, universally-accessible simulation settings singleton.
//
// This holds scene-independent knobs (ragdoll mass scaling, gravity) that any
// subsystem (SimulationController, UI dialogs) can read or write without threading
// the values through constructors. Shipped ragdoll/physics data is never modified;
// these scales are applied only to the live Havok bodies at simulation bootstrap so
// the authoring/preview values remain faithful to the original files.
//
// To add a future setting: add a field + clamped accessor here and one apply-point
// in SimulationController. Nothing else needs to change.
class SimulationSettings
{
public:
    static SimulationSettings& instance();

    // Fraction (0.05 - 1.0) applied to every ragdoll bone's original mass at
    // simulation bootstrap. 0.1 = one tenth of the shipped mass. Default 0.1.
    float ragdoll_mass_scale() const;
    void set_ragdoll_mass_scale(float scale);

    // Multiplier (0.0 - 2.0) on standard gravity. 1.0 = Havok default (-9.8 m/s^2
    // on Y). 0.0 = weightless (objects retain momentum from forces indefinitely).
    float gravity_scale() const;
    void set_gravity_scale(float scale);

    // Base gravity acceleration magnitude (m/s^2) that gravity_scale multiplies.
    static float base_gravity();

private:
    SimulationSettings();

    float m_ragdoll_mass_scale;
    float m_gravity_scale;
};

#endif
