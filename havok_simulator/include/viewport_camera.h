#ifndef HAVOK_SCENE_APP_VIEWPORT_CAMERA_H
#define HAVOK_SCENE_APP_VIEWPORT_CAMERA_H

#include <QPoint>

struct ViewportCameraBasis
{
    float position[3];
    float forward[3];
    float right[3];
    float up[3];
};

enum ViewportCameraSnapAxis
{
    ViewportCameraSnapAxisNone,
    ViewportCameraSnapAxisX,
    ViewportCameraSnapAxisY,
    ViewportCameraSnapAxisZ
};

class ViewportCamera
{
public:
    ViewportCamera();

    void apply_projection(int viewport_width, int viewport_height) const;
    void apply_view_transform() const;
    ViewportCameraBasis basis() const;
    void build_ray(
        const QPoint& mouse_position,
        int viewport_width,
        int viewport_height,
        float ray_origin[3],
        float ray_direction[3]) const;
    void orbit(float yaw_delta_degrees, float pitch_delta_degrees);
    void pan(float delta_x_pixels, float delta_y_pixels, int viewport_height);
    void zoom(float delta_steps);
    void snap_to_axis(ViewportCameraSnapAxis axis);

    bool is_orthographic() const;
    const char* orthographic_view_label() const;
    float distance() const;
    float visible_half_height() const;

private:
    void exit_orthographic_snap();
    void set_snap_view(ViewportCameraSnapAxis axis, bool negative);

    float m_target[3];
    float m_distance;
    float m_yaw_degrees;
    float m_pitch_degrees;
    bool m_is_orthographic;
    ViewportCameraSnapAxis m_last_snap_axis;
    bool m_last_snap_negative;
};

#endif