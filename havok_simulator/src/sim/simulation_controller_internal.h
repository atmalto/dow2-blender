#ifndef HAVOK_SCENE_APP_SIMULATION_CONTROLLER_INTERNAL_H
#define HAVOK_SCENE_APP_SIMULATION_CONTROLLER_INTERNAL_H

#include <sstream>
#include <string>
#include <vector>

#include "scene_document.h"

namespace simulation_controller_internal
{
    inline bool fail(std::string* error_message, const char* message)
    {
        if (error_message)
        {
            *error_message = message;
        }
        return false;
    }

    inline bool require_selected_kind(
        const SceneDocument& scene_document,
        SceneEntityKind expected_kind,
        const char* message,
        SceneEntitySelection* selected,
        std::string* error_message)
    {
        const SceneEntitySelection current = scene_document.selected_entity();
        if (current.kind != expected_kind)
        {
            return fail(error_message, message);
        }
        if (selected)
        {
            *selected = current;
        }
        return true;
    }

    inline bool require_authoring_selection(
        const SceneDocument& scene_document,
        bool can_author_scene,
        SceneEntityKind expected_kind,
        const char* message,
        SceneEntitySelection* selected,
        std::string* error_message)
    {
        if (!can_author_scene)
        {
            return fail(error_message, message);
        }
        return require_selected_kind(scene_document, expected_kind, message, selected, error_message);
    }

    inline std::string make_numbered_name(const char* prefix, SceneEntityId id)
    {
        std::ostringstream stream;
        stream << prefix << " " << id;
        return stream.str();
    }

    template <typename Entity>
    inline const Entity* find_entity_by_id(const std::vector<Entity>& entities, SceneEntityId entity_id)
    {
        std::size_t entity_index = 0;
        for (entity_index = 0; entity_index < entities.size(); ++entity_index)
        {
            if (entities[entity_index].record.id == entity_id)
            {
                return &entities[entity_index];
            }
        }
        return 0;
    }

    template <typename Entity>
    inline Entity* find_entity_by_id(std::vector<Entity>& entities, SceneEntityId entity_id)
    {
        std::size_t entity_index = 0;
        for (entity_index = 0; entity_index < entities.size(); ++entity_index)
        {
            if (entities[entity_index].record.id == entity_id)
            {
                return &entities[entity_index];
            }
        }
        return 0;
    }
}

#endif