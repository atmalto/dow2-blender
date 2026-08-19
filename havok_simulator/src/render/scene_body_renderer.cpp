#include "scene_body_renderer.h"

#include <cmath>

#ifdef _WIN32
#include <windows.h>
#endif

#include <GL/gl.h>
#include <GL/glu.h>

#include "capsule_render_utils.h"

void SceneBodyRenderer::draw_body(const BodyRenderState& body)
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
			draw_capsule(shaded_body, true);
		}
	}
	else
	{
		draw_body_geometry(shaded_body);
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

void SceneBodyRenderer::draw_body_geometry(const BodyRenderState& body, bool use_body_color)
{
	if (body.shape_type == BodyRenderState::ShapeBox)
	{
		draw_box(body, use_body_color);
	}
	else if (body.shape_type == BodyRenderState::ShapeSphere)
	{
		draw_sphere(body, use_body_color);
	}
	else if (body.shape_type == BodyRenderState::ShapeCapsule)
	{
		draw_capsule(body, use_body_color);
	}
	else if (body.shape_type == BodyRenderState::ShapeWedge)
	{
		draw_wedge(body, use_body_color);
	}
	else if (body.shape_type == BodyRenderState::ShapeConvexHull)
	{
		draw_convex_hull(body, use_body_color);
	}
	else
	{
		draw_arrow(body, use_body_color);
	}
}

void SceneBodyRenderer::draw_wireframe_overlay(const BodyRenderState& body)
{
	BodyRenderState overlay = body;

	overlay.is_solid = false;
	overlay.is_preview = false;
	overlay.color[0] = 0.14f;
	overlay.color[1] = 0.16f;
	overlay.color[2] = 0.19f;

	draw_body_geometry(overlay);
}

void SceneBodyRenderer::draw_selection_overlay(const BodyRenderState& body)
{
	BodyRenderState overlay = body;

	overlay.is_solid = false;
	overlay.is_preview = true;
	overlay.color[0] = 1.0f;
	overlay.color[1] = 0.96f;
	overlay.color[2] = 0.38f;

	glDisable(GL_DEPTH_TEST);
	draw_body_geometry(overlay);
	glEnable(GL_DEPTH_TEST);
}

void SceneBodyRenderer::draw_box(const BodyRenderState& body, bool use_body_color)
{
	const float x = body.half_extents[0];
	const float y = body.half_extents[1];
	const float z = body.half_extents[2];

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

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

void SceneBodyRenderer::draw_sphere(const BodyRenderState& body, bool use_body_color)
{
	const float radius = body.radius;

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

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

void SceneBodyRenderer::draw_capsule(const BodyRenderState& body, bool use_body_color)
{
	CapsuleRenderFrame frame;

	if (!build_capsule_render_frame(body, &frame))
	{
		return;
	}

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

	if (body.is_solid)
	{
		draw_capsule_solid_geometry(frame);
		return;
	}

	draw_capsule_wireframe_geometry(frame, body.is_preview);
}

void SceneBodyRenderer::draw_wedge(const BodyRenderState& body, bool use_body_color)
{
	const float x = body.half_extents[0];
	const float y = body.half_extents[1];
	const float z = body.half_extents[2];

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

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

void SceneBodyRenderer::draw_convex_hull(const BodyRenderState& body, bool use_body_color)
{
	std::size_t vertex_index = 0;

	if (body.mesh_vertices.empty())
	{
		return;
	}

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

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

void SceneBodyRenderer::draw_arrow(const BodyRenderState& body, bool use_body_color)
{
	const float shaft_length = body.half_extents[0];
	const float head_length = shaft_length * 0.28f;
	const float wing = body.half_extents[1] > 0.05f ? body.half_extents[1] : 1.2f;
	const float ray_length = body.half_extents[2] > shaft_length ? body.half_extents[2] : shaft_length;
	const float shaft_line_width = body.is_preview ? 5.0f : 3.0f;
	const float tail_line_width = body.is_preview ? 3.0f : 1.0f;

	if (use_body_color)
	{
		glColor3f(body.color[0], body.color[1], body.color[2]);
	}

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

void SceneBodyRenderer::apply_body_transform(const BodyRenderState& body)
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
