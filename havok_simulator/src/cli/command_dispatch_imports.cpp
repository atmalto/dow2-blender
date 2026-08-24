#include "command_dispatch_internal.h"

#include <map>
#include <set>
#include <string>
#include <vector>

#include "physics_import.h"
#include "scene_document.h"
#include "simulation_controller.h"

namespace command_dispatch_internal
{
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

    JsonValue cmd_sync_physics(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("sync_physics", "missing 'path'");
        }
        const std::string sync_id = cmd.member_string("sync_id", "dow2_physics");
        const bool partial = cmd.member_bool("partial", false);
        std::set<std::string> only_names;
        if (cmd.has("only_names") && cmd.find("only_names")->is_array())
        {
            const JsonValue& arr = *cmd.find("only_names");
            for (std::size_t i = 0; i < arr.size(); ++i)
            {
                only_names.insert(arr.at(i).as_string());
            }
        }

        std::vector<ImportedPhysicsSystem> systems;
        std::string error;
        if (!load_imported_physics_systems(path.c_str(), systems, &error))
        {
            return result_error("sync_physics", error.empty() ? "load_imported_physics_systems failed" : error);
        }

        if (!only_names.empty())
        {
            for (std::size_t s = 0; s < systems.size(); ++s)
            {
                std::vector<ImportedPhysicsObject> kept;
                for (std::size_t o = 0; o < systems[s].objects.size(); ++o)
                {
                    if (only_names.find(systems[s].objects[o].name) != only_names.end())
                    {
                        kept.push_back(systems[s].objects[o]);
                    }
                }
                systems[s].objects.swap(kept);
            }
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

        std::set<std::string> incoming_names;
        for (std::size_t s = 0; s < selected.size(); ++s)
        {
            const int idx = selected[s];
            if (idx < 0 || idx >= static_cast<int>(systems.size()))
            {
                continue;
            }
            for (std::size_t o = 0; o < systems[idx].objects.size(); ++o)
            {
                incoming_names.insert(systems[idx].name + " / " + systems[idx].objects[o].name);
            }
        }

        SceneDocument& document = controller.scene_document();

        std::map<std::string, SpawnedObjectSceneSpec> snapshot;
        std::vector<SceneEntityId> prior_ids;
        {
            const std::vector<PhysicsObjectSceneEntity>& objects = document.objects();
            for (std::size_t i = 0; i < objects.size(); ++i)
            {
                if (objects[i].record.sync_id != sync_id)
                {
                    continue;
                }
                snapshot[objects[i].record.name] = objects[i].object_spec;
                if (!partial || incoming_names.find(objects[i].record.name) != incoming_names.end())
                {
                    prior_ids.push_back(objects[i].record.id);
                }
            }
        }

        for (std::size_t i = 0; i < prior_ids.size(); ++i)
        {
            controller.select_entity(prior_ids[i], SceneEntityKindPhysicsObject);
            controller.delete_selected_entity();
        }

        std::set<SceneEntityId> before_ids;
        {
            const std::vector<PhysicsObjectSceneEntity>& objects = document.objects();
            for (std::size_t i = 0; i < objects.size(); ++i)
            {
                before_ids.insert(objects[i].record.id);
            }
        }

        if (!controller.import_physics_systems(systems, selected, &error))
        {
            return result_error("sync_physics", error.empty() ? "import_physics_systems failed" : error);
        }

        int matched = 0;
        int added = 0;
        std::set<std::string> new_names;
        {
            std::vector<PhysicsObjectSceneEntity>& objects = document.objects();
            for (std::size_t i = 0; i < objects.size(); ++i)
            {
                PhysicsObjectSceneEntity& object = objects[i];
                if (before_ids.find(object.record.id) != before_ids.end())
                {
                    continue;
                }
                object.record.sync_id = sync_id;
                new_names.insert(object.record.name);

                std::map<std::string, SpawnedObjectSceneSpec>::const_iterator found =
                    snapshot.find(object.record.name);
                if (found != snapshot.end())
                {
                    for (int axis = 0; axis < 3; ++axis)
                    {
                        object.object_spec.position[axis] = found->second.position[axis];
                        object.object_spec.rotation_degrees[axis] = found->second.rotation_degrees[axis];
                        object.object_spec.scale[axis] = found->second.scale[axis];
                    }
                    ++matched;
                }
                else
                {
                    ++added;
                }
            }
        }

        controller.reset();

        int removed = 0;
        if (!partial)
        {
            for (std::map<std::string, SpawnedObjectSceneSpec>::const_iterator it = snapshot.begin();
                 it != snapshot.end(); ++it)
            {
                if (new_names.find(it->first) == new_names.end())
                {
                    ++removed;
                }
            }
        }

        JsonValue r = result_base("sync_physics", true);
        r.set("sync_id", JsonValue(sync_id));
        r.set("partial", JsonValue(partial));
        r.set("systems_available", JsonValue(static_cast<int>(systems.size())));
        r.set("object_count", JsonValue(controller.spawned_object_count()));
        r.set("matched", JsonValue(matched));
        r.set("added", JsonValue(added));
        r.set("removed", JsonValue(removed));
        return r;
    }

    JsonValue cmd_sync_ragdoll(SimulationController& controller, const JsonValue& cmd)
    {
        const std::string path = cmd.member_string("path");
        if (path.empty())
        {
            return result_error("sync_ragdoll", "missing 'path'");
        }
        const std::string sync_id = cmd.member_string("sync_id", "dow2_ragdoll");

        SceneDocument& document = controller.scene_document();

        bool have_snapshot = false;
        float preserved_position[3] = { 0.0f, 0.0f, 0.0f };
        std::vector<SceneEntityId> prior_ids;
        {
            const std::vector<RagdollSceneEntity>& ragdolls = document.ragdolls();
            for (std::size_t i = 0; i < ragdolls.size(); ++i)
            {
                if (ragdolls[i].record.sync_id == sync_id)
                {
                    if (!have_snapshot)
                    {
                        preserved_position[0] = ragdolls[i].ragdoll.position[0];
                        preserved_position[1] = ragdolls[i].ragdoll.position[1];
                        preserved_position[2] = ragdolls[i].ragdoll.position[2];
                        have_snapshot = true;
                    }
                    prior_ids.push_back(ragdolls[i].record.id);
                }
            }
        }

        for (std::size_t i = 0; i < prior_ids.size(); ++i)
        {
            controller.select_entity(prior_ids[i], SceneEntityKindRagdoll);
            controller.delete_selected_entity();
        }

        std::string error;
        if (!controller.load_ragdoll(path.c_str(), &error))
        {
            return result_error("sync_ragdoll", error.empty() ? "load_ragdoll failed" : error);
        }

        const SceneEntityId new_id = last_ragdoll_id(controller);
        {
            std::vector<RagdollSceneEntity>& ragdolls = document.ragdolls();
            for (std::size_t i = 0; i < ragdolls.size(); ++i)
            {
                if (ragdolls[i].record.id == new_id)
                {
                    ragdolls[i].record.sync_id = sync_id;
                    break;
                }
            }
        }

        int matched = 0;
        if (have_snapshot)
        {
            controller.set_ragdoll_start_position(
                preserved_position[0], preserved_position[1], preserved_position[2]);
            matched = 1;
        }

        controller.reset();

        JsonValue r = result_base("sync_ragdoll", true);
        r.set("sync_id", JsonValue(sync_id));
        r.set("id", JsonValue(static_cast<int>(new_id)));
        r.set("ragdoll_count", JsonValue(controller.ragdoll_count()));
        r.set("matched", JsonValue(matched));
        r.set("added", JsonValue(matched == 1 ? 0 : 1));
        r.set("removed", JsonValue(static_cast<int>(prior_ids.size())));
        return r;
    }
}