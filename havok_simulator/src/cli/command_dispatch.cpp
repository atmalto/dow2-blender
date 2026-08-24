#include "command_dispatch_internal.h"

namespace
{
    struct DispatchEntry
    {
        const char* name;
        command_dispatch_internal::CommandHandler handler;
    };

    const DispatchEntry kDispatchTable[] =
    {
        { "new_scene", command_dispatch_internal::cmd_new_scene },
        { "clear_scene", command_dispatch_internal::cmd_clear_scene },
        { "save_scene", command_dispatch_internal::cmd_save_scene },
        { "load_scene", command_dispatch_internal::cmd_load_scene },
        { "add_object", command_dispatch_internal::cmd_add_object },
        { "add_force", command_dispatch_internal::cmd_add_force },
        { "import_ragdoll", command_dispatch_internal::cmd_import_ragdoll },
        { "import_physics", command_dispatch_internal::cmd_import_physics },
        { "sync_physics", command_dispatch_internal::cmd_sync_physics },
        { "sync_ragdoll", command_dispatch_internal::cmd_sync_ragdoll },
        { "run", command_dispatch_internal::cmd_run },
        { "reset", command_dispatch_internal::cmd_reset },
        { "settings", command_dispatch_internal::cmd_settings },
        { "edit_object", command_dispatch_internal::cmd_edit_object },
        { "edit_force", command_dispatch_internal::cmd_edit_force },
        { "move", command_dispatch_internal::cmd_move },
        { "rotate", command_dispatch_internal::cmd_rotate },
        { "delete", command_dispatch_internal::cmd_delete },
        { "duplicate", command_dispatch_internal::cmd_duplicate },
        { "get_props", command_dispatch_internal::cmd_get_props }
    };

    JsonValue dispatch(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string name = cmd.member_string("cmd");
        for (std::size_t i = 0; i < sizeof(kDispatchTable) / sizeof(kDispatchTable[0]); ++i)
        {
            if (name == kDispatchTable[i].name)
            {
                return kDispatchTable[i].handler(controller, cmd);
            }
        }
        return command_dispatch_internal::result_error(name.empty() ? "(missing)" : name,
                                                       "unknown command");
    }
}

JsonValue run_scenario(SimulationController& controller, const JsonValue& scenario)
{
    JsonValue results = JsonValue::make_array();

    const JsonValue* commands = scenario.is_array() ? &scenario : scenario.find("commands");
    if (!commands || !commands->is_array())
    {
        JsonValue out = JsonValue::make_object();
        out.set("ok", JsonValue(false));
        out.set("error", JsonValue("scenario must be an array or an object with a 'commands' array"));
        out.set("results", results);
        return out;
    }

    bool all_ok = true;
    const bool stop_on_error = scenario.member_bool("stop_on_error", true);
    for (std::size_t i = 0; i < commands->size(); ++i)
    {
        const JsonValue& cmd = commands->at(i);
        JsonValue result = dispatch(controller, cmd);
        const bool ok = result.member_bool("ok", false);
        all_ok = all_ok && ok;
        results.push_back(result);
        if (!ok && stop_on_error)
        {
            break;
        }
    }

    JsonValue out = JsonValue::make_object();
    out.set("ok", JsonValue(all_ok));
    out.set("results", results);
    return out;
}
