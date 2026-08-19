#ifndef HAVOK_SCENE_APP_VIEWPORT_OVERLAY_RENDERER_H
#define HAVOK_SCENE_APP_VIEWPORT_OVERLAY_RENDERER_H

class SimulationController;
class ViewportCamera;
class ViewportWidget;

class ViewportOverlayRenderer
{
public:
    ViewportOverlayRenderer(ViewportWidget& viewport, ViewportCamera& camera);

    void set_simulation(SimulationController* simulation);

    void draw_axes() const;
    void draw_axis_move_guide() const;
    void draw_axis_rotate_guide() const;
    void draw_entity_labels() const;
    void draw_screen_overlay() const;

private:
    ViewportWidget& m_viewport;
    ViewportCamera& m_camera;
    SimulationController* m_simulation;
};

#endif