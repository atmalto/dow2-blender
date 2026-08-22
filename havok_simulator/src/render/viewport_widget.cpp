#include "viewport_widget.h"

#include <cmath>

#include <QColor>
#include <QFont>
#include <QFontMetrics>
#include <QKeyEvent>
#include <QMouseEvent>
#include <QWheelEvent>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>
#include <GL/glu.h>

#include "capsule_render_utils.h"
#include "scene_body_renderer.h"
#include "simulation_controller.h"
#include "viewport_overlay_renderer.h"
#include "viewport_tool_controller.h"

namespace
{
    float grid_line_alpha(float axis_value, float segment_value)
    {
        const float distance = std::sqrt(axis_value * axis_value + segment_value * segment_value);
        float alpha = 0.34f - distance * 0.0024f;

        if (alpha < 0.0f)
        {
            alpha = 0.0f;
        }

        return alpha;
    }
}

ViewportWidget::ViewportWidget(QWidget* parent)
    : QGLWidget(parent)
    , m_simulation(0)
    , m_overlay_renderer(0)
    , m_tool_controller(0)
{
    setMinimumSize(640, 480);
    setFocusPolicy(Qt::StrongFocus);
    setMouseTracking(true);

    m_overlay_renderer = new ViewportOverlayRenderer(*this, m_camera);
    m_tool_controller = new ViewportToolController(*this, m_camera);
}

ViewportWidget::~ViewportWidget()
{
    delete m_overlay_renderer;
    m_overlay_renderer = 0;
    delete m_tool_controller;
    m_tool_controller = 0;
}

void ViewportWidget::set_simulation(SimulationController* simulation)
{
    m_simulation = simulation;
    if (m_overlay_renderer)
    {
        m_overlay_renderer->set_simulation(simulation);
    }
    if (m_tool_controller)
    {
        m_tool_controller->set_simulation(simulation);
    }
}

void ViewportWidget::initializeGL()
{
    qglClearColor(QColor(30, 34, 40));
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_CULL_FACE);
}

void ViewportWidget::resizeGL(int width, int height)
{
    glViewport(0, 0, width, height);
    m_camera.apply_projection(width, height);
}

void ViewportWidget::paintGL()
{
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    apply_camera_transform();

    draw_grid();
    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_axes();
    }

    if (m_simulation)
    {
        const std::vector<BodyRenderState>& bodies = m_simulation->render_bodies();
        std::size_t body_index = 0;
        for (body_index = 0; body_index < bodies.size(); ++body_index)
        {
            SceneBodyRenderer::draw_body(bodies[body_index]);
        }

        const std::vector<BodyRenderState>& preview_bodies = m_simulation->preview_bodies();
        for (body_index = 0; body_index < preview_bodies.size(); ++body_index)
        {
            SceneBodyRenderer::draw_body(preview_bodies[body_index]);
        }

        if (m_overlay_renderer)
        {
            m_overlay_renderer->draw_axis_move_guide();
            m_overlay_renderer->draw_axis_rotate_guide();
            m_overlay_renderer->draw_entity_labels();
        }
    }

    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_screen_overlay();
    }
}

void ViewportWidget::keyPressEvent(QKeyEvent* event)
{
    if (!m_tool_controller || !m_tool_controller->key_press(event))
    {
        QGLWidget::keyPressEvent(event);
    }
}

void ViewportWidget::mousePressEvent(QMouseEvent* event)
{
    if (m_tool_controller)
    {
        m_tool_controller->mouse_press(event);
    }
}

void ViewportWidget::mouseMoveEvent(QMouseEvent* event)
{
    if (m_tool_controller)
    {
        m_tool_controller->mouse_move(event);
    }
}

void ViewportWidget::mouseReleaseEvent(QMouseEvent* event)
{
    if (m_tool_controller)
    {
        m_tool_controller->mouse_release(event);
    }
}

void ViewportWidget::wheelEvent(QWheelEvent* event)
{
    const float delta_steps = static_cast<float>(event->delta()) / 120.0f;
    m_camera.zoom(delta_steps);
    resizeGL(width(), height());
    updateGL();
}

void ViewportWidget::apply_camera_transform()
{
    m_camera.apply_view_transform();
}

void ViewportWidget::notify_selection_changed()
{
    emit selection_changed();
}

void ViewportWidget::draw_axes()
{
    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_axes();
    }
}

void ViewportWidget::draw_axis_move_guide()
{
    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_axis_move_guide();
    }
}

void ViewportWidget::draw_axis_rotate_guide()
{
    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_axis_rotate_guide();
    }
}

void ViewportWidget::draw_body(const BodyRenderState& body)
{
    BodyRenderState shaded_body = body;
    const bool should_draw_transparent_capsule_fill =
        shaded_body.shape_type == BodyRenderState::ShapeCapsule && !shaded_body.is_preview;
    const bool should_draw_wireframe =
        (shaded_body.is_solid || should_draw_transparent_capsule_fill) && !shaded_body.is_preview;

    if (shaded_body.is_selected && !shaded_body.is_preview)
    {
        shaded_body.color[0] = shaded_body.color[0] + (1.0f - shaded_body.color[0]) * 0.52f;
        shaded_body.color[1] = shaded_body.color[1] + (0.92f - shaded_body.color[1]) * 0.52f;
        shaded_body.color[2] = shaded_body.color[2] + (0.26f - shaded_body.color[2]) * 0.52f;
    }

    glPushMatrix();
    apply_body_transform(shaded_body);

    if (should_draw_wireframe && !should_draw_transparent_capsule_fill)
    {
        glEnable(GL_POLYGON_OFFSET_FILL);
        glPolygonOffset(1.0f, 1.0f);
    }

    if (should_draw_transparent_capsule_fill)
    {
        CapsuleRenderFrame frame;

        if (build_capsule_render_frame(shaded_body, &frame))
        {
            const float capsule_alpha = shaded_body.is_selected ? 0.70f : 0.52f;
            glEnable(GL_BLEND);
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
            glDepthMask(GL_FALSE);
            glColor4f(shaded_body.color[0], shaded_body.color[1], shaded_body.color[2], capsule_alpha);
            draw_capsule_solid_geometry(frame);
            glDepthMask(GL_TRUE);
            glDisable(GL_BLEND);
        }
        else
        {
            draw_capsule(shaded_body);
        }
    }
    else if (shaded_body.shape_type == BodyRenderState::ShapeBox)
    {
        draw_box(shaded_body);
    }
    else if (shaded_body.shape_type == BodyRenderState::ShapeSphere)
    {
        draw_sphere(shaded_body);
    }
    else if (shaded_body.shape_type == BodyRenderState::ShapeCapsule)
    {
        draw_capsule(shaded_body);
    }
    else if (shaded_body.shape_type == BodyRenderState::ShapeWedge)
    {
        draw_wedge(shaded_body);
    }
    else if (shaded_body.shape_type == BodyRenderState::ShapeConvexHull)
    {
        draw_convex_hull(shaded_body);
    }
    else
    {
        draw_arrow(shaded_body);
    }

    if (should_draw_wireframe)
    {
        if (!should_draw_transparent_capsule_fill)
        {
            glDisable(GL_POLYGON_OFFSET_FILL);
        }
        draw_wireframe_overlay(shaded_body);
    }

    if (shaded_body.is_selected && !shaded_body.is_preview)
    {
        draw_selection_overlay(shaded_body);
    }

    glPopMatrix();
}

void ViewportWidget::draw_wireframe_overlay(const BodyRenderState& body)
{
    BodyRenderState overlay = body;

    overlay.is_solid = false;
    overlay.is_preview = false;
    overlay.color[0] = 0.14f;
    overlay.color[1] = 0.16f;
    overlay.color[2] = 0.19f;

    if (overlay.shape_type == BodyRenderState::ShapeBox)
    {
        draw_box(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeSphere)
    {
        draw_sphere(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeCapsule)
    {
        draw_capsule(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeWedge)
    {
        draw_wedge(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeConvexHull)
    {
        draw_convex_hull(overlay);
    }
}

void ViewportWidget::draw_selection_overlay(const BodyRenderState& body)
{
    BodyRenderState overlay = body;

    overlay.is_solid = false;
    overlay.is_preview = true;
    overlay.color[0] = 1.0f;
    overlay.color[1] = 0.96f;
    overlay.color[2] = 0.38f;

    glDisable(GL_DEPTH_TEST);

    if (overlay.shape_type == BodyRenderState::ShapeBox)
    {
        draw_box(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeSphere)
    {
        draw_sphere(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeCapsule)
    {
        draw_capsule(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeWedge)
    {
        draw_wedge(overlay);
    }
    else if (overlay.shape_type == BodyRenderState::ShapeConvexHull)
    {
        draw_convex_hull(overlay);
    }
    else
    {
        draw_arrow(overlay);
    }

    glEnable(GL_DEPTH_TEST);
}

void ViewportWidget::draw_box(const BodyRenderState& body)
{
    const float x = body.half_extents[0];
    const float y = body.half_extents[1];
    const float z = body.half_extents[2];

    glColor3f(body.color[0], body.color[1], body.color[2]);

    if (body.is_solid)
    {
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
    else
    {
        glLineWidth(body.is_preview ? 1.5f : 1.0f);
        glBegin(GL_LINES);

        glVertex3f(-x, -y, -z); glVertex3f(x, -y, -z);
        glVertex3f(x, -y, -z); glVertex3f(x, y, -z);
        glVertex3f(x, y, -z); glVertex3f(-x, y, -z);
        glVertex3f(-x, y, -z); glVertex3f(-x, -y, -z);

        glVertex3f(-x, -y, z); glVertex3f(x, -y, z);
        glVertex3f(x, -y, z); glVertex3f(x, y, z);
        glVertex3f(x, y, z); glVertex3f(-x, y, z);
        glVertex3f(-x, y, z); glVertex3f(-x, -y, z);

        glVertex3f(-x, -y, -z); glVertex3f(-x, -y, z);
        glVertex3f(x, -y, -z); glVertex3f(x, -y, z);
        glVertex3f(x, y, -z); glVertex3f(x, y, z);
        glVertex3f(-x, y, -z); glVertex3f(-x, y, z);

        glEnd();
    }
}

void ViewportWidget::draw_sphere(const BodyRenderState& body)
{
    const float radius = body.radius;

    glColor3f(body.color[0], body.color[1], body.color[2]);

    if (body.is_solid)
    {
        GLUquadric* quadric = gluNewQuadric();
        gluQuadricDrawStyle(quadric, GLU_FILL);
        gluQuadricNormals(quadric, GLU_FLAT);
        gluSphere(quadric, radius, 20, 14);
        gluDeleteQuadric(quadric);
        return;
    }

    const int segments = 24;
    glLineWidth(body.is_preview ? 1.5f : 1.0f);

    for (int ring = 0; ring < 3; ++ring)
    {
        glBegin(GL_LINE_LOOP);
        for (int segment = 0; segment < segments; ++segment)
        {
            const float angle = static_cast<float>(segment) / static_cast<float>(segments) * 6.2831853f;
            const float cs = std::cos(angle) * radius;
            const float sn = std::sin(angle) * radius;

            if (ring == 0)
            {
                glVertex3f(cs, sn, 0.0f);
            }
            else if (ring == 1)
            {
                glVertex3f(cs, 0.0f, sn);
            }
            else
            {
                glVertex3f(0.0f, cs, sn);
            }
        }
        glEnd();
    }
}

void ViewportWidget::draw_capsule(const BodyRenderState& body)
{
    CapsuleRenderFrame frame;

    if (!build_capsule_render_frame(body, &frame))
    {
        return;
    }

    glColor3f(body.color[0], body.color[1], body.color[2]);

    if (body.is_solid)
    {
        draw_capsule_solid_geometry(frame);
        return;
    }

    draw_capsule_wireframe_geometry(frame, body.is_preview);
}

void ViewportWidget::draw_wedge(const BodyRenderState& body)
{
    const float x = body.half_extents[0];
    const float y = body.half_extents[1];
    const float z = body.half_extents[2];

    glColor3f(body.color[0], body.color[1], body.color[2]);

    if (body.is_solid)
    {
        glShadeModel(GL_FLAT);
        glBegin(GL_TRIANGLES);

        glNormal3f(0.0f, 0.0f, -1.0f);
        glVertex3f(-x, -y, -z); glVertex3f(x, -y, -z); glVertex3f(-x, y, -z);

        glNormal3f(0.0f, 0.0f, 1.0f);
        glVertex3f(-x, -y, z); glVertex3f(-x, y, z); glVertex3f(x, -y, z);

        glEnd();

        glBegin(GL_QUADS);

        glNormal3f(0.0f, -1.0f, 0.0f);
        glVertex3f(-x, -y, -z); glVertex3f(-x, -y, z); glVertex3f(x, -y, z); glVertex3f(x, -y, -z);

        glNormal3f(-1.0f, 0.0f, 0.0f);
        glVertex3f(-x, -y, -z); glVertex3f(-x, y, -z); glVertex3f(-x, y, z); glVertex3f(-x, -y, z);

        glNormal3f(0.7f, 0.7f, 0.0f);
        glVertex3f(-x, y, -z); glVertex3f(x, -y, -z); glVertex3f(x, -y, z); glVertex3f(-x, y, z);

        glEnd();
        return;
    }

    glLineWidth(body.is_preview ? 1.5f : 1.0f);
    glBegin(GL_LINES);

    glVertex3f(-x, -y, -z); glVertex3f(-x, -y, z);
    glVertex3f(-x, -y, z); glVertex3f(x, -y, z);
    glVertex3f(x, -y, z); glVertex3f(x, -y, -z);
    glVertex3f(x, -y, -z); glVertex3f(-x, -y, -z);

    glVertex3f(-x, y, -z); glVertex3f(-x, y, z);
    glVertex3f(-x, y, z); glVertex3f(x, -y, z);
    glVertex3f(-x, y, -z); glVertex3f(x, -y, -z);

    glVertex3f(-x, -y, -z); glVertex3f(-x, y, -z);
    glVertex3f(-x, -y, z); glVertex3f(-x, y, z);

    glEnd();
}

void ViewportWidget::draw_convex_hull(const BodyRenderState& body)
{
    std::size_t vertex_index = 0;

    if (body.mesh_vertices.empty())
    {
        return;
    }

    glColor3f(body.color[0], body.color[1], body.color[2]);

    if (body.is_solid)
    {
        glShadeModel(GL_FLAT);
        glBegin(GL_TRIANGLES);

        for (vertex_index = 0; vertex_index + 8 < body.mesh_vertices.size(); vertex_index += 9)
        {
            const float ax = body.mesh_vertices[vertex_index + 0];
            const float ay = body.mesh_vertices[vertex_index + 1];
            const float az = body.mesh_vertices[vertex_index + 2];
            const float bx = body.mesh_vertices[vertex_index + 3];
            const float by = body.mesh_vertices[vertex_index + 4];
            const float bz = body.mesh_vertices[vertex_index + 5];
            const float cx = body.mesh_vertices[vertex_index + 6];
            const float cy = body.mesh_vertices[vertex_index + 7];
            const float cz = body.mesh_vertices[vertex_index + 8];
            const float ux = bx - ax;
            const float uy = by - ay;
            const float uz = bz - az;
            const float vx = cx - ax;
            const float vy = cy - ay;
            const float vz = cz - az;
            const float nx = uy * vz - uz * vy;
            const float ny = uz * vx - ux * vz;
            const float nz = ux * vy - uy * vx;

            glNormal3f(nx, ny, nz);
            glVertex3f(ax, ay, az);
            glVertex3f(bx, by, bz);
            glVertex3f(cx, cy, cz);
        }

        glEnd();
        return;
    }

    glLineWidth(body.is_preview ? 1.5f : 1.0f);
    glBegin(GL_LINES);

    for (vertex_index = 0; vertex_index + 8 < body.mesh_vertices.size(); vertex_index += 9)
    {
        const float ax = body.mesh_vertices[vertex_index + 0];
        const float ay = body.mesh_vertices[vertex_index + 1];
        const float az = body.mesh_vertices[vertex_index + 2];
        const float bx = body.mesh_vertices[vertex_index + 3];
        const float by = body.mesh_vertices[vertex_index + 4];
        const float bz = body.mesh_vertices[vertex_index + 5];
        const float cx = body.mesh_vertices[vertex_index + 6];
        const float cy = body.mesh_vertices[vertex_index + 7];
        const float cz = body.mesh_vertices[vertex_index + 8];

        glVertex3f(ax, ay, az); glVertex3f(bx, by, bz);
        glVertex3f(bx, by, bz); glVertex3f(cx, cy, cz);
        glVertex3f(cx, cy, cz); glVertex3f(ax, ay, az);
    }

    glEnd();
}

void ViewportWidget::draw_arrow(const BodyRenderState& body)
{
    const float shaft_length = body.half_extents[0];
    const float head_length = shaft_length * 0.28f;
    const float wing = body.half_extents[1] > 0.05f ? body.half_extents[1] : 1.2f;
    const float ray_length = body.half_extents[2] > shaft_length ? body.half_extents[2] : shaft_length;
    const float shaft_line_width = body.is_preview ? 5.0f : 3.0f;
    const float tail_line_width = body.is_preview ? 3.0f : 1.0f;

    glColor3f(body.color[0], body.color[1], body.color[2]);
    glLineWidth(shaft_line_width);
    glBegin(GL_LINES);

    glVertex3f(0.0f, 0.0f, 0.0f);
    glVertex3f(0.0f, 0.0f, -shaft_length);

    glVertex3f(0.0f, 0.0f, -shaft_length);
    glVertex3f(wing * 0.35f, 0.0f, -shaft_length + head_length);

    glVertex3f(0.0f, 0.0f, -shaft_length);
    glVertex3f(-wing * 0.35f, 0.0f, -shaft_length + head_length);

    glVertex3f(0.0f, 0.0f, -shaft_length);
    glVertex3f(0.0f, wing * 0.35f, -shaft_length + head_length);

    glVertex3f(0.0f, 0.0f, -shaft_length);
    glVertex3f(0.0f, -wing * 0.35f, -shaft_length + head_length);

    glEnd();

    glLineWidth(tail_line_width);
    glBegin(GL_LINES);
    glVertex3f(0.0f, 0.0f, -shaft_length);
    glVertex3f(0.0f, 0.0f, -ray_length);
    glEnd();
}

void ViewportWidget::apply_body_transform(const BodyRenderState& body)
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

    const GLfloat matrix[16] = {
        1.0f - 2.0f * (yy + zz), 2.0f * (xy + wz), 2.0f * (xz - wy), 0.0f,
        2.0f * (xy - wz), 1.0f - 2.0f * (xx + zz), 2.0f * (yz + wx), 0.0f,
        2.0f * (xz + wy), 2.0f * (yz - wx), 1.0f - 2.0f * (xx + yy), 0.0f,
        body.position[0], body.position[1], body.position[2], 1.0f
    };

    glMultMatrixf(matrix);
}

void ViewportWidget::draw_grid()
{
    const float elevation = 0.001f;

    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    // Let the grid write depth so it participates correctly in depth testing.
    // Drawn before the scene objects, this makes the y=0 grid intersect/cut
    // through geometry at its true 3D position instead of always being hidden
    // behind objects (which happens when the grid is depth-masked out).
    glDepthMask(GL_TRUE);
    glLineWidth(1.0f);
    glBegin(GL_LINES);

    for (int axis = -120; axis <= 120; ++axis)
    {
        const float line = static_cast<float>(axis);
        const float line_strength = (axis % 10) == 0 ? 1.0f : 0.55f;

        for (int segment = -120; segment < 120; ++segment)
        {
            const float segment_start = static_cast<float>(segment);
            const float segment_end = static_cast<float>(segment + 1);
            const float alpha_start = grid_line_alpha(line, segment_start) * line_strength;
            const float alpha_end = grid_line_alpha(line, segment_end) * line_strength;

            if (alpha_start > 0.0f || alpha_end > 0.0f)
            {
                glColor4f(0.88f, 0.9f, 0.94f, alpha_start);
                glVertex3f(line, elevation, segment_start);
                glColor4f(0.88f, 0.9f, 0.94f, alpha_end);
                glVertex3f(line, elevation, segment_end);

                glColor4f(0.88f, 0.9f, 0.94f, alpha_start);
                glVertex3f(segment_start, elevation, line);
                glColor4f(0.88f, 0.9f, 0.94f, alpha_end);
                glVertex3f(segment_end, elevation, line);
            }
        }
    }

    glEnd();
    glDepthMask(GL_TRUE);
    glDisable(GL_BLEND);
}

void ViewportWidget::draw_entity_labels()
{
    if (m_overlay_renderer)
    {
        m_overlay_renderer->draw_entity_labels();
    }
}