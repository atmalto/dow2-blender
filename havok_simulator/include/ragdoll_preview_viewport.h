#ifndef HAVOK_SCENE_APP_RAGDOLL_PREVIEW_VIEWPORT_H
#define HAVOK_SCENE_APP_RAGDOLL_PREVIEW_VIEWPORT_H

#include <QPoint>
#include <QGLWidget>

#include "ragdoll_preview_data.h"

class QMouseEvent;
class QWheelEvent;

class RagdollPreviewViewport : public QGLWidget
{
    Q_OBJECT

public:
    explicit RagdollPreviewViewport(QWidget* parent = 0);

    void set_preview_data(const RagdollPreviewData& preview_data);
    void clear_preview_data();
    void set_selected_bone_index(int bone_index);
    void set_active_skeleton_kind(RagdollPreviewSkeletonKind skeleton_kind);

protected:
    virtual void initializeGL();
    virtual void resizeGL(int width, int height);
    virtual void paintGL();
    virtual void mousePressEvent(QMouseEvent* event);
    virtual void mouseMoveEvent(QMouseEvent* event);
    virtual void mouseReleaseEvent(QMouseEvent* event);
    virtual void wheelEvent(QWheelEvent* event);

signals:
    void bone_selected(int bone_index);

private:
    void apply_camera_transform();
    void frame_preview();
    void draw_grid();
    void draw_axes();
    void draw_bone_hierarchy();
    void draw_body(const BodyRenderState& body);
    void draw_body_labels();
    void draw_box(const BodyRenderState& body);
    void draw_sphere(const BodyRenderState& body);
    void draw_capsule(const BodyRenderState& body);
    void apply_body_transform(const BodyRenderState& body);
    void pick_body_at(const QPoint& mouse_position);

    RagdollPreviewData m_preview_data;
    QPoint m_last_mouse_pos;
    QPoint m_left_press_pos;
    bool m_is_orbiting;
    bool m_is_panning;
    bool m_pending_selection_click;
    int m_selected_bone_index;
    RagdollPreviewSkeletonKind m_active_skeleton_kind;
    float m_camera_target[3];
    float m_camera_distance;
    float m_camera_yaw_degrees;
    float m_camera_pitch_degrees;
};

#endif