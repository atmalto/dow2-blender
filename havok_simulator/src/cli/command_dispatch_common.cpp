#include "command_dispatch_internal.h"

#include <string>
#include <vector>

#include "body_render_state.h"
#include "simulation_controller.h"

namespace command_dispatch_internal
{
    namespace
    {
        bool select_target_impl(SimulationController& controller, const JsonValue& cmd,
                                const char* forced_kind_name, const char* cmd_name,
                                SceneEntityId* id_out, SceneEntityKind* kind_out,
                                JsonValue* error_result)
        {
            std::string error;
            JsonValue target_cmd = cmd;
            if (forced_kind_name && forced_kind_name[0] != '\0')
            {
                target_cmd.set("kind", JsonValue(forced_kind_name));
            }
            if (!resolve_target(controller, target_cmd, id_out, kind_out, &error))
            {
                if (error_result)
                {
                    *error_result = result_error(cmd_name, error.empty() ? "target not found" : error);
                }
                return false;
            }
            if (!controller.select_entity(*id_out, *kind_out))
            {
                if (error_result)
                {
                    *error_result = result_error(cmd_name, "select_entity failed");
                }
                return false;
            }
            return true;
        }
    }

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

    bool select_target(SimulationController& controller, const JsonValue& cmd,
                       const char* cmd_name, SceneEntityId* id_out,
                       SceneEntityKind* kind_out, JsonValue* error_result)
    {
        return select_target_impl(controller, cmd, "", cmd_name, id_out, kind_out, error_result);
    }

    bool select_target_with_kind(SimulationController& controller, const JsonValue& cmd,
                                 const char* kind_name, const char* cmd_name,
                                 SceneEntityId* id_out, SceneEntityKind* kind_out,
                                 JsonValue* error_result)
    {
        return select_target_impl(controller, cmd, kind_name, cmd_name,
                                  id_out, kind_out, error_result);
    }

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
        j.set("radius", JsonValue(static_cast<double>(spec.radius)));
        return j;
    }
}