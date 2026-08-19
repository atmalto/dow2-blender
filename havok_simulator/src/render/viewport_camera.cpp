#include "viewport_camera.h"

#include <cmath>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>
#include <GL/glu.h>

namespace
{
    const float kRadiansPerDegree = 0.0174532925f;
    const float kVerticalFovTangent = 0.08f;
    const float kNearPlane = 0.1f;
    const float kFarPlane = 200.0f;
    const float kMinCameraDistance = 4.0f;
    const float kMaxCameraDistance = 400.0f;

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

    ViewportCameraBasis compute_camera_basis(
        const float target[3],
        float distance,
        float yaw_degrees,
        float pitch_degrees)
    {
        ViewportCameraBasis basis;
        const float yaw_radians = yaw_degrees * kRadiansPerDegree;
        const float pitch_radians = pitch_degrees * kRadiansPerDegree;
        const float cos_yaw = std::cos(yaw_radians);
        const float sin_yaw = std::sin(yaw_radians);
        const float cos_pitch = std::cos(pitch_radians);
        const float sin_pitch = std::sin(pitch_radians);
        float reference_up[3] = { 0.0f, 1.0f, 0.0f };

        basis.position[0] = target[0] + sin_yaw * cos_pitch * distance;
        basis.position[1] = target[1] + sin_pitch * distance;
        basis.position[2] = target[2] + cos_yaw * cos_pitch * distance;

        basis.forward[0] = target[0] - basis.position[0];
        basis.forward[1] = target[1] - basis.position[1];
        basis.forward[2] = target[2] - basis.position[2];
        normalize_vector(basis.forward);

        if (std::fabs(basis.forward[1]) > 0.999f)
        {
            reference_up[1] = 0.0f;
            reference_up[2] = basis.forward[1] > 0.0f ? 1.0f : -1.0f;
        }

        cross_product(basis.forward, reference_up, basis.right);
        normalize_vector(basis.right);

        cross_product(basis.right, basis.forward, basis.up);
        normalize_vector(basis.up);

        return basis;
    }
}

ViewportCamera::ViewportCamera()
    : m_distance(24.0f)
    , m_yaw_degrees(-28.0f)
    , m_pitch_degrees(18.0f)
    , m_is_orthographic(false)
    , m_last_snap_axis(ViewportCameraSnapAxisNone)
    , m_last_snap_negative(false)
{
    m_target[0] = 0.0f;
    m_target[1] = 2.0f;
    m_target[2] = 0.0f;
}

void ViewportCamera::apply_projection(int viewport_width, int viewport_height) const
{
    const float aspect_ratio = viewport_height > 0
        ? static_cast<float>(viewport_width) / static_cast<float>(viewport_height)
        : 1.0f;

    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();

    if (m_is_orthographic)
    {
        const float half_height = visible_half_height();
        const float half_width = half_height * aspect_ratio;
        glOrtho(-half_width, half_width, -half_height, half_height, kNearPlane, kFarPlane);
    }
    else
    {
        const float top = kVerticalFovTangent * kNearPlane;
        const float right = top * aspect_ratio;
        glFrustum(-right, right, -top, top, kNearPlane, kFarPlane);
    }

    glMatrixMode(GL_MODELVIEW);
}

void ViewportCamera::apply_view_transform() const
{
    const ViewportCameraBasis current_basis = basis();

    gluLookAt(
        current_basis.position[0], current_basis.position[1], current_basis.position[2],
        m_target[0], m_target[1], m_target[2],
        current_basis.up[0], current_basis.up[1], current_basis.up[2]);
}

ViewportCameraBasis ViewportCamera::basis() const
{
    return compute_camera_basis(m_target, m_distance, m_yaw_degrees, m_pitch_degrees);
}

void ViewportCamera::build_ray(
    const QPoint& mouse_position,
    int viewport_width,
    int viewport_height,
    float ray_origin[3],
    float ray_direction[3]) const
{
    const ViewportCameraBasis current_basis = basis();
    const float aspect_ratio = viewport_height > 0
        ? static_cast<float>(viewport_width) / static_cast<float>(viewport_height)
        : 1.0f;
    const float normalized_x = viewport_width > 0
        ? ((static_cast<float>(mouse_position.x()) + 0.5f) / static_cast<float>(viewport_width)) * 2.0f - 1.0f
        : 0.0f;
    const float normalized_y = viewport_height > 0
        ? 1.0f - ((static_cast<float>(mouse_position.y()) + 0.5f) / static_cast<float>(viewport_height)) * 2.0f
        : 0.0f;

    if (m_is_orthographic)
    {
        const float half_height = visible_half_height();
        const float half_width = half_height * aspect_ratio;

        ray_origin[0] = current_basis.position[0] + current_basis.right[0] * (normalized_x * half_width) + current_basis.up[0] * (normalized_y * half_height);
        ray_origin[1] = current_basis.position[1] + current_basis.right[1] * (normalized_x * half_width) + current_basis.up[1] * (normalized_y * half_height);
        ray_origin[2] = current_basis.position[2] + current_basis.right[2] * (normalized_x * half_width) + current_basis.up[2] * (normalized_y * half_height);
        ray_direction[0] = current_basis.forward[0];
        ray_direction[1] = current_basis.forward[1];
        ray_direction[2] = current_basis.forward[2];
        return;
    }

    const float top = kVerticalFovTangent * kNearPlane;
    const float right = top * aspect_ratio;
    const float view_x = normalized_x * right;
    const float view_y = normalized_y * top;

    ray_origin[0] = current_basis.position[0];
    ray_origin[1] = current_basis.position[1];
    ray_origin[2] = current_basis.position[2];
    ray_direction[0] = current_basis.forward[0] * kNearPlane + current_basis.right[0] * view_x + current_basis.up[0] * view_y;
    ray_direction[1] = current_basis.forward[1] * kNearPlane + current_basis.right[1] * view_x + current_basis.up[1] * view_y;
    ray_direction[2] = current_basis.forward[2] * kNearPlane + current_basis.right[2] * view_x + current_basis.up[2] * view_y;
    normalize_vector(ray_direction);
}

void ViewportCamera::orbit(float yaw_delta_degrees, float pitch_delta_degrees)
{
    if (yaw_delta_degrees != 0.0f || pitch_delta_degrees != 0.0f)
    {
        exit_orthographic_snap();
    }

    m_yaw_degrees += yaw_delta_degrees;
    m_pitch_degrees += pitch_delta_degrees;

    if (m_pitch_degrees > 89.0f)
    {
        m_pitch_degrees = 89.0f;
    }
    if (m_pitch_degrees < -89.0f)
    {
        m_pitch_degrees = -89.0f;
    }
}

void ViewportCamera::pan(float delta_x_pixels, float delta_y_pixels, int viewport_height)
{
    const ViewportCameraBasis current_basis = basis();
    const float pixels_to_world = viewport_height > 0
        ? (2.0f * visible_half_height()) / static_cast<float>(viewport_height)
        : 0.0f;
    const float pan_x = -delta_x_pixels * pixels_to_world;
    const float pan_y = delta_y_pixels * pixels_to_world;

    m_target[0] += current_basis.right[0] * pan_x + current_basis.up[0] * pan_y;
    m_target[1] += current_basis.right[1] * pan_x + current_basis.up[1] * pan_y;
    m_target[2] += current_basis.right[2] * pan_x + current_basis.up[2] * pan_y;
}

void ViewportCamera::zoom(float delta_steps)
{
    m_distance -= delta_steps * 1.5f;

    if (m_distance < kMinCameraDistance)
    {
        m_distance = kMinCameraDistance;
    }
    if (m_distance > kMaxCameraDistance)
    {
        m_distance = kMaxCameraDistance;
    }
}

void ViewportCamera::snap_to_axis(ViewportCameraSnapAxis axis)
{
    bool negative = false;

    if (m_is_orthographic && axis == m_last_snap_axis)
    {
        negative = !m_last_snap_negative;
    }

    set_snap_view(axis, negative);
    m_is_orthographic = true;
    m_last_snap_axis = axis;
    m_last_snap_negative = negative;
}

bool ViewportCamera::is_orthographic() const
{
    return m_is_orthographic;
}

const char* ViewportCamera::orthographic_view_label() const
{
    if (!m_is_orthographic)
    {
        return "";
    }

    if (m_last_snap_axis == ViewportCameraSnapAxisX)
    {
        return m_last_snap_negative ? "Left" : "Right";
    }
    if (m_last_snap_axis == ViewportCameraSnapAxisY)
    {
        return m_last_snap_negative ? "Back" : "Front";
    }
    if (m_last_snap_axis == ViewportCameraSnapAxisZ)
    {
        return m_last_snap_negative ? "Bottom" : "Top";
    }

    return "";
}

float ViewportCamera::distance() const
{
    return m_distance;
}

float ViewportCamera::visible_half_height() const
{
    return m_distance * kVerticalFovTangent;
}

void ViewportCamera::exit_orthographic_snap()
{
    m_is_orthographic = false;
    m_last_snap_axis = ViewportCameraSnapAxisNone;
    m_last_snap_negative = false;
}

void ViewportCamera::set_snap_view(ViewportCameraSnapAxis axis, bool negative)
{
    if (axis == ViewportCameraSnapAxisX)
    {
        m_yaw_degrees = negative ? -90.0f : 90.0f;
        m_pitch_degrees = 0.0f;
    }
    else if (axis == ViewportCameraSnapAxisY)
    {
        m_yaw_degrees = negative ? 180.0f : 0.0f;
        m_pitch_degrees = 0.0f;
    }
    else if (axis == ViewportCameraSnapAxisZ)
    {
        m_yaw_degrees = 0.0f;
        m_pitch_degrees = negative ? -89.0f : 89.0f;
    }
}