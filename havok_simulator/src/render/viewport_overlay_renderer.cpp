#include "viewport_overlay_renderer.h"

#include <cmath>

#include <QColor>
#include <QFont>
#include <QFontMetrics>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>

#include "simulation_controller.h"
#include "viewport_camera.h"
#include "viewport_widget.h"

ViewportOverlayRenderer::ViewportOverlayRenderer(ViewportWidget& viewport, ViewportCamera& camera)
    : m_viewport(viewport)
    , m_camera(camera)
    , m_simulation(0)
{
}

void ViewportOverlayRenderer::set_simulation(SimulationController* simulation)
{
    m_simulation = simulation;
}

void ViewportOverlayRenderer::draw_axes() const
{
    QFont axis_font = m_viewport.font();
    int font_size = axis_font.pointSize();

    if (font_size < 0)
    {
        font_size = 11;
    }

    axis_font.setBold(true);
    axis_font.setPointSize(font_size + 1);

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

    m_viewport.qglColor(QColor(209, 74, 74));
    m_viewport.renderText(4.2, 0.0, 0.0, "X", axis_font);

    m_viewport.qglColor(QColor(92, 186, 110));
    m_viewport.renderText(0.0, 4.2, 0.0, "Z", axis_font);

    m_viewport.qglColor(QColor(89, 148, 219));
    m_viewport.renderText(0.0, 0.0, 4.2, "Y", axis_font);
}

void ViewportOverlayRenderer::draw_axis_move_guide() const
{
    if (!m_simulation)
    {
        return;
    }

    const SceneAxisMoveSession& move_session = m_simulation->axis_move_session();
    const float guide_length = m_camera.distance() > 12.0f ? m_camera.distance() : 12.0f;

    if (!move_session.active)
    {
        return;
    }

    glLineWidth(2.0f);
    glEnable(GL_LINE_STIPPLE);
    glLineStipple(1, 0x0F0F);

    if (move_session.axis == SceneMoveAxisX)
    {
        glColor3f(0.95f, 0.34f, 0.34f);
        glBegin(GL_LINES);
        glVertex3f(move_session.preview_position[0] - guide_length, move_session.preview_position[1], move_session.preview_position[2]);
        glVertex3f(move_session.preview_position[0] + guide_length, move_session.preview_position[1], move_session.preview_position[2]);
        glEnd();
    }
    else if (move_session.axis == SceneMoveAxisY)
    {
        glColor3f(0.41f, 0.82f, 0.48f);
        glBegin(GL_LINES);
        glVertex3f(move_session.preview_position[0], move_session.preview_position[1] - guide_length, move_session.preview_position[2]);
        glVertex3f(move_session.preview_position[0], move_session.preview_position[1] + guide_length, move_session.preview_position[2]);
        glEnd();
    }
    else if (move_session.axis == SceneMoveAxisZ)
    {
        glColor3f(0.42f, 0.67f, 0.94f);
        glBegin(GL_LINES);
        glVertex3f(move_session.preview_position[0], move_session.preview_position[1], move_session.preview_position[2] - guide_length);
        glVertex3f(move_session.preview_position[0], move_session.preview_position[1], move_session.preview_position[2] + guide_length);
        glEnd();
    }

    glDisable(GL_LINE_STIPPLE);
}

void ViewportOverlayRenderer::draw_axis_rotate_guide() const
{
    if (!m_simulation)
    {
        return;
    }

    const SceneAxisRotateSession& rotate_session = m_simulation->axis_rotate_session();
    const float guide_length = m_camera.distance() > 12.0f ? m_camera.distance() : 12.0f;
    const float guide_radius = m_camera.distance() > 18.0f ? m_camera.distance() * 0.18f : 3.5f;
    const int segments = 40;

    if (!rotate_session.active)
    {
        return;
    }

    glLineWidth(2.0f);
    glEnable(GL_LINE_STIPPLE);
    glLineStipple(1, 0x0F0F);

    if (rotate_session.axis == SceneMoveAxisX)
    {
        glColor3f(0.95f, 0.34f, 0.34f);
        glBegin(GL_LINES);
        glVertex3f(rotate_session.pivot_position[0] - guide_length, rotate_session.pivot_position[1], rotate_session.pivot_position[2]);
        glVertex3f(rotate_session.pivot_position[0] + guide_length, rotate_session.pivot_position[1], rotate_session.pivot_position[2]);
        glEnd();

        glBegin(GL_LINE_LOOP);
        for (int segment = 0; segment < segments; ++segment)
        {
            const float angle = static_cast<float>(segment) / static_cast<float>(segments) * 6.2831853f;
            glVertex3f(
                rotate_session.pivot_position[0],
                rotate_session.pivot_position[1] + std::cos(angle) * guide_radius,
                rotate_session.pivot_position[2] + std::sin(angle) * guide_radius);
        }
        glEnd();
    }
    else if (rotate_session.axis == SceneMoveAxisY)
    {
        glColor3f(0.41f, 0.82f, 0.48f);
        glBegin(GL_LINES);
        glVertex3f(rotate_session.pivot_position[0], rotate_session.pivot_position[1] - guide_length, rotate_session.pivot_position[2]);
        glVertex3f(rotate_session.pivot_position[0], rotate_session.pivot_position[1] + guide_length, rotate_session.pivot_position[2]);
        glEnd();

        glBegin(GL_LINE_LOOP);
        for (int segment = 0; segment < segments; ++segment)
        {
            const float angle = static_cast<float>(segment) / static_cast<float>(segments) * 6.2831853f;
            glVertex3f(
                rotate_session.pivot_position[0] + std::cos(angle) * guide_radius,
                rotate_session.pivot_position[1],
                rotate_session.pivot_position[2] + std::sin(angle) * guide_radius);
        }
        glEnd();
    }
    else if (rotate_session.axis == SceneMoveAxisZ)
    {
        glColor3f(0.42f, 0.67f, 0.94f);
        glBegin(GL_LINES);
        glVertex3f(rotate_session.pivot_position[0], rotate_session.pivot_position[1], rotate_session.pivot_position[2] - guide_length);
        glVertex3f(rotate_session.pivot_position[0], rotate_session.pivot_position[1], rotate_session.pivot_position[2] + guide_length);
        glEnd();

        glBegin(GL_LINE_LOOP);
        for (int segment = 0; segment < segments; ++segment)
        {
            const float angle = static_cast<float>(segment) / static_cast<float>(segments) * 6.2831853f;
            glVertex3f(
                rotate_session.pivot_position[0] + std::cos(angle) * guide_radius,
                rotate_session.pivot_position[1] + std::sin(angle) * guide_radius,
                rotate_session.pivot_position[2]);
        }
        glEnd();
    }

    glDisable(GL_LINE_STIPPLE);
}

void ViewportOverlayRenderer::draw_entity_labels() const
{
    if (!m_simulation)
    {
        return;
    }

    const SceneDocument& scene_document = m_simulation->scene_document();
    const SceneEntitySelection& selected = m_simulation->selected_entity();
    const std::vector<BodyRenderState>& render_bodies = m_simulation->render_bodies();
    const std::vector<RagdollSceneEntity>& ragdolls = scene_document.ragdolls();
    const std::vector<PhysicsObjectSceneEntity>& objects = scene_document.objects();
    const std::vector<ForceSceneEntity>& forces = scene_document.forces();
    std::size_t entity_index = 0;

    glDisable(GL_DEPTH_TEST);

    for (entity_index = 0; entity_index < ragdolls.size(); ++entity_index)
    {
        float label_position[3] = {
            ragdolls[entity_index].ragdoll.position[0],
            ragdolls[entity_index].ragdoll.position[1],
            ragdolls[entity_index].ragdoll.position[2]
        };
        int body_count = 0;
        std::size_t body_index = 0;

        for (body_index = 0; body_index < render_bodies.size(); ++body_index)
        {
            if (render_bodies[body_index].entity_id != ragdolls[entity_index].record.id ||
                render_bodies[body_index].entity_kind != SceneEntityKindRagdoll)
            {
                continue;
            }

            if (body_count == 0)
            {
                label_position[0] = 0.0f;
                label_position[1] = 0.0f;
                label_position[2] = 0.0f;
            }

            label_position[0] += render_bodies[body_index].position[0];
            label_position[1] += render_bodies[body_index].position[1];
            label_position[2] += render_bodies[body_index].position[2];
            ++body_count;
        }

        if (body_count > 0)
        {
            label_position[0] /= static_cast<float>(body_count);
            label_position[1] /= static_cast<float>(body_count);
            label_position[2] /= static_cast<float>(body_count);
        }

        m_viewport.qglColor(selected.id == ragdolls[entity_index].record.id && selected.kind == SceneEntityKindRagdoll
            ? QColor(255, 244, 120)
            : QColor(232, 236, 242));
        m_viewport.renderText(
            label_position[0],
            label_position[1] + 2.0f,
            label_position[2],
            QString::fromLocal8Bit(ragdolls[entity_index].record.name.c_str()));
    }

    for (entity_index = 0; entity_index < forces.size(); ++entity_index)
    {
        m_viewport.qglColor(selected.id == forces[entity_index].record.id && selected.kind == SceneEntityKindForce
            ? QColor(255, 244, 120)
            : QColor(232, 236, 242));
        m_viewport.renderText(
            forces[entity_index].force_spec.position[0],
            forces[entity_index].force_spec.position[1] + 1.5f,
            forces[entity_index].force_spec.position[2],
            QString::fromLocal8Bit(forces[entity_index].record.name.c_str()));
    }

    for (entity_index = 0; entity_index < objects.size(); ++entity_index)
    {
        const PhysicsObjectSceneEntity& object = objects[entity_index];
        float label_position[3] = {
            object.object_spec.position[0],
            object.object_spec.position[1],
            object.object_spec.position[2]
        };
        const float vertical_offset = object.object_spec.scale[1] + 0.8f;
        std::size_t body_index = 0;

        for (body_index = 0; body_index < render_bodies.size(); ++body_index)
        {
            if (render_bodies[body_index].entity_id == object.record.id &&
                render_bodies[body_index].entity_kind == SceneEntityKindPhysicsObject)
            {
                label_position[0] = render_bodies[body_index].position[0];
                label_position[1] = render_bodies[body_index].position[1];
                label_position[2] = render_bodies[body_index].position[2];
                break;
            }
        }

        m_viewport.qglColor(selected.id == object.record.id && selected.kind == SceneEntityKindPhysicsObject
            ? QColor(255, 244, 120)
            : QColor(232, 236, 242));
        m_viewport.renderText(
            label_position[0],
            label_position[1] + vertical_offset,
            label_position[2],
            QString::fromLocal8Bit(object.record.name.c_str()));
    }

    glEnable(GL_DEPTH_TEST);
}

void ViewportOverlayRenderer::draw_screen_overlay() const
{
    glDisable(GL_DEPTH_TEST);
    m_viewport.qglColor(QColor(220, 224, 230));
    m_viewport.renderText(24.0, 36.0, "Shortcuts");
    m_viewport.renderText(24.0, 60.0, "Camera");
    m_viewport.renderText(40.0, 80.0, "Click: select");
    m_viewport.renderText(40.0, 100.0, "LMB drag: orbit camera");
    m_viewport.renderText(40.0, 120.0, "RMB drag: pan camera");
    m_viewport.renderText(40.0, 140.0, "Wheel: zoom camera");
    m_viewport.renderText(40.0, 160.0, "Ctrl+X: right / left orthographic snap");
    m_viewport.renderText(40.0, 180.0, "Ctrl+Y: front / back orthographic snap");
    m_viewport.renderText(40.0, 200.0, "Ctrl+Z: top / bottom orthographic snap");
    m_viewport.renderText(40.0, 220.0, "Repeat same Ctrl+axis: flip to opposite side");
    m_viewport.renderText(40.0, 240.0, "Orbit while snapped: return to perspective");
    m_viewport.renderText(24.0, 268.0, "Transform");
    m_viewport.renderText(40.0, 288.0, "X / Y / Z: move selected object on axis");
    m_viewport.renderText(40.0, 308.0, "Shift+X / Shift+Y / Shift+Z: rotate selected object on axis");
    m_viewport.renderText(40.0, 328.0, "S: uniformly scale selected cube / wedge / sphere");
    m_viewport.renderText(40.0, 348.0, "Mouse left / right while scaling: smaller / larger");
    m_viewport.renderText(40.0, 368.0, "LMB: confirm active transform");
    m_viewport.renderText(40.0, 388.0, "Esc: cancel active transform");
    m_viewport.renderText(24.0, 416.0, "Scene");
    m_viewport.renderText(40.0, 436.0, "Space: play / pause simulation");
    m_viewport.renderText(40.0, 456.0, "Right Arrow: step simulation");
    m_viewport.renderText(40.0, 476.0, "Backspace: reset simulation");
    m_viewport.renderText(40.0, 496.0, "R: add rigid body object");
    m_viewport.renderText(40.0, 516.0, "F: add force");
    m_viewport.renderText(40.0, 536.0, "E: edit selected object");
    m_viewport.renderText(40.0, 556.0, "Delete: delete selected object");
    m_viewport.renderText(40.0, 576.0, "Ctrl+N: new scene");
    m_viewport.renderText(40.0, 596.0, "Ctrl+W: clear scene");

    if (m_camera.is_orthographic())
    {
        const QString ortho_label = QString::fromLatin1(m_camera.orthographic_view_label());
        if (!ortho_label.isEmpty())
        {
            QFont overlay_font = m_viewport.font();
            QFontMetrics overlay_metrics(overlay_font);
            int font_size = overlay_font.pointSize();

            if (font_size < 0)
            {
                font_size = 12;
            }

            overlay_font.setBold(true);
            overlay_font.setPointSize(font_size + 2);
            overlay_metrics = QFontMetrics(overlay_font);
            m_viewport.renderText(
                static_cast<double>(m_viewport.width() - overlay_metrics.width(ortho_label) - 24),
                40.0,
                ortho_label,
                overlay_font);
        }
    }

    glEnable(GL_DEPTH_TEST);
}