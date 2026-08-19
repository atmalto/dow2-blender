#ifndef HAVOK_SCENE_APP_CAPSULE_RENDER_UTILS_H
#define HAVOK_SCENE_APP_CAPSULE_RENDER_UTILS_H

#include "body_render_state.h"

struct CapsuleRenderFrame
{
    float center_a[3];
    float center_b[3];
    float axis[3];
    float side[3];
    float up[3];
    float radius;
};

bool build_capsule_render_frame(const BodyRenderState& body, CapsuleRenderFrame* frame);
void draw_capsule_wireframe_geometry(const CapsuleRenderFrame& frame, bool is_preview);
void draw_capsule_solid_geometry(const CapsuleRenderFrame& frame);

#endif