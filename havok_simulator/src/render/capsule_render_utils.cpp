#include "capsule_render_utils.h"

#include <cmath>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>

namespace
{
    const float kPi = 3.14159265f;
    const float kTwoPi = kPi * 2.0f;

    void set_vector(float vector[3], float x, float y, float z)
    {
        vector[0] = x;
        vector[1] = y;
        vector[2] = z;
    }

    void normalize_vector(float vector[3])
    {
        const float length = std::sqrt(
            vector[0] * vector[0] +
            vector[1] * vector[1] +
            vector[2] * vector[2]);

        if (length <= 0.0f)
        {
            return;
        }

        vector[0] /= length;
        vector[1] /= length;
        vector[2] /= length;
    }

    void cross_product(const float left[3], const float right[3], float result[3])
    {
        result[0] = left[1] * right[2] - left[2] * right[1];
        result[1] = left[2] * right[0] - left[0] * right[2];
        result[2] = left[0] * right[1] - left[1] * right[0];
    }

    void add_scaled_vector(const float source[3], const float direction[3], float scale, float result[3])
    {
        result[0] = source[0] + direction[0] * scale;
        result[1] = source[1] + direction[1] * scale;
        result[2] = source[2] + direction[2] * scale;
    }

    void combine_basis_vectors(
        const float axis[3],
        float axis_scale,
        const float side[3],
        float side_scale,
        const float up[3],
        float up_scale,
        float result[3])
    {
        result[0] = axis[0] * axis_scale + side[0] * side_scale + up[0] * up_scale;
        result[1] = axis[1] * axis_scale + side[1] * side_scale + up[1] * up_scale;
        result[2] = axis[2] * axis_scale + side[2] * side_scale + up[2] * up_scale;
    }

    void emit_capsule_ring_vertex(
        const CapsuleRenderFrame& frame,
        const float center[3],
        float sin_theta,
        float cos_theta,
        float angle,
        float axis_sign,
        bool emit_normal)
    {
        float radial_unit[3];
        float normal[3];
        float point[3];

        combine_basis_vectors(frame.axis, 0.0f, frame.side, std::cos(angle), frame.up, std::sin(angle), radial_unit);
        combine_basis_vectors(frame.axis, axis_sign * cos_theta, frame.side, sin_theta * std::cos(angle), frame.up, sin_theta * std::sin(angle), normal);
        add_scaled_vector(center, normal, frame.radius, point);

        if (emit_normal)
        {
            glNormal3f(normal[0], normal[1], normal[2]);
        }
        glVertex3f(point[0], point[1], point[2]);
    }

    void emit_capsule_pole(const CapsuleRenderFrame& frame, const float center[3], float axis_sign, bool emit_normal)
    {
        float point[3];

        add_scaled_vector(center, frame.axis, axis_sign * frame.radius, point);
        if (emit_normal)
        {
            glNormal3f(frame.axis[0] * axis_sign, frame.axis[1] * axis_sign, frame.axis[2] * axis_sign);
        }
        glVertex3f(point[0], point[1], point[2]);
    }
}

bool build_capsule_render_frame(const BodyRenderState& body, CapsuleRenderFrame* frame)
{
    float reference[3];
    float axis_length = 0.0f;

    if (!frame || body.radius <= 0.0f)
    {
        return false;
    }

    set_vector(frame->center_a, body.capsule_vertices[0], body.capsule_vertices[1], body.capsule_vertices[2]);
    set_vector(frame->center_b, body.capsule_vertices[3], body.capsule_vertices[4], body.capsule_vertices[5]);
    set_vector(
        frame->axis,
        frame->center_b[0] - frame->center_a[0],
        frame->center_b[1] - frame->center_a[1],
        frame->center_b[2] - frame->center_a[2]);
    axis_length = std::sqrt(
        frame->axis[0] * frame->axis[0] +
        frame->axis[1] * frame->axis[1] +
        frame->axis[2] * frame->axis[2]);

    if (axis_length <= 0.001f)
    {
        set_vector(frame->axis, 0.0f, 1.0f, 0.0f);
    }
    else
    {
        frame->axis[0] /= axis_length;
        frame->axis[1] /= axis_length;
        frame->axis[2] /= axis_length;
    }

    if (std::fabs(frame->axis[2]) < 0.999f)
    {
        set_vector(reference, 0.0f, 0.0f, 1.0f);
    }
    else
    {
        set_vector(reference, 1.0f, 0.0f, 0.0f);
    }

    cross_product(frame->axis, reference, frame->side);
    normalize_vector(frame->side);
    cross_product(frame->side, frame->axis, frame->up);
    normalize_vector(frame->up);
    frame->radius = body.radius;
    return true;
}

void draw_capsule_wireframe_geometry(const CapsuleRenderFrame& frame, bool is_preview)
{
    const int ring_segments = 20;
    const int cap_rings = 5;
    const int meridians = 6;
    int ring_index = 0;
    int segment_index = 0;
    int meridian_index = 0;

    glLineWidth(is_preview ? 2.0f : 1.25f);

    for (ring_index = 1; ring_index <= cap_rings; ++ring_index)
    {
        const float theta = (static_cast<float>(ring_index) / static_cast<float>(cap_rings)) * (kPi * 0.5f);
        const float sin_theta = std::sin(theta);
        const float cos_theta = std::cos(theta);

        glBegin(GL_LINE_LOOP);
        for (segment_index = 0; segment_index < ring_segments; ++segment_index)
        {
            const float angle = (static_cast<float>(segment_index) / static_cast<float>(ring_segments)) * kTwoPi;
            emit_capsule_ring_vertex(frame, frame.center_a, sin_theta, cos_theta, angle, -1.0f, false);
        }
        glEnd();

        glBegin(GL_LINE_LOOP);
        for (segment_index = 0; segment_index < ring_segments; ++segment_index)
        {
            const float angle = (static_cast<float>(segment_index) / static_cast<float>(ring_segments)) * kTwoPi;
            emit_capsule_ring_vertex(frame, frame.center_b, sin_theta, cos_theta, angle, 1.0f, false);
        }
        glEnd();
    }

    for (meridian_index = 0; meridian_index < meridians; ++meridian_index)
    {
        const float angle = (static_cast<float>(meridian_index) / static_cast<float>(meridians)) * kTwoPi;

        glBegin(GL_LINE_STRIP);
        emit_capsule_pole(frame, frame.center_a, -1.0f, false);
        for (ring_index = 1; ring_index <= cap_rings; ++ring_index)
        {
            const float theta = (static_cast<float>(ring_index) / static_cast<float>(cap_rings)) * (kPi * 0.5f);
            emit_capsule_ring_vertex(frame, frame.center_a, std::sin(theta), std::cos(theta), angle, -1.0f, false);
        }
        for (ring_index = cap_rings; ring_index >= 1; --ring_index)
        {
            const float theta = (static_cast<float>(ring_index) / static_cast<float>(cap_rings)) * (kPi * 0.5f);
            emit_capsule_ring_vertex(frame, frame.center_b, std::sin(theta), std::cos(theta), angle, 1.0f, false);
        }
        emit_capsule_pole(frame, frame.center_b, 1.0f, false);
        glEnd();
    }
}

void draw_capsule_solid_geometry(const CapsuleRenderFrame& frame)
{
    const int ring_segments = 20;
    const int cap_rings = 7;
    int segment_index = 0;
    int ring_index = 0;

    glShadeModel(GL_FLAT);

    glBegin(GL_QUAD_STRIP);
    for (segment_index = 0; segment_index <= ring_segments; ++segment_index)
    {
        const float angle = (static_cast<float>(segment_index % ring_segments) / static_cast<float>(ring_segments)) * kTwoPi;
        const float cos_angle = std::cos(angle);
        const float sin_angle = std::sin(angle);
        const float side_scale = cos_angle * frame.radius;
        const float up_scale = sin_angle * frame.radius;
        float normal[3];
        float point_a[3];
        float point_b[3];

        combine_basis_vectors(frame.axis, 0.0f, frame.side, cos_angle, frame.up, sin_angle, normal);
        add_scaled_vector(frame.center_a, frame.side, side_scale, point_a);
        add_scaled_vector(point_a, frame.up, up_scale, point_a);
        add_scaled_vector(frame.center_b, frame.side, side_scale, point_b);
        add_scaled_vector(point_b, frame.up, up_scale, point_b);

        glNormal3f(normal[0], normal[1], normal[2]);
        glVertex3f(point_a[0], point_a[1], point_a[2]);
        glNormal3f(normal[0], normal[1], normal[2]);
        glVertex3f(point_b[0], point_b[1], point_b[2]);
    }
    glEnd();

    glBegin(GL_TRIANGLE_FAN);
    emit_capsule_pole(frame, frame.center_a, -1.0f, true);
    for (segment_index = ring_segments; segment_index >= 0; --segment_index)
    {
        const float angle = (static_cast<float>(segment_index % ring_segments) / static_cast<float>(ring_segments)) * kTwoPi;
        emit_capsule_ring_vertex(frame, frame.center_a, std::sin(kPi * 0.5f / static_cast<float>(cap_rings)), std::cos(kPi * 0.5f / static_cast<float>(cap_rings)), angle, -1.0f, true);
    }
    glEnd();

    for (ring_index = 1; ring_index < cap_rings; ++ring_index)
    {
        const float current_theta = (static_cast<float>(ring_index) / static_cast<float>(cap_rings)) * (kPi * 0.5f);
        const float next_theta = (static_cast<float>(ring_index + 1) / static_cast<float>(cap_rings)) * (kPi * 0.5f);

        glBegin(GL_QUAD_STRIP);
        for (segment_index = 0; segment_index <= ring_segments; ++segment_index)
        {
            const float angle = (static_cast<float>(segment_index % ring_segments) / static_cast<float>(ring_segments)) * kTwoPi;
            emit_capsule_ring_vertex(frame, frame.center_a, std::sin(current_theta), std::cos(current_theta), angle, -1.0f, true);
            emit_capsule_ring_vertex(frame, frame.center_a, std::sin(next_theta), std::cos(next_theta), angle, -1.0f, true);
        }
        glEnd();
    }

    for (ring_index = cap_rings - 1; ring_index >= 1; --ring_index)
    {
        const float current_theta = (static_cast<float>(ring_index + 1) / static_cast<float>(cap_rings)) * (kPi * 0.5f);
        const float next_theta = (static_cast<float>(ring_index) / static_cast<float>(cap_rings)) * (kPi * 0.5f);

        glBegin(GL_QUAD_STRIP);
        for (segment_index = 0; segment_index <= ring_segments; ++segment_index)
        {
            const float angle = (static_cast<float>(segment_index % ring_segments) / static_cast<float>(ring_segments)) * kTwoPi;
            emit_capsule_ring_vertex(frame, frame.center_b, std::sin(current_theta), std::cos(current_theta), angle, 1.0f, true);
            emit_capsule_ring_vertex(frame, frame.center_b, std::sin(next_theta), std::cos(next_theta), angle, 1.0f, true);
        }
        glEnd();
    }

    glBegin(GL_TRIANGLE_FAN);
    emit_capsule_pole(frame, frame.center_b, 1.0f, true);
    for (segment_index = 0; segment_index <= ring_segments; ++segment_index)
    {
        const float angle = (static_cast<float>(segment_index % ring_segments) / static_cast<float>(ring_segments)) * kTwoPi;
        emit_capsule_ring_vertex(frame, frame.center_b, std::sin(kPi * 0.5f / static_cast<float>(cap_rings)), std::cos(kPi * 0.5f / static_cast<float>(cap_rings)), angle, 1.0f, true);
    }
    glEnd();
}