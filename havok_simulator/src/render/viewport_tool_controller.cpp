#include "viewport_tool_controller.h"

#include <cmath>

#include <QKeyEvent>
#include <QMouseEvent>

#include "simulation_controller.h"
#include "viewport_camera.h"
#include "viewport_widget.h"

namespace
{
    const float kAxisProjectionEpsilon = 0.0001f;

    float compute_axis_move_delta(
        const ViewportCameraBasis& basis,
        SceneMoveAxis axis,
        const QPoint& start_mouse_pos,
        const QPoint& current_mouse_pos,
        float visible_half_height,
        int viewport_height)
    {
        float axis_world[3] = { 0.0f, 0.0f, 0.0f };
        float axis_screen[2];
        float mouse_delta_world[2];
        const float units_per_pixel = viewport_height > 0
            ? (2.0f * visible_half_height) / static_cast<float>(viewport_height)
            : 0.0f;
        float screen_length_squared = 0.0f;

        if (axis == SceneMoveAxisX)
        {
            axis_world[0] = 1.0f;
        }
        else if (axis == SceneMoveAxisY)
        {
            axis_world[1] = 1.0f;
        }
        else if (axis == SceneMoveAxisZ)
        {
            axis_world[2] = 1.0f;
        }
        else
        {
            return 0.0f;
        }

        axis_screen[0] = axis_world[0] * basis.right[0] + axis_world[1] * basis.right[1] + axis_world[2] * basis.right[2];
        axis_screen[1] = axis_world[0] * basis.up[0] + axis_world[1] * basis.up[1] + axis_world[2] * basis.up[2];
        screen_length_squared = axis_screen[0] * axis_screen[0] + axis_screen[1] * axis_screen[1];

        mouse_delta_world[0] = static_cast<float>(current_mouse_pos.x() - start_mouse_pos.x()) * units_per_pixel;
        mouse_delta_world[1] = static_cast<float>(start_mouse_pos.y() - current_mouse_pos.y()) * units_per_pixel;

        if (screen_length_squared > kAxisProjectionEpsilon)
        {
            return (mouse_delta_world[0] * axis_screen[0] + mouse_delta_world[1] * axis_screen[1]) / screen_length_squared;
        }

        if (std::fabs(axis_screen[0]) >= std::fabs(axis_screen[1]) && std::fabs(axis_screen[0]) > kAxisProjectionEpsilon)
        {
            return mouse_delta_world[0] / axis_screen[0];
        }

        if (std::fabs(axis_screen[1]) > kAxisProjectionEpsilon)
        {
            return mouse_delta_world[1] / axis_screen[1];
        }

        return mouse_delta_world[1];
    }

    float compute_axis_rotate_delta_degrees(
        const ViewportCameraBasis& basis,
        SceneMoveAxis axis,
        const QPoint& start_mouse_pos,
        const QPoint& current_mouse_pos)
    {
        float axis_world[3] = { 0.0f, 0.0f, 0.0f };
        float axis_screen[2];
        float mouse_delta_pixels[2];
        float axis_screen_length = 0.0f;
        const float degrees_per_pixel = 0.75f;

        if (axis == SceneMoveAxisX)
        {
            axis_world[0] = 1.0f;
        }
        else if (axis == SceneMoveAxisY)
        {
            axis_world[1] = 1.0f;
        }
        else if (axis == SceneMoveAxisZ)
        {
            axis_world[2] = 1.0f;
        }
        else
        {
            return 0.0f;
        }

        axis_screen[0] = axis_world[0] * basis.right[0] + axis_world[1] * basis.right[1] + axis_world[2] * basis.right[2];
        axis_screen[1] = axis_world[0] * basis.up[0] + axis_world[1] * basis.up[1] + axis_world[2] * basis.up[2];
        axis_screen_length = std::sqrt(axis_screen[0] * axis_screen[0] + axis_screen[1] * axis_screen[1]);

        mouse_delta_pixels[0] = static_cast<float>(current_mouse_pos.x() - start_mouse_pos.x());
        mouse_delta_pixels[1] = static_cast<float>(start_mouse_pos.y() - current_mouse_pos.y());

        if (axis_screen_length > kAxisProjectionEpsilon)
        {
            return ((mouse_delta_pixels[0] * axis_screen[0]) + (mouse_delta_pixels[1] * axis_screen[1])) / axis_screen_length * degrees_per_pixel;
        }

        if (std::fabs(axis_screen[0]) >= std::fabs(axis_screen[1]) && std::fabs(axis_screen[0]) > kAxisProjectionEpsilon)
        {
            return (axis_screen[0] >= 0.0f ? mouse_delta_pixels[0] : -mouse_delta_pixels[0]) * degrees_per_pixel;
        }

        if (std::fabs(axis_screen[1]) > kAxisProjectionEpsilon)
        {
            return (axis_screen[1] >= 0.0f ? mouse_delta_pixels[1] : -mouse_delta_pixels[1]) * degrees_per_pixel;
        }

        return mouse_delta_pixels[1] * degrees_per_pixel;
    }

    float compute_uniform_scale_factor(
        const QPoint& start_mouse_pos,
        const QPoint& current_mouse_pos)
    {
        const float pixels_to_scale = 0.01f;
        const float pixel_delta = static_cast<float>(current_mouse_pos.x() - start_mouse_pos.x());
        return std::exp(pixel_delta * pixels_to_scale);
    }
}

ViewportToolController::ViewportToolController(ViewportWidget& viewport, ViewportCamera& camera)
    : m_viewport(viewport)
    , m_camera(camera)
    , m_simulation(0)
    , m_is_orbiting(false)
    , m_is_panning(false)
    , m_pending_selection_click(false)
    , m_axis_move_start_mouse_pos()
    , m_axis_rotate_start_mouse_pos()
    , m_uniform_scale_start_mouse_pos()
{
}

void ViewportToolController::set_simulation(SimulationController* simulation)
{
    m_simulation = simulation;
}

bool ViewportToolController::key_press(QKeyEvent* event)
{
    SceneMoveAxis axis = SceneMoveAxisNone;
    const bool is_ctrl_snap = (event->modifiers() & Qt::ControlModifier) != 0;
    const bool is_shift_rotation = (event->modifiers() & Qt::ShiftModifier) != 0;

    if (!m_simulation)
    {
        return false;
    }

    if (is_ctrl_snap)
    {
        if (event->key() == Qt::Key_X)
        {
            m_camera.snap_to_axis(ViewportCameraSnapAxisX);
            m_camera.apply_projection(m_viewport.width(), m_viewport.height());
            m_viewport.updateGL();
            return true;
        }
        else if (event->key() == Qt::Key_Y)
        {
            m_camera.snap_to_axis(ViewportCameraSnapAxisY);
            m_camera.apply_projection(m_viewport.width(), m_viewport.height());
            m_viewport.updateGL();
            return true;
        }
        else if (event->key() == Qt::Key_Z)
        {
            m_camera.snap_to_axis(ViewportCameraSnapAxisZ);
            m_camera.apply_projection(m_viewport.width(), m_viewport.height());
            m_viewport.updateGL();
            return true;
        }
    }

    if (event->key() == Qt::Key_Escape)
    {
        if (m_simulation->axis_move_session().active)
        {
            m_simulation->cancel_axis_move();
            m_viewport.updateGL();
            m_viewport.notify_selection_changed();
            return true;
        }

        if (m_simulation->axis_rotate_session().active)
        {
            m_simulation->cancel_axis_rotate();
            m_viewport.updateGL();
            m_viewport.notify_selection_changed();
            return true;
        }

        if (m_simulation->uniform_scale_session().active)
        {
            m_simulation->cancel_uniform_scale();
            m_viewport.updateGL();
            m_viewport.notify_selection_changed();
            return true;
        }

        return false;
    }

    if (event->key() == Qt::Key_X)
    {
        axis = SceneMoveAxisX;
    }
    else if (event->key() == Qt::Key_Y)
    {
        axis = SceneMoveAxisZ;
    }
    else if (event->key() == Qt::Key_Z)
    {
        axis = SceneMoveAxisY;
    }

    if (axis != SceneMoveAxisNone)
    {
        if (!is_shift_rotation && m_simulation->uniform_scale_session().active)
        {
            if (m_simulation->set_uniform_scale_axis(axis))
            {
                const float scale_factor = compute_uniform_scale_factor(
                    m_uniform_scale_start_mouse_pos,
                    m_last_mouse_pos);

                if (m_simulation->update_uniform_scale_preview(scale_factor))
                {
                    m_viewport.updateGL();
                    m_viewport.notify_selection_changed();
                }
            }
            return true;
        }

        if (is_shift_rotation)
        {
            if (m_simulation->begin_axis_rotate(axis))
            {
                m_axis_rotate_start_mouse_pos = m_last_mouse_pos;
                m_viewport.updateGL();
                m_viewport.notify_selection_changed();
            }
        }
        else if (m_simulation->begin_axis_move(axis))
        {
            m_axis_move_start_mouse_pos = m_last_mouse_pos;
            m_viewport.updateGL();
            m_viewport.notify_selection_changed();
        }
        return true;
    }

    if (event->key() == Qt::Key_S && !is_ctrl_snap && !is_shift_rotation)
    {
        if (m_simulation->begin_uniform_scale())
        {
            m_uniform_scale_start_mouse_pos = m_last_mouse_pos;
            m_viewport.updateGL();
            m_viewport.notify_selection_changed();
        }
        return true;
    }

    return false;
}

void ViewportToolController::mouse_press(QMouseEvent* event)
{
    m_last_mouse_pos = event->pos();

    if (m_simulation && m_simulation->has_active_tool_session())
    {
        return;
    }

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

void ViewportToolController::mouse_move(QMouseEvent* event)
{
    const QPoint delta = event->pos() - m_last_mouse_pos;
    m_last_mouse_pos = event->pos();

    if (m_simulation && m_simulation->axis_move_session().active)
    {
        const ViewportCameraBasis basis = m_camera.basis();
        const float axis_delta = compute_axis_move_delta(
            basis,
            m_simulation->axis_move_session().axis,
            m_axis_move_start_mouse_pos,
            event->pos(),
            m_camera.visible_half_height(),
            m_viewport.height());

        if (m_simulation->update_axis_move_preview(axis_delta))
        {
            m_viewport.updateGL();
        }
        return;
    }

    if (m_simulation && m_simulation->axis_rotate_session().active)
    {
        const ViewportCameraBasis basis = m_camera.basis();
        const float angle_delta_degrees = compute_axis_rotate_delta_degrees(
            basis,
            m_simulation->axis_rotate_session().axis,
            m_axis_rotate_start_mouse_pos,
            event->pos());

        if (m_simulation->update_axis_rotate_preview(angle_delta_degrees))
        {
            m_viewport.updateGL();
        }
        return;
    }

    if (m_simulation && m_simulation->uniform_scale_session().active)
    {
        const float scale_factor = compute_uniform_scale_factor(
            m_uniform_scale_start_mouse_pos,
            event->pos());

        if (m_simulation->update_uniform_scale_preview(scale_factor))
        {
            m_viewport.updateGL();
        }
        return;
    }

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

        m_camera.orbit(-static_cast<float>(delta.x()) * 0.45f, static_cast<float>(delta.y()) * 0.35f);
        m_viewport.updateGL();
    }
    else if (m_is_panning)
    {
        m_camera.pan(static_cast<float>(delta.x()), static_cast<float>(delta.y()), m_viewport.height());
        m_viewport.updateGL();
    }
}

void ViewportToolController::mouse_release(QMouseEvent* event)
{
    if (m_simulation && m_simulation->has_active_tool_session() && event->button() == Qt::LeftButton)
    {
        pick_scene_entity(event->pos());
        return;
    }

    if (event->button() == Qt::LeftButton)
    {
        if (m_pending_selection_click)
        {
            pick_scene_entity(event->pos());
        }

        m_is_orbiting = false;
        m_pending_selection_click = false;
    }
    else if (event->button() == Qt::RightButton || event->button() == Qt::MidButton)
    {
        m_is_panning = false;
    }
}

void ViewportToolController::pick_scene_entity(const QPoint& mouse_position)
{
    float ray_origin[3];
    float ray_direction[3];
    SceneEntityId entity_id = 0;
    SceneEntityKind entity_kind = SceneEntityKindNone;
    bool did_change_selection = false;
    const SceneAxisMoveSession move_session = m_simulation ? m_simulation->axis_move_session() : SceneAxisMoveSession();
    const SceneAxisRotateSession rotate_session = m_simulation ? m_simulation->axis_rotate_session() : SceneAxisRotateSession();
    const SceneUniformScaleSession scale_session = m_simulation ? m_simulation->uniform_scale_session() : SceneUniformScaleSession();

    if (!m_simulation)
    {
        return;
    }

    m_camera.build_ray(mouse_position, m_viewport.width(), m_viewport.height(), ray_origin, ray_direction);

    if (move_session.active)
    {
        if (m_simulation->commit_axis_move())
        {
            did_change_selection = true;
        }
    }
    else if (rotate_session.active)
    {
        if (m_simulation->commit_axis_rotate())
        {
            did_change_selection = true;
        }
    }
    else if (scale_session.active)
    {
        if (m_simulation->commit_uniform_scale())
        {
            did_change_selection = true;
        }
    }
    else if (m_simulation->pick_entity_from_ray(ray_origin, ray_direction, &entity_id, &entity_kind))
    {
        const SceneEntitySelection& selected = m_simulation->selected_entity();
        if (selected.id != entity_id || selected.kind != entity_kind)
        {
            did_change_selection = m_simulation->select_entity(entity_id, entity_kind);
        }
    }
    else if (m_simulation->selected_entity().id != 0)
    {
        m_simulation->clear_selected_entity();
        did_change_selection = true;
    }

    if (did_change_selection)
    {
        m_viewport.notify_selection_changed();
    }

    m_viewport.updateGL();
}