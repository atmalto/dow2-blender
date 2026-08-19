#ifndef HAVOK_SCENE_APP_VIEWPORT_WIDGET_H
#define HAVOK_SCENE_APP_VIEWPORT_WIDGET_H

#include <QPoint>
#include <QGLWidget>

#include "body_render_state.h"
#include "scene_entity.h"
#include "viewport_camera.h"

class QKeyEvent;
class QMouseEvent;
class QWheelEvent;
class SimulationController;
class ViewportOverlayRenderer;
class ViewportToolController;

class ViewportWidget : public QGLWidget
{
    Q_OBJECT

public:
    explicit ViewportWidget(QWidget* parent = 0);
    virtual ~ViewportWidget();

    void set_simulation(SimulationController* simulation);

signals:
    void selection_changed();

protected:
    virtual void initializeGL();
    virtual void resizeGL(int width, int height);
    virtual void paintGL();
    virtual void keyPressEvent(QKeyEvent* event);
    virtual void mousePressEvent(QMouseEvent* event);
    virtual void mouseMoveEvent(QMouseEvent* event);
    virtual void mouseReleaseEvent(QMouseEvent* event);
    virtual void wheelEvent(QWheelEvent* event);

private:
    friend class ViewportOverlayRenderer;
    friend class ViewportToolController;

    void apply_camera_transform();
    void notify_selection_changed();
    void draw_grid();
    void draw_entity_labels();
    void draw_axes();
    void draw_axis_move_guide();
    void draw_axis_rotate_guide();
    void draw_body(const BodyRenderState& body);
    void draw_wireframe_overlay(const BodyRenderState& body);
    void draw_selection_overlay(const BodyRenderState& body);
    void draw_box(const BodyRenderState& body);
    void draw_sphere(const BodyRenderState& body);
    void draw_capsule(const BodyRenderState& body);
    void draw_wedge(const BodyRenderState& body);
    void draw_convex_hull(const BodyRenderState& body);
    void draw_arrow(const BodyRenderState& body);
    void apply_body_transform(const BodyRenderState& body);

    SimulationController* m_simulation;
    ViewportOverlayRenderer* m_overlay_renderer;
    ViewportToolController* m_tool_controller;
    ViewportCamera m_camera;
};

#endif