#ifndef HAVOK_SCENE_APP_SCENE_BODY_RENDERER_H
#define HAVOK_SCENE_APP_SCENE_BODY_RENDERER_H

#include "body_render_state.h"

class SceneBodyRenderer
{
public:
    static void draw_body(const BodyRenderState& body);
    static void draw_body_geometry(const BodyRenderState& body, bool use_body_color = true);
    static void draw_wireframe_overlay(const BodyRenderState& body);
    static void draw_selection_overlay(const BodyRenderState& body);
    static void apply_body_transform(const BodyRenderState& body);

private:
    static void draw_box(const BodyRenderState& body, bool use_body_color);
    static void draw_sphere(const BodyRenderState& body, bool use_body_color);
    static void draw_capsule(const BodyRenderState& body, bool use_body_color);
    static void draw_wedge(const BodyRenderState& body, bool use_body_color);
    static void draw_convex_hull(const BodyRenderState& body, bool use_body_color);
    static void draw_arrow(const BodyRenderState& body, bool use_body_color);
};

#endif