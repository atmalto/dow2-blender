#include "command_dispatch_internal.h"

#include <string>
#include <vector>

#include "scene_persistence.h"
#include "simulation_controller.h"
#include "simulation_settings.h"

namespace command_dispatch_internal
{
    JsonValue cmd_new_scene(SimulationController& controller, const JsonValue& cmd)
    {
        ScenePresetId preset = ScenePresetBlank;
        if (cmd.has("preset") && !parse_preset(cmd.member_string("preset"), &preset))
        {
            return result_error("new_scene", "unknown preset");
        }
        std::string error;
        if (!controller.create_scene_from_preset(preset, &error))
        {
            return result_error("new_scene", error.empty() ? "create_scene_from_preset failed" : error);
        }
        JsonValue r = result_base("new_scene", true);
        r.set("preset", JsonValue(scene_preset_label(preset)));
        return r;
    }

    JsonValue cmd_clear_scene(SimulationController& controller, const JsonValue&)
    {
        controller.clear_scene();
        return result_base("clear_scene", true);
    }

    JsonValue cmd_save_scene(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("save_scene", "missing 'path'");
        }
        PersistedSceneData data;
        if (!controller.build_persisted_scene(&data))
        {
            return result_error("save_scene", "build_persisted_scene failed");
        }
        std::string error;
        if (!save_scene_file(path.c_str(), data, &error))
        {
            return result_error("save_scene", error.empty() ? "save_scene_file failed" : error);
        }
        JsonValue r = result_base("save_scene", true);
        r.set("path", JsonValue(path));
        return r;
    }

    JsonValue cmd_load_scene(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("load_scene", "missing 'path'");
        }
        PersistedSceneData data;
        std::vector<std::string> warnings;
        std::string error;
        if (!load_scene_file(path.c_str(), &data, &warnings, &error))
        {
            return result_error("load_scene", error.empty() ? "load_scene_file failed" : error);
        }
        if (!controller.load_persisted_scene(data, &warnings, &error))
        {
            return result_error("load_scene", error.empty() ? "load_persisted_scene failed" : error);
        }
        JsonValue r = result_base("load_scene", true);
        r.set("path", JsonValue(path));
        JsonValue warn_arr = JsonValue::make_array();
        for (std::size_t i = 0; i < warnings.size(); ++i)
        {
            warn_arr.push_back(JsonValue(warnings[i]));
        }
        r.set("warnings", warn_arr);
        return r;
    }

    JsonValue cmd_run(SimulationController& controller, const JsonValue& cmd)
    {
        const int steps = cmd.member_int("steps", 1);
        for (int i = 0; i < steps; ++i)
        {
            controller.step();
        }
        JsonValue r = result_base("run", true);
        r.set("steps", JsonValue(steps));
        return r;
    }

    JsonValue cmd_reset(SimulationController& controller, const JsonValue&)
    {
        controller.reset();
        return result_base("reset", true);
    }

    JsonValue cmd_settings(SimulationController& controller, const JsonValue& cmd)
    {
        SimulationSettings& settings = SimulationSettings::instance();
        if (cmd.has("gravity_scale"))
        {
            settings.set_gravity_scale(static_cast<float>(cmd.member_number("gravity_scale", settings.gravity_scale())));
        }
        if (cmd.has("ragdoll_mass_scale"))
        {
            settings.set_ragdoll_mass_scale(static_cast<float>(cmd.member_number("ragdoll_mass_scale", settings.ragdoll_mass_scale())));
        }
        controller.reset();
        JsonValue r = result_base("settings", true);
        r.set("gravity_scale", JsonValue(static_cast<double>(settings.gravity_scale())));
        r.set("ragdoll_mass_scale", JsonValue(static_cast<double>(settings.ragdoll_mass_scale())));
        return r;
    }
}