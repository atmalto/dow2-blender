#ifndef HAVOK_SCENE_APP_VIEWPORT_TOOL_CONTROLLER_H
#define HAVOK_SCENE_APP_VIEWPORT_TOOL_CONTROLLER_H

#include <QPoint>

#include "scene_entity.h"

class QKeyEvent;
class QMouseEvent;
class SimulationController;
class ViewportCamera;
class ViewportWidget;

class ViewportToolController
{
public:
    ViewportToolController(ViewportWidget& viewport, ViewportCamera& camera);

    void set_simulation(SimulationController* simulation);

    bool key_press(QKeyEvent* event);
    void mouse_press(QMouseEvent* event);
    void mouse_move(QMouseEvent* event);
    void mouse_release(QMouseEvent* event);

private:
    void pick_scene_entity(const QPoint& mouse_position);

    ViewportWidget& m_viewport;
    ViewportCamera& m_camera;
    SimulationController* m_simulation;
    QPoint m_last_mouse_pos;
    QPoint m_left_press_pos;
    bool m_is_orbiting;
    bool m_is_panning;
    bool m_pending_selection_click;
    QPoint m_axis_move_start_mouse_pos;
    QPoint m_axis_rotate_start_mouse_pos;
    QPoint m_uniform_scale_start_mouse_pos;
};

#endif