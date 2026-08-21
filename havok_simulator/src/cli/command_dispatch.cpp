#include "command_dispatch.h"

#include <string>
#include <vector>

#include "simulation_controller.h"
#include "scene_document.h"
#include "scene_entity.h"
#include "scene_presets.h"
#include "scene_persistence.h"
#include "physics_import.h"
#include "ragdoll_runtime_diagnostics.h"
#include "body_render_state.h"
#include "simulation_settings.h"

namespace
{
    // ---- small mapping helpers ------------------------------------------------

    std::string to_lower(const std::string& text)
    {
        std::string out(text);
        for (std::size_t i = 0; i < out.size(); ++i)
        {
            if (out[i] >= 'A' && out[i] <= 'Z')
            {
                out[i] = static_cast<char>(out[i] - 'A' + 'a');
            }
        }
        return out;
    }

    bool parse_preset(const std::string& text, ScenePresetId* out)
    {
        const std::string t = to_lower(text);
        if (t == "blank" || t.empty()) { *out = ScenePresetBlank; return true; }
        if (t == "flat_plane_with_force" || t == "flat_plane" || t == "flat") { *out = ScenePresetFlatPlaneWithForce; return true; }
        if (t == "diagonal_plane" || t == "diagonal" || t == "slanted") { *out = ScenePresetDiagonalPlane; return true; }
        return false;
    }

    bool parse_object_type(const JsonValue& value, int* out)
    {
        if (value.type() == JsonValue::TypeNumber) { *out = value.as_int(0); return true; }
        const std::string t = to_lower(value.as_string());
        if (t == "cube" || t == "box") { *out = SimulationController::ObjectCube; return true; }
        if (t == "sphere") { *out = SimulationController::ObjectSphere; return true; }
        if (t == "wedge") { *out = SimulationController::ObjectWedge; return true; }
        if (t == "hull" || t == "convex_hull" || t == "convexhull") { *out = SimulationController::ObjectConvexHull; return true; }
        return false;
    }

    bool parse_body_type(const JsonValue& value, int* out)
    {
        if (value.type() == JsonValue::TypeNumber) { *out = value.as_int(0); return true; }
        const std::string t = to_lower(value.as_string());
        if (t == "dynamic" || t == "dyn") { *out = SimulationController::BodyDynamic; return true; }
        if (t == "static" || t == "fixed") { *out = SimulationController::BodyStatic; return true; }
        return false;
    }

    bool parse_force_mode(const JsonValue& value, int* out)
    {
        if (value.type() == JsonValue::TypeNumber) { *out = value.as_int(0); return true; }
        const std::string t = to_lower(value.as_string());
        if (t == "push") { *out = SimulationController::ForcePush; return true; }
        if (t == "pull") { *out = SimulationController::ForcePull; return true; }
        return false;
    }

    bool parse_kind(const std::string& text, SceneEntityKind* out)
    {
        const std::string t = to_lower(text);
        if (t == "ragdoll") { *out = SceneEntityKindRagdoll; return true; }
        if (t == "physics_object" || t == "object" || t == "body") { *out = SceneEntityKindPhysicsObject; return true; }
        if (t == "force") { *out = SceneEntityKindForce; return true; }
        return false;
    }

    const char* kind_to_string(SceneEntityKind kind)
    {
        switch (kind)
        {
        case SceneEntityKindRagdoll: return "ragdoll";
        case SceneEntityKindPhysicsObject: return "physics_object";
        case SceneEntityKindForce: return "force";
        default: return "none";
        }
    }

    const char* shape_to_string(BodyRenderState::ShapeType shape)
    {
        switch (shape)
        {
        case BodyRenderState::ShapeBox: return "box";
        case BodyRenderState::ShapeSphere: return "sphere";
        case BodyRenderState::ShapeCapsule: return "capsule";
        case BodyRenderState::ShapeWedge: return "wedge";
        case BodyRenderState::ShapeConvexHull: return "convex_hull";
        case BodyRenderState::ShapeArrow: return "arrow";
        default: return "unknown";
        }
    }

    SceneEntityId last_object_id(const SimulationController& controller)
    {
        const std::vector<PhysicsObjectSceneEntity>& objects = controller.scene_document().objects();
        return objects.empty() ? 0u : objects.back().record.id;
    }

    SceneEntityId last_force_id(const SimulationController& controller)
    {
        const std::vector<ForceSceneEntity>& forces = controller.scene_document().forces();
        return forces.empty() ? 0u : forces.back().record.id;
    }

    SceneEntityId last_ragdoll_id(const SimulationController& controller)
    {
        const std::vector<RagdollSceneEntity>& ragdolls = controller.scene_document().ragdolls();
        return ragdolls.empty() ? 0u : ragdolls.back().record.id;
    }

    // Resolve the entity id/kind a command targets. Accepts explicit "id"+"kind",
    // or falls back to the last entity of the given kind when only "kind" is set.
    bool resolve_target(const SimulationController& controller, const JsonValue& cmd,
                        SceneEntityId* id_out, SceneEntityKind* kind_out, std::string* error)
    {
        SceneEntityKind kind = SceneEntityKindNone;
        if (cmd.has("kind"))
        {
            if (!parse_kind(cmd.member_string("kind"), &kind))
            {
                *error = "unknown kind";
                return false;
            }
        }

        if (cmd.has("id"))
        {
            *id_out = static_cast<SceneEntityId>(cmd.member_int("id", 0));
            *kind_out = kind;
            return true;
        }

        // No explicit id: use the most recently added entity of the kind.
        switch (kind)
        {
        case SceneEntityKindPhysicsObject: *id_out = last_object_id(controller); break;
        case SceneEntityKindForce: *id_out = last_force_id(controller); break;
        case SceneEntityKindRagdoll: *id_out = last_ragdoll_id(controller); break;
        default: *error = "command requires 'id' or 'kind'"; return false;
        }
        *kind_out = kind;
        return *id_out != 0u;
    }

    // ---- result builders ------------------------------------------------------

    JsonValue result_base(const std::string& cmd, bool ok)
    {
        JsonValue r = JsonValue::make_object();
        r.set("cmd", JsonValue(cmd));
        r.set("ok", JsonValue(ok));
        return r;
    }

    JsonValue result_error(const std::string& cmd, const std::string& message)
    {
        JsonValue r = result_base(cmd, false);
        r.set("error", JsonValue(message));
        return r;
    }

    JsonValue render_body_to_json(const BodyRenderState& body)
    {
        JsonValue j = JsonValue::make_object();
        j.set("entity_id", JsonValue(static_cast<int>(body.entity_id)));
        j.set("kind", JsonValue(kind_to_string(body.entity_kind)));
        j.set("shape", JsonValue(shape_to_string(body.shape_type)));
        j.set("is_dynamic", JsonValue(body.is_dynamic));
        j.set("is_selected", JsonValue(body.is_selected));
        j.set("position", JsonValue::make_vec(body.position, 3));
        j.set("rotation", JsonValue::make_vec(body.rotation, 4));
        j.set("half_extents", JsonValue::make_vec(body.half_extents, 3));
        j.set("radius", JsonValue(static_cast<double>(body.radius)));
        return j;
    }

    JsonValue object_spec_to_json(const SpawnedObjectSceneSpec& spec)
    {
        JsonValue j = JsonValue::make_object();
        j.set("object_type", JsonValue(spec.object_type));
        j.set("body_type", JsonValue(spec.body_type));
        j.set("position", JsonValue::make_vec(spec.position, 3));
        j.set("rotation_degrees", JsonValue::make_vec(spec.rotation_degrees, 3));
        j.set("scale", JsonValue::make_vec(spec.scale, 3));
        j.set("restitution", JsonValue(static_cast<double>(spec.restitution)));
        j.set("mass", JsonValue(static_cast<double>(spec.mass)));
        j.set("shape_radius", JsonValue(static_cast<double>(spec.shape_radius)));
        return j;
    }

    JsonValue force_spec_to_json(const ForceSceneSpec& spec)
    {
        JsonValue j = JsonValue::make_object();
        j.set("position", JsonValue::make_vec(spec.position, 3));
        j.set("rotation_degrees", JsonValue::make_vec(spec.rotation_degrees, 3));
        j.set("strength", JsonValue(static_cast<double>(spec.strength)));
        j.set("mode", JsonValue(spec.mode));
        j.set("active", JsonValue(spec.active));
        return j;
    }

    // ---- command handlers -----------------------------------------------------

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

    JsonValue cmd_add_object(SimulationController& controller, const JsonValue& cmd)
    {
        SpawnedObjectSceneSpec spec;
        if (cmd.has("object") && !parse_object_type(*cmd.find("object"), &spec.object_type))
        {
            return result_error("add_object", "unknown object type");
        }
        if (cmd.has("body") && !parse_body_type(*cmd.find("body"), &spec.body_type))
        {
            return result_error("add_object", "unknown body type");
        }
        cmd.member_vec("position", spec.position, 3);
        cmd.member_vec("rotation", spec.rotation_degrees, 3);
        cmd.member_vec("rotation_degrees", spec.rotation_degrees, 3);
        cmd.member_vec("scale", spec.scale, 3);
        spec.mass = static_cast<float>(cmd.member_number("mass", spec.mass));
        spec.restitution = static_cast<float>(cmd.member_number("restitution", spec.restitution));
        spec.shape_radius = static_cast<float>(cmd.member_number("shape_radius", spec.shape_radius));

        std::string error;
        if (!controller.add_object(spec, &error))
        {
            return result_error("add_object", error.empty() ? "add_object failed" : error);
        }
        JsonValue r = result_base("add_object", true);
        r.set("id", JsonValue(static_cast<int>(last_object_id(controller))));
        r.set("kind", JsonValue("physics_object"));
        return r;
    }

    JsonValue cmd_add_force(SimulationController& controller, const JsonValue& cmd)
    {
        ForceSceneSpec spec;
        spec.position[0] = spec.position[1] = spec.position[2] = 0.0f;
        spec.rotation_degrees[0] = spec.rotation_degrees[1] = spec.rotation_degrees[2] = 0.0f;
        spec.strength = 100.0f;
        spec.mode = SimulationController::ForcePush;
        spec.active = true;

        cmd.member_vec("position", spec.position, 3);
        cmd.member_vec("rotation", spec.rotation_degrees, 3);
        cmd.member_vec("rotation_degrees", spec.rotation_degrees, 3);
        spec.strength = static_cast<float>(cmd.member_number("strength", spec.strength));
        if (cmd.has("mode") && !parse_force_mode(*cmd.find("mode"), &spec.mode))
        {
            return result_error("add_force", "unknown force mode");
        }
        spec.active = cmd.member_bool("active", spec.active);

        std::string error;
        if (!controller.add_force_entity(spec, &error))
        {
            return result_error("add_force", error.empty() ? "add_force_entity failed" : error);
        }
        JsonValue r = result_base("add_force", true);
        r.set("id", JsonValue(static_cast<int>(last_force_id(controller))));
        r.set("kind", JsonValue("force"));
        return r;
    }

    JsonValue cmd_import_ragdoll(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("import_ragdoll", "missing 'path'");
        }
        std::string error;
        if (!controller.load_ragdoll(path.c_str(), &error))
        {
            return result_error("import_ragdoll", error.empty() ? "load_ragdoll failed" : error);
        }
        JsonValue r = result_base("import_ragdoll", true);
        r.set("id", JsonValue(static_cast<int>(last_ragdoll_id(controller))));
        r.set("kind", JsonValue("ragdoll"));
        return r;
    }

    JsonValue cmd_import_physics(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("import_physics", "missing 'path'");
        }
        std::vector<ImportedPhysicsSystem> systems;
        std::string error;
        if (!load_imported_physics_systems(path.c_str(), systems, &error))
        {
            return result_error("import_physics", error.empty() ? "load_imported_physics_systems failed" : error);
        }

        std::vector<int> selected;
        if (cmd.has("systems") && cmd.find("systems")->is_array())
        {
            const JsonValue& arr = *cmd.find("systems");
            for (std::size_t i = 0; i < arr.size(); ++i)
            {
                selected.push_back(arr.at(i).as_int(0));
            }
        }
        else
        {
            for (std::size_t i = 0; i < systems.size(); ++i)
            {
                selected.push_back(static_cast<int>(i));
            }
        }

        if (!controller.import_physics_systems(systems, selected, &error))
        {
            return result_error("import_physics", error.empty() ? "import_physics_systems failed" : error);
        }
        JsonValue r = result_base("import_physics", true);
        r.set("systems_available", JsonValue(static_cast<int>(systems.size())));
        r.set("object_count", JsonValue(controller.spawned_object_count()));
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
        // Settings apply to live bodies at bootstrap; reset so they take effect now.
        controller.reset();
        JsonValue r = result_base("settings", true);
        r.set("gravity_scale", JsonValue(static_cast<double>(settings.gravity_scale())));
        r.set("ragdoll_mass_scale", JsonValue(static_cast<double>(settings.ragdoll_mass_scale())));
        return r;
    }

    JsonValue cmd_edit_object(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        JsonValue target_cmd = cmd;
        target_cmd.set("kind", JsonValue("physics_object"));
        if (!resolve_target(controller, target_cmd, &id, &kind, &error))
        {
            return result_error("edit_object", error.empty() ? "target not found" : error);
        }
        if (!controller.select_entity(id, SceneEntityKindPhysicsObject))
        {
            return result_error("edit_object", "select_entity failed");
        }
        SpawnedObjectSceneSpec spec;
        if (!controller.get_selected_object_spec(&spec))
        {
            return result_error("edit_object", "get_selected_object_spec failed");
        }
        if (cmd.has("object")) { parse_object_type(*cmd.find("object"), &spec.object_type); }
        if (cmd.has("body")) { parse_body_type(*cmd.find("body"), &spec.body_type); }
        cmd.member_vec("position", spec.position, 3);
        cmd.member_vec("rotation", spec.rotation_degrees, 3);
        cmd.member_vec("rotation_degrees", spec.rotation_degrees, 3);
        cmd.member_vec("scale", spec.scale, 3);
        spec.mass = static_cast<float>(cmd.member_number("mass", spec.mass));
        spec.restitution = static_cast<float>(cmd.member_number("restitution", spec.restitution));
        spec.shape_radius = static_cast<float>(cmd.member_number("shape_radius", spec.shape_radius));

        if (!controller.update_selected_object(spec, &error))
        {
            return result_error("edit_object", error.empty() ? "update_selected_object failed" : error);
        }
        JsonValue r = result_base("edit_object", true);
        r.set("id", JsonValue(static_cast<int>(id)));
        return r;
    }

    JsonValue cmd_edit_force(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        JsonValue target_cmd = cmd;
        target_cmd.set("kind", JsonValue("force"));
        if (!resolve_target(controller, target_cmd, &id, &kind, &error))
        {
            return result_error("edit_force", error.empty() ? "target not found" : error);
        }
        if (!controller.select_entity(id, SceneEntityKindForce))
        {
            return result_error("edit_force", "select_entity failed");
        }
        ForceSceneSpec spec;
        if (!controller.get_selected_force_spec(&spec))
        {
            return result_error("edit_force", "get_selected_force_spec failed");
        }
        cmd.member_vec("position", spec.position, 3);
        cmd.member_vec("rotation", spec.rotation_degrees, 3);
        cmd.member_vec("rotation_degrees", spec.rotation_degrees, 3);
        spec.strength = static_cast<float>(cmd.member_number("strength", spec.strength));
        if (cmd.has("mode")) { parse_force_mode(*cmd.find("mode"), &spec.mode); }
        spec.active = cmd.member_bool("active", spec.active);

        if (!controller.update_selected_force(spec, &error))
        {
            return result_error("edit_force", error.empty() ? "update_selected_force failed" : error);
        }
        JsonValue r = result_base("edit_force", true);
        r.set("id", JsonValue(static_cast<int>(id)));
        return r;
    }

    JsonValue cmd_move(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        if (!resolve_target(controller, cmd, &id, &kind, &error))
        {
            return result_error("move", error.empty() ? "target not found" : error);
        }
        float position[3] = { 0.0f, 0.0f, 0.0f };
        if (!cmd.member_vec("position", position, 3))
        {
            return result_error("move", "missing 'position' [x,y,z]");
        }
        if (!controller.select_entity(id, kind))
        {
            return result_error("move", "select_entity failed");
        }

        if (kind == SceneEntityKindRagdoll)
        {
            RagdollSceneSpec spec;
            if (!controller.get_selected_ragdoll_spec(&spec))
            {
                return result_error("move", "get_selected_ragdoll_spec failed");
            }
            spec.position[0] = position[0];
            spec.position[1] = position[1];
            spec.position[2] = position[2];
            if (!controller.update_selected_ragdoll(spec, &error))
            {
                return result_error("move", error.empty() ? "update_selected_ragdoll failed" : error);
            }
        }
        else if (kind == SceneEntityKindPhysicsObject)
        {
            SpawnedObjectSceneSpec spec;
            if (!controller.get_selected_object_spec(&spec))
            {
                return result_error("move", "get_selected_object_spec failed");
            }
            spec.position[0] = position[0];
            spec.position[1] = position[1];
            spec.position[2] = position[2];
            if (!controller.update_selected_object(spec, &error))
            {
                return result_error("move", error.empty() ? "update_selected_object failed" : error);
            }
        }
        else if (kind == SceneEntityKindForce)
        {
            ForceSceneSpec spec;
            if (!controller.get_selected_force_spec(&spec))
            {
                return result_error("move", "get_selected_force_spec failed");
            }
            spec.position[0] = position[0];
            spec.position[1] = position[1];
            spec.position[2] = position[2];
            if (!controller.update_selected_force(spec, &error))
            {
                return result_error("move", error.empty() ? "update_selected_force failed" : error);
            }
        }
        else
        {
            return result_error("move", "unsupported kind");
        }

        JsonValue r = result_base("move", true);
        r.set("id", JsonValue(static_cast<int>(id)));
        r.set("kind", JsonValue(kind_to_string(kind)));
        return r;
    }

    JsonValue cmd_rotate(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        if (!resolve_target(controller, cmd, &id, &kind, &error))
        {
            return result_error("rotate", error.empty() ? "target not found" : error);
        }
        float rotation[3] = { 0.0f, 0.0f, 0.0f };
        if (!cmd.member_vec("rotation", rotation, 3) && !cmd.member_vec("rotation_degrees", rotation, 3))
        {
            return result_error("rotate", "missing 'rotation' [x,y,z] degrees");
        }
        if (kind == SceneEntityKindRagdoll)
        {
            return result_error("rotate", "ragdoll entities cannot be rotated");
        }
        if (!controller.select_entity(id, kind))
        {
            return result_error("rotate", "select_entity failed");
        }

        if (kind == SceneEntityKindPhysicsObject)
        {
            SpawnedObjectSceneSpec spec;
            if (!controller.get_selected_object_spec(&spec))
            {
                return result_error("rotate", "get_selected_object_spec failed");
            }
            spec.rotation_degrees[0] = rotation[0];
            spec.rotation_degrees[1] = rotation[1];
            spec.rotation_degrees[2] = rotation[2];
            if (!controller.update_selected_object(spec, &error))
            {
                return result_error("rotate", error.empty() ? "update_selected_object failed" : error);
            }
        }
        else if (kind == SceneEntityKindForce)
        {
            ForceSceneSpec spec;
            if (!controller.get_selected_force_spec(&spec))
            {
                return result_error("rotate", "get_selected_force_spec failed");
            }
            spec.rotation_degrees[0] = rotation[0];
            spec.rotation_degrees[1] = rotation[1];
            spec.rotation_degrees[2] = rotation[2];
            if (!controller.update_selected_force(spec, &error))
            {
                return result_error("rotate", error.empty() ? "update_selected_force failed" : error);
            }
        }
        else
        {
            return result_error("rotate", "unsupported kind");
        }

        JsonValue r = result_base("rotate", true);
        r.set("id", JsonValue(static_cast<int>(id)));
        r.set("kind", JsonValue(kind_to_string(kind)));
        return r;
    }

    JsonValue cmd_delete(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        if (!resolve_target(controller, cmd, &id, &kind, &error))
        {
            return result_error("delete", error.empty() ? "target not found" : error);
        }
        if (!controller.select_entity(id, kind))
        {
            return result_error("delete", "select_entity failed");
        }
        if (!controller.delete_selected_entity())
        {
            return result_error("delete", "delete_selected_entity failed");
        }
        JsonValue r = result_base("delete", true);
        r.set("id", JsonValue(static_cast<int>(id)));
        r.set("kind", JsonValue(kind_to_string(kind)));
        return r;
    }

    JsonValue cmd_duplicate(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        std::string error;
        if (!resolve_target(controller, cmd, &id, &kind, &error))
        {
            return result_error("duplicate", error.empty() ? "target not found" : error);
        }
        if (!controller.select_entity(id, kind))
        {
            return result_error("duplicate", "select_entity failed");
        }
        if (!controller.duplicate_selected_entity(&error))
        {
            return result_error("duplicate", error.empty() ? "duplicate_selected_entity failed" : error);
        }
        SceneEntityId new_id = 0;
        switch (kind)
        {
        case SceneEntityKindPhysicsObject: new_id = last_object_id(controller); break;
        case SceneEntityKindForce: new_id = last_force_id(controller); break;
        case SceneEntityKindRagdoll: new_id = last_ragdoll_id(controller); break;
        default: break;
        }
        JsonValue r = result_base("duplicate", true);
        r.set("source_id", JsonValue(static_cast<int>(id)));
        r.set("id", JsonValue(static_cast<int>(new_id)));
        r.set("kind", JsonValue(kind_to_string(kind)));
        return r;
    }

    JsonValue cmd_get_props(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string target = to_lower(cmd.member_string("target", "scene"));

        if (target == "scene")
        {
            const std::vector<BodyRenderState>& bodies = controller.render_bodies();
            JsonValue arr = JsonValue::make_array();
            for (std::size_t i = 0; i < bodies.size(); ++i)
            {
                arr.push_back(render_body_to_json(bodies[i]));
            }
            JsonValue r = result_base("get_props", true);
            r.set("target", JsonValue("scene"));
            r.set("body_count", JsonValue(static_cast<int>(bodies.size())));
            r.set("bodies", arr);
            return r;
        }

        if (target == "object" || target == "force")
        {
            SceneEntityId id = 0;
            SceneEntityKind kind = SceneEntityKindNone;
            std::string error;
            JsonValue target_cmd = cmd;
            target_cmd.set("kind", JsonValue(target == "object" ? "physics_object" : "force"));
            if (!resolve_target(controller, target_cmd, &id, &kind, &error))
            {
                return result_error("get_props", error.empty() ? "target not found" : error);
            }
            if (!controller.select_entity(id, kind))
            {
                return result_error("get_props", "select_entity failed");
            }
            JsonValue r = result_base("get_props", true);
            r.set("target", JsonValue(target));
            r.set("id", JsonValue(static_cast<int>(id)));
            if (target == "object")
            {
                SpawnedObjectSceneSpec spec;
                if (!controller.get_selected_object_spec(&spec))
                {
                    return result_error("get_props", "get_selected_object_spec failed");
                }
                r.set("object", object_spec_to_json(spec));
            }
            else
            {
                ForceSceneSpec spec;
                if (!controller.get_selected_force_spec(&spec))
                {
                    return result_error("get_props", "get_selected_force_spec failed");
                }
                r.set("force", force_spec_to_json(spec));
            }
            return r;
        }

        if (target == "ragdoll")
        {
            SceneEntityId id = cmd.has("id")
                ? static_cast<SceneEntityId>(cmd.member_int("id", 0))
                : last_ragdoll_id(controller);
            if (id == 0)
            {
                return result_error("get_props", "no ragdoll in scene");
            }
            RagdollRuntimeDiagnostics diag;
            const bool have_diag = controller.get_ragdoll_runtime_diagnostics(id, &diag);
            JsonValue r = result_base("get_props", true);
            r.set("target", JsonValue("ragdoll"));
            r.set("id", JsonValue(static_cast<int>(id)));
            JsonValue rag = JsonValue::make_object();
            rag.set("has_diagnostics", JsonValue(have_diag));
            rag.set("is_holding", JsonValue(diag.is_holding));
            rag.set("max_stress", JsonValue(static_cast<double>(diag.max_stress)));
            rag.set("max_stress_bone_index", JsonValue(diag.max_stress_bone_index));
            r.set("ragdoll", rag);
            return r;
        }

        return result_error("get_props", "unknown target (expected scene|object|force|ragdoll)");
    }

    JsonValue dispatch(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string name = cmd.member_string("cmd");
        if (name == "new_scene") return cmd_new_scene(controller, cmd);
        if (name == "clear_scene") return cmd_clear_scene(controller, cmd);
        if (name == "save_scene") return cmd_save_scene(controller, cmd);
        if (name == "load_scene") return cmd_load_scene(controller, cmd);
        if (name == "add_object") return cmd_add_object(controller, cmd);
        if (name == "add_force") return cmd_add_force(controller, cmd);
        if (name == "import_ragdoll") return cmd_import_ragdoll(controller, cmd);
        if (name == "import_physics") return cmd_import_physics(controller, cmd);
        if (name == "run") return cmd_run(controller, cmd);
        if (name == "reset") return cmd_reset(controller, cmd);
        if (name == "settings") return cmd_settings(controller, cmd);
        if (name == "edit_object") return cmd_edit_object(controller, cmd);
        if (name == "edit_force") return cmd_edit_force(controller, cmd);
        if (name == "move") return cmd_move(controller, cmd);
        if (name == "rotate") return cmd_rotate(controller, cmd);
        if (name == "delete") return cmd_delete(controller, cmd);
        if (name == "duplicate") return cmd_duplicate(controller, cmd);
        if (name == "get_props") return cmd_get_props(controller, cmd);
        return result_error(name.empty() ? "(missing)" : name, "unknown command");
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
