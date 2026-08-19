#ifndef HAVOK_SCENE_APP_BODY_RENDER_STATE_H
#define HAVOK_SCENE_APP_BODY_RENDER_STATE_H

#include <vector>

#include "scene_entity.h"

struct BodyRenderState
{
    enum ShapeType
    {
        ShapeBox,
        ShapeSphere,
        ShapeCapsule,
        ShapeWedge,
        ShapeConvexHull,
        ShapeArrow
    };

    ShapeType shape_type;
    bool is_dynamic;
    bool is_solid;
    bool is_preview;
    SceneEntityId entity_id;
    SceneEntityKind entity_kind;
    bool is_selected;
    float position[3];
    float rotation[4];
    float half_extents[3];
    float capsule_vertices[6];
    float radius;
    float color[3];
    std::vector<float> mesh_vertices;
};

#endif