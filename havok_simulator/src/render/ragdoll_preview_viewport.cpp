#include "ragdoll_preview_viewport.h"

#include <algorithm>
#include <cmath>

#include <QColor>
#include <QMouseEvent>
#include <QWheelEvent>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>
#include <GL/glu.h>

#include "capsule_render_utils.h"
#include "scene_body_renderer.h"

namespace
{
    const float kRadiansPerDegree = 0.0174532925f;
    const float kVerticalFovTangent = 0.08f;
    const float kAxisProjectionEpsilon = 0.0001f;

    struct CameraBasis
    {
        float position[3];
        float forward[3];
        float right[3];
        float up[3];
    };

    const std::vector<RagdollPreviewBone>& active_bones_for_kind(const RagdollPreviewData& preview_data, RagdollPreviewSkeletonKind skeleton_kind)
    {
        return skeleton_kind == RagdollPreviewSkeletonAnimation
            ? preview_data.animation_bones
            : preview_data.bones;
    }

    void expand_bounds(float point_x, float point_y, float point_z, bool* has_bounds, float* min_x, float* max_x, float* min_y, float* max_y, float* min_z, float* max_z)
    {
        if (!has_bounds || !min_x || !max_x || !min_y || !max_y || !min_z || !max_z)
        {
            return;
        }

        if (!*has_bounds)
        {
            *min_x = *max_x = point_x;
            *min_y = *max_y = point_y;
            *min_z = *max_z = point_z;
            *has_bounds = true;
            return;
        }

        *min_x = (std::min)(*min_x, point_x);
        *max_x = (std::max)(*max_x, point_x);
        *min_y = (std::min)(*min_y, point_y);
        *max_y = (std::max)(*max_y, point_y);
        *min_z = (std::min)(*min_z, point_z);
        *max_z = (std::max)(*max_z, point_z);
    }

    void expand_bounds_for_bones(const std::vector<RagdollPreviewBone>& bones, bool* has_bounds, float* min_x, float* max_x, float* min_y, float* max_y, float* min_z, float* max_z)
    {
        for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
        {
            const RagdollPreviewBone& bone = bones[bone_index];
            expand_bounds(
                bone.translation[0],
                bone.translation[1],
                bone.translation[2],
                has_bounds,
                min_x,
                max_x,
                min_y,
                max_y,
                min_z,
                max_z);
        }
    }

    void expand_bounds_for_bodies(const std::vector<RagdollPreviewBody>& bodies, bool* has_bounds, float* min_x, float* max_x, float* min_y, float* max_y, float* min_z, float* max_z)
    {
        for (std::size_t body_index = 0; body_index < bodies.size(); ++body_index)
        {
            const RagdollPreviewBody& body = bodies[body_index];
            expand_bounds(
                body.position[0],
                body.position[1],
                body.position[2],
                has_bounds,
                min_x,
                max_x,
                min_y,
                max_y,
                min_z,
                max_z);
        }
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

    float dot_product(const float left[3], const float right[3])
    {
        return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
    }

    void rotate_vector_by_quaternion(const float quaternion[4], const float input[3], float output[3])
    {
        const float x = quaternion[0];
        const float y = quaternion[1];
        const float z = quaternion[2];
        const float w = quaternion[3];
        const float xx = x * x;
        const float yy = y * y;
        const float zz = z * z;
        const float xy = x * y;
        const float xz = x * z;
        const float yz = y * z;
        const float wx = w * x;
        const float wy = w * y;
        const float wz = w * z;

        output[0] = (1.0f - 2.0f * (yy + zz)) * input[0] + (2.0f * (xy - wz)) * input[1] + (2.0f * (xz + wy)) * input[2];
        output[1] = (2.0f * (xy + wz)) * input[0] + (1.0f - 2.0f * (xx + zz)) * input[1] + (2.0f * (yz - wx)) * input[2];
        output[2] = (2.0f * (xz - wy)) * input[0] + (2.0f * (yz + wx)) * input[1] + (1.0f - 2.0f * (xx + yy)) * input[2];
    }

    void transform_local_point(const BodyRenderState& body, const float local_point[3], float world_point[3])
    {
        rotate_vector_by_quaternion(body.rotation, local_point, world_point);
        world_point[0] += body.position[0];
        world_point[1] += body.position[1];
        world_point[2] += body.position[2];
    }

    bool distance_squared_between_ray_and_segment(
        const float ray_origin[3],
        const float ray_direction[3],
        const float segment_start[3],
        const float segment_end[3],
        float* ray_distance,
        float* distance_squared)
    {
        const float epsilon = 1.0e-5f;
        const float u[3] = { ray_direction[0], ray_direction[1], ray_direction[2] };
        const float v[3] = {
            segment_end[0] - segment_start[0],
            segment_end[1] - segment_start[1],
            segment_end[2] - segment_start[2]
        };
        const float w[3] = {
            ray_origin[0] - segment_start[0],
            ray_origin[1] - segment_start[1],
            ray_origin[2] - segment_start[2]
        };
        const float a = dot_product(u, u);
        const float b = dot_product(u, v);
        const float c = dot_product(v, v);
        const float d = dot_product(u, w);
        const float e = dot_product(v, w);
        const float determinant = a * c - b * b;
        float ray_numerator = 0.0f;
        float ray_denominator = determinant;
        float segment_numerator = 0.0f;
        float segment_denominator = determinant;
        float ray_parameter = 0.0f;
        float segment_parameter = 0.0f;
        float closest_delta[3];

        if (c <= epsilon)
        {
            ray_parameter = -d / a;
            if (ray_parameter < 0.0f)
            {
                ray_parameter = 0.0f;
            }

            closest_delta[0] = w[0] + ray_parameter * u[0];
            closest_delta[1] = w[1] + ray_parameter * u[1];
            closest_delta[2] = w[2] + ray_parameter * u[2];

            if (ray_distance)
            {
                *ray_distance = ray_parameter;
            }
            if (distance_squared)
            {
                *distance_squared = dot_product(closest_delta, closest_delta);
            }
            return true;
        }

        if (determinant <= epsilon)
        {
            ray_numerator = 0.0f;
            ray_denominator = 1.0f;
            segment_numerator = e;
            segment_denominator = c;
        }
        else
        {
            ray_numerator = b * e - c * d;
            segment_numerator = a * e - b * d;

            if (ray_numerator < 0.0f)
            {
                ray_numerator = 0.0f;
                ray_denominator = 1.0f;
                segment_numerator = e;
                segment_denominator = c;
            }
        }

        segment_parameter = segment_denominator > epsilon ? segment_numerator / segment_denominator : 0.0f;
        if (segment_parameter < 0.0f)
        {
            segment_parameter = 0.0f;
        }
        if (segment_parameter > 1.0f)
        {
            segment_parameter = 1.0f;
        }

        if (segment_parameter <= epsilon)
        {
            ray_parameter = -d / a;
        }
        else if (segment_parameter >= 1.0f - epsilon)
        {
            ray_parameter = (b - d) / a;
        }
        else
        {
            ray_parameter = ray_denominator > epsilon ? ray_numerator / ray_denominator : 0.0f;
        }

        if (ray_parameter < 0.0f)
        {
            ray_parameter = 0.0f;
            segment_parameter = e / c;
            if (segment_parameter < 0.0f)
            {
                segment_parameter = 0.0f;
            }
            if (segment_parameter > 1.0f)
            {
                segment_parameter = 1.0f;
            }
        }

        closest_delta[0] = w[0] + ray_parameter * u[0] - segment_parameter * v[0];
        closest_delta[1] = w[1] + ray_parameter * u[1] - segment_parameter * v[1];
        closest_delta[2] = w[2] + ray_parameter * u[2] - segment_parameter * v[2];

        if (ray_distance)
        {
            *ray_distance = ray_parameter;
        }
        if (distance_squared)
        {
            *distance_squared = dot_product(closest_delta, closest_delta);
        }
        return true;
    }

    bool distance_squared_between_ray_and_point(
        const float ray_origin[3],
        const float ray_direction[3],
        const float point[3],
        float* ray_distance,
        float* distance_squared)
    {
        float delta[3] = {
            point[0] - ray_origin[0],
            point[1] - ray_origin[1],
            point[2] - ray_origin[2]
        };
        float projection = dot_product(delta, ray_direction);
        float closest[3];

        if (projection < 0.0f)
        {
            projection = 0.0f;
        }

        closest[0] = ray_origin[0] + ray_direction[0] * projection;
        closest[1] = ray_origin[1] + ray_direction[1] * projection;
        closest[2] = ray_origin[2] + ray_direction[2] * projection;
        closest[0] = point[0] - closest[0];
        closest[1] = point[1] - closest[1];
        closest[2] = point[2] - closest[2];

        if (ray_distance)
        {
            *ray_distance = projection;
        }
        if (distance_squared)
        {
            *distance_squared = dot_product(closest, closest);
        }
        return true;
    }

    void build_arrow_basis(const float direction[3], float side[3], float up[3])
    {
        float reference[3] = { 0.0f, 1.0f, 0.0f };

        if (std::fabs(direction[1]) > 0.95f)
        {
            reference[0] = 1.0f;
            reference[1] = 0.0f;
            reference[2] = 0.0f;
        }

        cross_product(direction, reference, side);
        normalize_vector(side);
        cross_product(side, direction, up);
        normalize_vector(up);
    }

    CameraBasis compute_camera_basis(const float target[3], float distance, float yaw_degrees, float pitch_degrees)
    {
        CameraBasis basis;
        const float yaw_radians = yaw_degrees * kRadiansPerDegree;
        const float pitch_radians = pitch_degrees * kRadiansPerDegree;
        const float cos_yaw = std::cos(yaw_radians);
        const float sin_yaw = std::sin(yaw_radians);
        const float cos_pitch = std::cos(pitch_radians);
        const float sin_pitch = std::sin(pitch_radians);
        const float world_up[3] = { 0.0f, 1.0f, 0.0f };

        basis.position[0] = target[0] + sin_yaw * cos_pitch * distance;
        basis.position[1] = target[1] + sin_pitch * distance;
        basis.position[2] = target[2] + cos_yaw * cos_pitch * distance;

        basis.forward[0] = target[0] - basis.position[0];
        basis.forward[1] = target[1] - basis.position[1];
        basis.forward[2] = target[2] - basis.position[2];
        normalize_vector(basis.forward);

        cross_product(basis.forward, world_up, basis.right);
        normalize_vector(basis.right);

        cross_product(basis.right, basis.forward, basis.up);
        normalize_vector(basis.up);

        return basis;
    }
}

RagdollPreviewViewport::RagdollPreviewViewport(QWidget* parent)
    : QGLWidget(parent)
    , m_is_orbiting(false)
    , m_is_panning(false)
    , m_pending_selection_click(false)
    , m_selected_bone_index(-1)
    , m_active_skeleton_kind(RagdollPreviewSkeletonAnimation)
    , m_camera_distance(20.0f)
    , m_camera_yaw_degrees(-28.0f)
    , m_camera_pitch_degrees(18.0f)
{
    setMinimumSize(480, 360);
    setFocusPolicy(Qt::StrongFocus);
    setMouseTracking(true);

    m_camera_target[0] = 0.0f;
    m_camera_target[1] = 2.0f;
    m_camera_target[2] = 0.0f;
}

void RagdollPreviewViewport::set_preview_data(const RagdollPreviewData& preview_data)
{
    m_preview_data = preview_data;
    if (m_selected_bone_index >= static_cast<int>(active_bones_for_kind(m_preview_data, m_active_skeleton_kind).size()))
    {
        m_selected_bone_index = -1;
    }
    frame_preview();
    updateGL();
}

void RagdollPreviewViewport::clear_preview_data()
{
    m_preview_data = RagdollPreviewData();
    m_selected_bone_index = -1;
    m_camera_target[0] = 0.0f;
    m_camera_target[1] = 2.0f;
    m_camera_target[2] = 0.0f;
    m_camera_distance = 20.0f;
    updateGL();
}

void RagdollPreviewViewport::set_selected_bone_index(int bone_index)
{
    m_selected_bone_index = bone_index;
    updateGL();
}

void RagdollPreviewViewport::set_active_skeleton_kind(RagdollPreviewSkeletonKind skeleton_kind)
{
    m_active_skeleton_kind = skeleton_kind;
    if (m_selected_bone_index >= static_cast<int>(active_bones_for_kind(m_preview_data, m_active_skeleton_kind).size()))
    {
        m_selected_bone_index = -1;
    }
    updateGL();
}

void RagdollPreviewViewport::initializeGL()
{
    qglClearColor(QColor(26, 29, 34));
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
}

void RagdollPreviewViewport::resizeGL(int width, int height)
{
    glViewport(0, 0, width, height);

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    const float aspect_ratio = height > 0 ? static_cast<float>(width) / static_cast<float>(height) : 1.0f;
    const float near_plane = 0.1f;
    const float far_plane = 200.0f;
    const float top = 0.08f * near_plane;
    const float right = top * aspect_ratio;

    glFrustum(-right, right, -top, top, near_plane, far_plane);
    glMatrixMode(GL_MODELVIEW);
}

void RagdollPreviewViewport::paintGL()
{
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    apply_camera_transform();

    draw_grid();
    draw_axes();
    draw_bone_hierarchy();

    for (std::size_t body_index = 0; body_index < m_preview_data.bodies.size(); ++body_index)
    {
        if (m_preview_data.bodies[body_index].has_render_state)
        {
            draw_body(m_preview_data.bodies[body_index].render_state);
        }
    }

    draw_body_labels();

    glDisable(GL_DEPTH_TEST);
    qglColor(QColor(220, 224, 230));
    renderText(18.0, 28.0, "Ragdoll Preview");
    renderText(18.0, 46.0,
        m_active_skeleton_kind == RagdollPreviewSkeletonAnimation
            ? "Animation skeleton  LMB drag orbit  RMB or MMB drag pan  Wheel zoom  Click bone to inspect"
            : "Ragdoll skeleton  LMB drag orbit  RMB or MMB drag pan  Wheel zoom  Click body or bone to inspect");
    glEnable(GL_DEPTH_TEST);
}

void RagdollPreviewViewport::mousePressEvent(QMouseEvent* event)
{
    m_last_mouse_pos = event->pos();

    if (event->button() == Qt::LeftButton)
    {
        m_left_press_pos = event->pos();
        m_is_orbiting = true;
        m_pending_selection_click = true;
    }
    else if (event->button() == Qt::RightButton || event->button() == Qt::MidButton)
    {
        m_is_panning = true;
    }
}

void RagdollPreviewViewport::mouseMoveEvent(QMouseEvent* event)
{
    const QPoint delta = event->pos() - m_last_mouse_pos;
    m_last_mouse_pos = event->pos();

    if (m_is_orbiting)
    {
        const QPoint click_delta = event->pos() - m_left_press_pos;
        if (m_pending_selection_click)
        {
            if (std::abs(click_delta.x()) > 3 || std::abs(click_delta.y()) > 3)
            {
                m_pending_selection_click = false;
                m_last_mouse_pos = event->pos();
            }
            else
            {
                return;
            }
        }

        m_camera_yaw_degrees -= static_cast<float>(delta.x()) * 0.45f;
        m_camera_pitch_degrees += static_cast<float>(delta.y()) * 0.35f;

        if (m_camera_pitch_degrees > 89.0f)
        {
            m_camera_pitch_degrees = 89.0f;
        }
        if (m_camera_pitch_degrees < -89.0f)
        {
            m_camera_pitch_degrees = -89.0f;
        }

        updateGL();
    }
    else if (m_is_panning)
    {
        const CameraBasis basis = compute_camera_basis(
            m_camera_target,
            m_camera_distance,
            m_camera_yaw_degrees,
            m_camera_pitch_degrees);
        const float half_vertical_span = m_camera_distance * kVerticalFovTangent;
        const float pixels_to_world = height() > 0
            ? (2.0f * half_vertical_span) / static_cast<float>(height())
            : 0.0f;
        const float pan_x = -static_cast<float>(delta.x()) * pixels_to_world;
        const float pan_y = static_cast<float>(delta.y()) * pixels_to_world;

        m_camera_target[0] += basis.right[0] * pan_x + basis.up[0] * pan_y;
        m_camera_target[1] += basis.right[1] * pan_x + basis.up[1] * pan_y;
        m_camera_target[2] += basis.right[2] * pan_x + basis.up[2] * pan_y;

        updateGL();
    }
}

void RagdollPreviewViewport::mouseReleaseEvent(QMouseEvent* event)
{
    if (event->button() == Qt::LeftButton)
    {
        if (m_pending_selection_click)
        {
            pick_body_at(event->pos());
        }
        m_is_orbiting = false;
        m_pending_selection_click = false;
    }
    else if (event->button() == Qt::RightButton || event->button() == Qt::MidButton)
    {
        m_is_panning = false;
    }
}

void RagdollPreviewViewport::wheelEvent(QWheelEvent* event)
{
    const float delta_steps = static_cast<float>(event->delta()) / 120.0f;
    m_camera_distance -= delta_steps * 1.5f;

    if (m_camera_distance < 2.5f)
    {
        m_camera_distance = 2.5f;
    }
    if (m_camera_distance > 400.0f)
    {
        m_camera_distance = 400.0f;
    }

    updateGL();
}

void RagdollPreviewViewport::apply_camera_transform()
{
    const CameraBasis basis = compute_camera_basis(
        m_camera_target,
        m_camera_distance,
        m_camera_yaw_degrees,
        m_camera_pitch_degrees);

    gluLookAt(
        basis.position[0], basis.position[1], basis.position[2],
        m_camera_target[0], m_camera_target[1], m_camera_target[2],
        basis.up[0], basis.up[1], basis.up[2]);
}

void RagdollPreviewViewport::frame_preview()
{
    bool has_bounds = false;
    float min_x = 0.0f;
    float max_x = 0.0f;
    float min_y = 0.0f;
    float max_y = 0.0f;
    float min_z = 0.0f;
    float max_z = 0.0f;

    expand_bounds_for_bones(m_preview_data.bones, &has_bounds, &min_x, &max_x, &min_y, &max_y, &min_z, &max_z);
    expand_bounds_for_bones(m_preview_data.animation_bones, &has_bounds, &min_x, &max_x, &min_y, &max_y, &min_z, &max_z);
    expand_bounds_for_bodies(m_preview_data.bodies, &has_bounds, &min_x, &max_x, &min_y, &max_y, &min_z, &max_z);

    if (!has_bounds)
    {
        m_camera_target[0] = 0.0f;
        m_camera_target[1] = 2.0f;
        m_camera_target[2] = 0.0f;
        m_camera_distance = 20.0f;
        return;
    }

    m_camera_target[0] = (min_x + max_x) * 0.5f;
    m_camera_target[1] = (min_y + max_y) * 0.5f;
    m_camera_target[2] = (min_z + max_z) * 0.5f;

    const float span_x = max_x - min_x;
    const float span_y = max_y - min_y;
    const float span_z = max_z - min_z;
    float max_span = span_x;
    if (span_y > max_span)
    {
        max_span = span_y;
    }
    if (span_z > max_span)
    {
        max_span = span_z;
    }

    if (max_span < 1.0f)
    {
        max_span = 1.0f;
    }

    m_camera_distance = max_span * 3.2f + 4.0f;
}

void RagdollPreviewViewport::draw_grid()
{
    const int half_extent = 12;

    glLineWidth(1.0f);
    glBegin(GL_LINES);

    for (int line = -half_extent; line <= half_extent; ++line)
    {
        if (line == 0)
        {
            glColor3f(0.32f, 0.35f, 0.40f);
        }
        else
        {
            glColor3f(0.17f, 0.19f, 0.22f);
        }

        glVertex3f(static_cast<float>(line), 0.0f, static_cast<float>(-half_extent));
        glVertex3f(static_cast<float>(line), 0.0f, static_cast<float>(half_extent));

        glVertex3f(static_cast<float>(-half_extent), 0.0f, static_cast<float>(line));
        glVertex3f(static_cast<float>(half_extent), 0.0f, static_cast<float>(line));
    }

    glEnd();
}

void RagdollPreviewViewport::draw_axes()
{
    glLineWidth(1.5f);
    glBegin(GL_LINES);

    glColor3f(0.82f, 0.29f, 0.29f);
    glVertex3f(0.0f, 0.0f, 0.0f);
    glVertex3f(4.0f, 0.0f, 0.0f);

    glColor3f(0.36f, 0.73f, 0.43f);
    glVertex3f(0.0f, 0.0f, 0.0f);
    glVertex3f(0.0f, 4.0f, 0.0f);

    glColor3f(0.35f, 0.58f, 0.86f);
    glVertex3f(0.0f, 0.0f, 0.0f);
    glVertex3f(0.0f, 0.0f, 4.0f);

    glEnd();
}

void RagdollPreviewViewport::draw_body(const BodyRenderState& body)
{
    BodyRenderState shaded_body = body;
    bool is_selected = false;
    const float body_alpha = 0.52f;
    const float selected_body_alpha = 0.70f;

    for (std::size_t body_index = 0; body_index < m_preview_data.bodies.size(); ++body_index)
    {
        if (&m_preview_data.bodies[body_index].render_state == &body)
        {
            is_selected = m_active_skeleton_kind == RagdollPreviewSkeletonRagdoll
                && m_preview_data.bodies[body_index].bone_index == m_selected_bone_index;
            break;
        }
    }

    shaded_body.is_preview = false;
    shaded_body.is_selected = false;
    shaded_body.is_solid = true;

    if (is_selected)
    {
        shaded_body.color[0] = shaded_body.color[0] + (1.0f - shaded_body.color[0]) * 0.40f;
        shaded_body.color[1] = shaded_body.color[1] + (0.92f - shaded_body.color[1]) * 0.40f;
        shaded_body.color[2] = shaded_body.color[2] + (0.36f - shaded_body.color[2]) * 0.40f;
    }

    glPushMatrix();
    SceneBodyRenderer::apply_body_transform(shaded_body);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDepthMask(GL_FALSE);

    glColor4f(shaded_body.color[0], shaded_body.color[1], shaded_body.color[2], is_selected ? selected_body_alpha : body_alpha);
    SceneBodyRenderer::draw_body_geometry(shaded_body, false);

    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);

    if (is_selected && shaded_body.shape_type == BodyRenderState::ShapeCapsule)
    {
        BodyRenderState overlay = shaded_body;
        overlay.is_solid = false;
        overlay.is_preview = true;
        overlay.color[0] = 1.0f;
        overlay.color[1] = 0.95f;
        overlay.color[2] = 0.45f;
        SceneBodyRenderer::draw_body_geometry(overlay);
    }

    glPopMatrix();
}

void RagdollPreviewViewport::draw_body_labels()
{
    const std::vector<RagdollPreviewBone>& bones = active_bones_for_kind(m_preview_data, m_active_skeleton_kind);

    for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
    {
        const RagdollPreviewBone& bone = bones[bone_index];
        float label_position[3] = {
            bone.translation[0],
            bone.translation[1] + 0.14f,
            bone.translation[2]
        };

        qglColor(static_cast<int>(bone_index) == m_selected_bone_index
            ? QColor(255, 244, 120)
            : QColor(220, 224, 230));
        renderText(
            label_position[0],
            label_position[1],
            label_position[2],
            QString::fromLocal8Bit(bone.name.c_str()));
    }
}

void RagdollPreviewViewport::draw_bone_hierarchy()
{
    const std::vector<RagdollPreviewBone>& bones = active_bones_for_kind(m_preview_data, m_active_skeleton_kind);

    for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
    {
        const RagdollPreviewBone& bone = bones[bone_index];
        float direction[3];
        float length = 0.0f;
        float side[3];
        float up[3];
        float arrow_base[3];
        float arrow_left[3];
        float arrow_right[3];
        float arrow_length = 0.0f;
        float arrow_width = 0.0f;

        if (bone.parent_index < 0 || bone.parent_index >= static_cast<int>(bones.size()))
        {
            continue;
        }

        const RagdollPreviewBone& parent = bones[bone.parent_index];
        direction[0] = bone.translation[0] - parent.translation[0];
        direction[1] = bone.translation[1] - parent.translation[1];
        direction[2] = bone.translation[2] - parent.translation[2];
        length = std::sqrt(direction[0] * direction[0] + direction[1] * direction[1] + direction[2] * direction[2]);

        if (length <= kAxisProjectionEpsilon)
        {
            continue;
        }

        direction[0] /= length;
        direction[1] /= length;
        direction[2] /= length;
        build_arrow_basis(direction, side, up);

        arrow_length = length * 0.18f;
        if (arrow_length < 0.04f)
        {
            arrow_length = 0.04f;
        }
        arrow_width = arrow_length * 0.55f;

        arrow_base[0] = bone.translation[0] - direction[0] * arrow_length;
        arrow_base[1] = bone.translation[1] - direction[1] * arrow_length;
        arrow_base[2] = bone.translation[2] - direction[2] * arrow_length;
        arrow_left[0] = arrow_base[0] + side[0] * arrow_width;
        arrow_left[1] = arrow_base[1] + side[1] * arrow_width;
        arrow_left[2] = arrow_base[2] + side[2] * arrow_width;
        arrow_right[0] = arrow_base[0] - side[0] * arrow_width;
        arrow_right[1] = arrow_base[1] - side[1] * arrow_width;
        arrow_right[2] = arrow_base[2] - side[2] * arrow_width;

        if (static_cast<int>(bone_index) == m_selected_bone_index)
        {
            glColor3f(0.58f, 0.78f, 1.0f);
            glLineWidth(2.25f);
        }
        else
        {
            glColor3f(0.30f, 0.56f, 0.92f);
            glLineWidth(1.3f);
        }

        glBegin(GL_LINES);
        glVertex3f(parent.translation[0], parent.translation[1], parent.translation[2]);
        glVertex3f(bone.translation[0], bone.translation[1], bone.translation[2]);
        glVertex3f(bone.translation[0], bone.translation[1], bone.translation[2]);
        glVertex3f(arrow_left[0], arrow_left[1], arrow_left[2]);
        glVertex3f(bone.translation[0], bone.translation[1], bone.translation[2]);
        glVertex3f(arrow_right[0], arrow_right[1], arrow_right[2]);
        glEnd();
    }
}

void RagdollPreviewViewport::draw_box(const BodyRenderState& body)
{
    const float x = body.half_extents[0];
    const float y = body.half_extents[1];
    const float z = body.half_extents[2];

    glShadeModel(GL_FLAT);
    glBegin(GL_QUADS);

    glNormal3f(0.0f, 0.0f, -1.0f);
    glVertex3f(-x, -y, -z); glVertex3f(x, -y, -z); glVertex3f(x, y, -z); glVertex3f(-x, y, -z);
    glNormal3f(0.0f, 0.0f, 1.0f);
    glVertex3f(-x, -y, z); glVertex3f(-x, y, z); glVertex3f(x, y, z); glVertex3f(x, -y, z);
    glNormal3f(-1.0f, 0.0f, 0.0f);
    glVertex3f(-x, -y, -z); glVertex3f(-x, y, -z); glVertex3f(-x, y, z); glVertex3f(-x, -y, z);
    glNormal3f(1.0f, 0.0f, 0.0f);
    glVertex3f(x, -y, -z); glVertex3f(x, -y, z); glVertex3f(x, y, z); glVertex3f(x, y, -z);
    glNormal3f(0.0f, 1.0f, 0.0f);
    glVertex3f(-x, y, -z); glVertex3f(x, y, -z); glVertex3f(x, y, z); glVertex3f(-x, y, z);
    glNormal3f(0.0f, -1.0f, 0.0f);
    glVertex3f(-x, -y, -z); glVertex3f(-x, -y, z); glVertex3f(x, -y, z); glVertex3f(x, -y, -z);

    glEnd();
}

void RagdollPreviewViewport::draw_sphere(const BodyRenderState& body)
{
    const float radius = body.radius;
    GLUquadric* quadric = 0;

    quadric = gluNewQuadric();
    gluQuadricDrawStyle(quadric, GLU_FILL);
    gluQuadricNormals(quadric, GLU_FLAT);
    gluSphere(quadric, radius, 20, 14);
    gluDeleteQuadric(quadric);
}

void RagdollPreviewViewport::draw_capsule(const BodyRenderState& body)
{
    CapsuleRenderFrame frame;

    if (!build_capsule_render_frame(body, &frame))
    {
        return;
    }

    draw_capsule_solid_geometry(frame);
}

void RagdollPreviewViewport::apply_body_transform(const BodyRenderState& body)
{
    const float x = body.rotation[0];
    const float y = body.rotation[1];
    const float z = body.rotation[2];
    const float w = body.rotation[3];
    const float xx = x * x;
    const float yy = y * y;
    const float zz = z * z;
    const float xy = x * y;
    const float xz = x * z;
    const float yz = y * z;
    const float wx = w * x;
    const float wy = w * y;
    const float wz = w * z;
    const float matrix[16] = {
        1.0f - 2.0f * (yy + zz), 2.0f * (xy + wz), 2.0f * (xz - wy), 0.0f,
        2.0f * (xy - wz), 1.0f - 2.0f * (xx + zz), 2.0f * (yz + wx), 0.0f,
        2.0f * (xz + wy), 2.0f * (yz - wx), 1.0f - 2.0f * (xx + yy), 0.0f,
        body.position[0], body.position[1], body.position[2], 1.0f
    };

    glMultMatrixf(matrix);
}

void RagdollPreviewViewport::pick_body_at(const QPoint& mouse_position)
{
    const CameraBasis basis = compute_camera_basis(
        m_camera_target,
        m_camera_distance,
        m_camera_yaw_degrees,
        m_camera_pitch_degrees);
    const float near_plane = 0.1f;
    const float aspect_ratio = height() > 0 ? static_cast<float>(width()) / static_cast<float>(height()) : 1.0f;
    const float top = 0.08f * near_plane;
    const float right = top * aspect_ratio;
    const float normalized_x = width() > 0
        ? ((static_cast<float>(mouse_position.x()) + 0.5f) / static_cast<float>(width())) * 2.0f - 1.0f
        : 0.0f;
    const float normalized_y = height() > 0
        ? 1.0f - ((static_cast<float>(mouse_position.y()) + 0.5f) / static_cast<float>(height())) * 2.0f
        : 0.0f;
    const float view_x = normalized_x * right;
    const float view_y = normalized_y * top;
    const std::vector<RagdollPreviewBone>& bones = active_bones_for_kind(m_preview_data, m_active_skeleton_kind);
    float ray_origin[3];
    float ray_direction[3];
    float best_distance = 500.0f;
    int best_bone_index = -1;

    ray_origin[0] = basis.position[0];
    ray_origin[1] = basis.position[1];
    ray_origin[2] = basis.position[2];
    ray_direction[0] = basis.forward[0] * near_plane + basis.right[0] * view_x + basis.up[0] * view_y;
    ray_direction[1] = basis.forward[1] * near_plane + basis.right[1] * view_x + basis.up[1] * view_y;
    ray_direction[2] = basis.forward[2] * near_plane + basis.right[2] * view_x + basis.up[2] * view_y;
    normalize_vector(ray_direction);

    if (m_active_skeleton_kind == RagdollPreviewSkeletonRagdoll)
    {
        for (std::size_t body_index = 0; body_index < m_preview_data.bodies.size(); ++body_index)
        {
            const RagdollPreviewBody& body = m_preview_data.bodies[body_index];
            float ray_distance = 0.0f;
            float distance_squared = 0.0f;
            float pick_radius = 0.65f;
            bool hit = false;

            if (!body.is_present || !body.has_render_state)
            {
                continue;
            }

            if (body.shape_type == RagdollPreviewBodyShapeCapsule)
            {
                float local_a[3] = {
                    body.render_state.capsule_vertices[0],
                    body.render_state.capsule_vertices[1],
                    body.render_state.capsule_vertices[2]
                };
                float local_b[3] = {
                    body.render_state.capsule_vertices[3],
                    body.render_state.capsule_vertices[4],
                    body.render_state.capsule_vertices[5]
                };
                float world_a[3];
                float world_b[3];

                transform_local_point(body.render_state, local_a, world_a);
                transform_local_point(body.render_state, local_b, world_b);
                distance_squared_between_ray_and_segment(ray_origin, ray_direction, world_a, world_b, &ray_distance, &distance_squared);
                pick_radius = body.radius > 0.2f ? body.radius : 0.2f;
                hit = distance_squared <= pick_radius * pick_radius;
            }
            else
            {
                if (body.shape_type == RagdollPreviewBodyShapeSphere)
                {
                    pick_radius = body.radius > 0.2f ? body.radius : 0.2f;
                }
                else if (body.shape_type == RagdollPreviewBodyShapeBox)
                {
                    pick_radius = std::sqrt(
                        body.half_extents[0] * body.half_extents[0] +
                        body.half_extents[1] * body.half_extents[1] +
                        body.half_extents[2] * body.half_extents[2]);
                }

                distance_squared_between_ray_and_point(ray_origin, ray_direction, body.position, &ray_distance, &distance_squared);
                hit = distance_squared <= pick_radius * pick_radius;
            }

            if (hit && ray_distance < best_distance)
            {
                best_distance = ray_distance;
                best_bone_index = body.bone_index;
            }
        }
    }

    if (best_bone_index < 0)
    {
        for (std::size_t bone_index = 0; bone_index < bones.size(); ++bone_index)
        {
            float ray_distance = 0.0f;
            float distance_squared = 0.0f;
            const float pick_radius = m_camera_distance > 60.0f ? 0.45f : 0.24f;

            distance_squared_between_ray_and_point(ray_origin, ray_direction, bones[bone_index].translation, &ray_distance, &distance_squared);
            if (distance_squared <= pick_radius * pick_radius && ray_distance < best_distance)
            {
                best_distance = ray_distance;
                best_bone_index = static_cast<int>(bone_index);
            }
        }
    }

    if (best_bone_index >= 0)
    {
        emit bone_selected(best_bone_index);
    }
}