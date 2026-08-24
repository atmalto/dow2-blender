#ifndef HAVOK_SIM_CLI_COMMAND_DISPATCH_INTERNAL_H
#define HAVOK_SIM_CLI_COMMAND_DISPATCH_INTERNAL_H

#include <string>

#include "command_dispatch.h"
#include "scene_entity.h"
#include "scene_presets.h"

class SimulationController;
struct BodyRenderState;
struct ForceSceneSpec;
struct SpawnedObjectSceneSpec;

namespace command_dispatch_internal
{
    typedef JsonValue (*CommandHandler)(SimulationController& controller, const JsonValue& cmd);

    std::string to_lower(const std::string& text);

    bool parse_preset(const std::string& text, ScenePresetId* out);
    bool parse_object_type(const JsonValue& value, int* out);
    bool parse_body_type(const JsonValue& value, int* out);
    bool parse_force_mode(const JsonValue& value, int* out);
    bool parse_kind(const std::string& text, SceneEntityKind* out);

    const char* kind_to_string(SceneEntityKind kind);

    SceneEntityId last_object_id(const SimulationController& controller);
    SceneEntityId last_force_id(const SimulationController& controller);
    SceneEntityId last_ragdoll_id(const SimulationController& controller);

    bool resolve_target(const SimulationController& controller, const JsonValue& cmd,
                        SceneEntityId* id_out, SceneEntityKind* kind_out, std::string* error);
    bool select_target(SimulationController& controller, const JsonValue& cmd,
                       const char* cmd_name, SceneEntityId* id_out,
                       SceneEntityKind* kind_out, JsonValue* error_result);
    bool select_target_with_kind(SimulationController& controller, const JsonValue& cmd,
                                 const char* kind_name, const char* cmd_name,
                                 SceneEntityId* id_out, SceneEntityKind* kind_out,
                                 JsonValue* error_result);

    JsonValue result_base(const std::string& cmd, bool ok);
    JsonValue result_error(const std::string& cmd, const std::string& message);
    JsonValue render_body_to_json(const BodyRenderState& body);
    JsonValue object_spec_to_json(const SpawnedObjectSceneSpec& spec);
    JsonValue force_spec_to_json(const ForceSceneSpec& spec);

    JsonValue cmd_new_scene(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_clear_scene(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_save_scene(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_load_scene(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_add_object(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_add_force(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_import_ragdoll(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_import_physics(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_sync_physics(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_sync_ragdoll(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_run(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_reset(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_settings(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_edit_object(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_edit_force(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_move(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_rotate(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_delete(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_duplicate(SimulationController& controller, const JsonValue& cmd);
    JsonValue cmd_get_props(SimulationController& controller, const JsonValue& cmd);
}

#endif