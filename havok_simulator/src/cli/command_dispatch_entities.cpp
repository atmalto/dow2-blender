#include "command_dispatch_internal.h"

#include <string>

#include "simulation_controller.h"

namespace command_dispatch_internal
{
    namespace
    {
        void apply_object_spec_fields(const JsonValue& cmd, SpawnedObjectSceneSpec* spec,
                                      bool allow_shape_and_body)
        {
            if (allow_shape_and_body && cmd.has("object"))
            {
                parse_object_type(*cmd.find("object"), &spec->object_type);
            }
            if (allow_shape_and_body && cmd.has("body"))
            {
                parse_body_type(*cmd.find("body"), &spec->body_type);
            }
            cmd.member_vec("position", spec->position, 3);
            cmd.member_vec("rotation", spec->rotation_degrees, 3);
            cmd.member_vec("rotation_degrees", spec->rotation_degrees, 3);
            cmd.member_vec("scale", spec->scale, 3);
            spec->mass = static_cast<float>(cmd.member_number("mass", spec->mass));
            spec->restitution = static_cast<float>(cmd.member_number("restitution", spec->restitution));
            spec->shape_radius = static_cast<float>(cmd.member_number("shape_radius", spec->shape_radius));
        }

        void apply_force_spec_fields(const JsonValue& cmd, ForceSceneSpec* spec,
                                     bool allow_mode)
        {
            cmd.member_vec("position", spec->position, 3);
            cmd.member_vec("rotation", spec->rotation_degrees, 3);
            cmd.member_vec("rotation_degrees", spec->rotation_degrees, 3);
            spec->strength = static_cast<float>(cmd.member_number("strength", spec->strength));
            spec->radius = static_cast<float>(cmd.member_number("radius", spec->radius));
            if (allow_mode && cmd.has("mode"))
            {
                parse_force_mode(*cmd.find("mode"), &spec->mode);
            }
            spec->active = cmd.member_bool("active", spec->active);
        }
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
        apply_object_spec_fields(cmd, &spec, false);

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
        spec.radius = 0.0f;

        apply_force_spec_fields(cmd, &spec, false);
        if (cmd.has("mode") && !parse_force_mode(*cmd.find("mode"), &spec.mode))
        {
            return result_error("add_force", "unknown force mode");
        }

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

    JsonValue cmd_edit_object(SimulationController& controller, const JsonValue& cmd)
    {
        SceneEntityId id = 0;
        SceneEntityKind kind = SceneEntityKindNone;
        JsonValue error_result;
        if (!select_target_with_kind(controller, cmd, "physics_object", "edit_object",
                                     &id, &kind, &error_result))
        {
            return error_result;
        }
        SpawnedObjectSceneSpec spec;
        if (!controller.get_selected_object_spec(&spec))
        {
            return result_error("edit_object", "get_selected_object_spec failed");
        }
        apply_object_spec_fields(cmd, &spec, true);

        std::string error;
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
        JsonValue error_result;
        if (!select_target_with_kind(controller, cmd, "force", "edit_force",
                                     &id, &kind, &error_result))
        {
            return error_result;
        }
        ForceSceneSpec spec;
        if (!controller.get_selected_force_spec(&spec))
        {
            return result_error("edit_force", "get_selected_force_spec failed");
        }
        apply_force_spec_fields(cmd, &spec, true);

        std::string error;
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
        JsonValue error_result;
        if (!select_target(controller, cmd, "move", &id, &kind, &error_result))
        {
            return error_result;
        }
        float position[3] = { 0.0f, 0.0f, 0.0f };
        if (!cmd.member_vec("position", position, 3))
        {
            return result_error("move", "missing 'position' [x,y,z]");
        }

        std::string error;
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
        JsonValue error_result;
        if (!select_target(controller, cmd, "rotate", &id, &kind, &error_result))
        {
            return error_result;
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

        std::string error;
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
        JsonValue error_result;
        if (!select_target(controller, cmd, "delete", &id, &kind, &error_result))
        {
            return error_result;
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
        JsonValue error_result;
        if (!select_target(controller, cmd, "duplicate", &id, &kind, &error_result))
        {
            return error_result;
        }
        std::string error;
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
}