#include "command_dispatch_internal.h"

#include <string>
#include <vector>

#include "ragdoll_runtime_diagnostics.h"
#include "simulation_controller.h"

namespace command_dispatch_internal
{
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
            JsonValue error_result;
            if (!select_target_with_kind(controller, cmd,
                                         target == "object" ? "physics_object" : "force",
                                         "get_props", &id, &kind, &error_result))
            {
                return error_result;
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
}