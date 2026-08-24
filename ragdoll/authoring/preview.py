from __future__ import annotations

import math
import time

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix, Vector

from .collections import remove_collection_tree
from .constraint_props import read_constraint_settings
from .constants import (
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_BODY_VERTEX_A_PROP,
    RAGDOLL_BODY_VERTEX_B_PROP,
)
from .geometry import _dx_vector_to_blender_local
from ...model.skeleton_space import remove_bone_axis_adapter
from .props import _vector_prop
from .queries import _body_object_by_bone_name, _ragdoll_bones_in_order, is_ragdoll_skeleton_object, resolve_ragdoll_body_object


_CONSTRAINT_PREVIEW_WAS_ENABLED = False
_CONSTRAINT_PREVIEW_DRAW_HANDLE = None
_CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE = None
_CONSTRAINT_PREVIEW_ARROW_SEGMENTS: list[tuple[Vector, Vector]] = []
_CONSTRAINT_PREVIEW_CONE_SEGMENTS: list[tuple[Vector, Vector]] = []
_CONSTRAINT_PREVIEW_PLANE_SEGMENTS: list[tuple[Vector, Vector]] = []
_CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS: list[tuple[Vector, Vector]] = []
_CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE: tuple[object, ...] = ()
_CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES: tuple[str, ...] = ()
_CONSTRAINT_PREVIEW_LAST_CHANGE_TIME = 0.0
_CONSTRAINT_PREVIEW_DEBOUNCE_SECONDS = 0.1


def _constraint_preview_enabled() -> bool:
    scene = getattr(bpy.context, "scene", None)
    settings = getattr(scene, "dow2_ragdoll_settings", None) if scene is not None else None
    return bool(settings and settings.preview_constraints)


def _constraint_preview_plane_flags() -> tuple[bool, bool]:
    scene = getattr(bpy.context, "scene", None)
    settings = getattr(scene, "dow2_ragdoll_settings", None) if scene is not None else None
    if settings is None:
        return True, True
    return bool(getattr(settings, "preview_plane_min", True)), bool(getattr(settings, "preview_plane_max", True))


def _remove_legacy_constraint_preview_objects() -> None:
    objects = getattr(bpy.data, "objects", None)
    collections = getattr(bpy.data, "collections", None)
    if objects is None or collections is None:
        return

    legacy_prefixes = ("rdc::", "ragdoll_constraint_preview::")
    for obj in list(objects):
        if obj.name.startswith(legacy_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)

    legacy_collection = collections.get("ragdoll_constraint_previews")
    if legacy_collection is not None:
        remove_collection_tree(legacy_collection)


def clear_constraint_preview_objects() -> None:
    global _CONSTRAINT_PREVIEW_ARROW_SEGMENTS
    global _CONSTRAINT_PREVIEW_CONE_SEGMENTS
    global _CONSTRAINT_PREVIEW_PLANE_SEGMENTS
    global _CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS
    global _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE
    global _CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES
    global _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME
    global _CONSTRAINT_PREVIEW_WAS_ENABLED

    _CONSTRAINT_PREVIEW_ARROW_SEGMENTS = []
    _CONSTRAINT_PREVIEW_CONE_SEGMENTS = []
    _CONSTRAINT_PREVIEW_PLANE_SEGMENTS = []
    _CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS = []
    _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE = ()
    _CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES = ()
    _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME = 0.0
    _CONSTRAINT_PREVIEW_WAS_ENABLED = False
    _remove_legacy_constraint_preview_objects()
    _tag_constraint_preview_redraw()


def _body_anchor_world_points(body_object: bpy.types.Object) -> list[Vector]:
    shape = str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE") or "CAPSULE").upper()
    if shape == "CAPSULE":
        vertex_a = _vector_prop(body_object, RAGDOLL_BODY_VERTEX_A_PROP, [0.0, -0.2, 0.0])
        vertex_b = _vector_prop(body_object, RAGDOLL_BODY_VERTEX_B_PROP, [0.0, 0.2, 0.0])
        return [
            body_object.matrix_world @ Vector(vertex_a),
            body_object.matrix_world @ Vector(vertex_b),
        ]
    return [body_object.matrix_world.translation.copy()]


def _body_anchor_toward(body_object: bpy.types.Object, target_position: Vector) -> Vector:
    anchor_points = _body_anchor_world_points(body_object)
    if not anchor_points:
        return body_object.matrix_world.translation.copy()
    return min(anchor_points, key=lambda anchor: (anchor - target_position).length_squared)


def _tag_constraint_preview_redraw() -> None:
    context = getattr(bpy, "context", None)
    window_manager = getattr(context, "window_manager", None) if context is not None else None
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = window.screen
        if screen is None:
            continue
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _selected_ragdoll_body_names() -> set[str]:
    context = getattr(bpy, "context", None)
    if context is None:
        return set()
    view_layer = getattr(context, "view_layer", None)
    if view_layer is None:
        return set()

    selected_body_names: set[str] = set()
    for scene_object in view_layer.objects:
        if not scene_object.select_get():
            continue
        body_object = resolve_ragdoll_body_object(scene_object)
        if body_object is not None:
            selected_body_names.add(body_object.name)
    return selected_body_names


def register_constraint_preview_draw_handler() -> None:
    global _CONSTRAINT_PREVIEW_DRAW_HANDLE
    global _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE

    if bpy.app.background:
        return
    if _CONSTRAINT_PREVIEW_DRAW_HANDLE is None:
        _CONSTRAINT_PREVIEW_DRAW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(
            _draw_constraint_preview_overlay,
            (),
            "WINDOW",
            "POST_VIEW",
        )
    if _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE is None:
        _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(
            _draw_constraint_preview_text_overlay,
            (),
            "WINDOW",
            "POST_PIXEL",
        )


def unregister_constraint_preview_draw_handler() -> None:
    global _CONSTRAINT_PREVIEW_DRAW_HANDLE
    global _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE

    if _CONSTRAINT_PREVIEW_DRAW_HANDLE is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_CONSTRAINT_PREVIEW_DRAW_HANDLE, "WINDOW")
        _CONSTRAINT_PREVIEW_DRAW_HANDLE = None
    if _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE, "WINDOW")
        _CONSTRAINT_PREVIEW_TEXT_DRAW_HANDLE = None


def _constraint_arrow_triangle(start: Vector, end: Vector, view_direction: Vector) -> tuple[Vector, Vector, Vector] | None:
    direction = end - start
    length = direction.length
    if length <= 1e-6:
        return None
    direction.normalize()
    side = direction.cross(view_direction)
    if side.length <= 1e-6:
        side = direction.orthogonal()
    if side.length <= 1e-6:
        return None
    side.normalize()
    arrow_length = min(0.06, length * 0.45)
    arrow_half_width = arrow_length * 0.45
    base = end - (direction * arrow_length)
    return end, base + (side * arrow_half_width), base - (side * arrow_half_width)


def _rounded_values(values: Vector | list[float] | tuple[float, ...], digits: int = 4) -> tuple[float, ...]:
    return tuple(round(float(component), digits) for component in values)


def _matrix_signature(matrix_value: Matrix) -> tuple[tuple[float, ...], ...]:
    return tuple(_rounded_values(row, digits=4) for row in matrix_value)


def _body_preview_signature(body_object: bpy.types.Object) -> tuple[object, ...]:
    location, rotation, scale = body_object.matrix_world.decompose()
    shape = str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE") or "CAPSULE").upper()
    return (
        body_object.name,
        shape,
        round(float(body_object.get("dow2_ragdoll_body_radius", 0.1)), 4),
        round(float(body_object.get("dow2_ragdoll_body_length", 0.4)), 4),
        round(float(body_object.get("dow2_ragdoll_body_height", 0.2)), 4),
        _rounded_values((location.x, location.y, location.z)),
        _rounded_values((rotation.x, rotation.y, rotation.z, rotation.w)),
        _rounded_values((scale.x, scale.y, scale.z)),
        _rounded_values(_vector_prop(body_object, RAGDOLL_BODY_VERTEX_A_PROP, [0.0, -0.2, 0.0])),
        _rounded_values(_vector_prop(body_object, RAGDOLL_BODY_VERTEX_B_PROP, [0.0, 0.2, 0.0])),
    )


def _constraint_settings_signature(settings: dict[str, object]) -> tuple[object, ...]:
    return (
        str(settings["constraint_type"]),
        round(float(settings["twist_min"]), 4),
        round(float(settings["twist_max"]), 4),
        round(float(settings["cone_angle"]), 4),
        round(float(settings["plane_min"]), 4),
        round(float(settings["plane_max"]), 4),
        round(float(settings["hinge_min"]), 4),
        round(float(settings["hinge_max"]), 4),
        _rounded_values(settings["pivot_a"]),
        _rounded_values(settings["pivot_b"]),
        _rounded_values(settings["twist_axis_a"]),
        _rounded_values(settings["twist_axis_b"]),
        _rounded_values(settings["plane_axis_a"]),
        _rounded_values(settings["plane_axis_b"]),
    )


def _body_preview_scale(body_object: bpy.types.Object) -> float:
    radius = max(float(body_object.get("dow2_ragdoll_body_radius", 0.1)), 0.001)
    length = max(float(body_object.get("dow2_ragdoll_body_length", radius * 2.0)), radius * 2.0)
    height = max(float(body_object.get("dow2_ragdoll_body_height", radius * 2.0)), radius * 2.0)
    return max(radius * 2.5, length * 0.35, height * 0.75, 0.08)


def _normalized(vector: Vector, fallback: Vector) -> Vector:
    if vector.length <= 1e-6:
        return fallback.copy()
    result = vector.copy()
    result.normalize()
    return result


def _transform_point(matrix_world: Matrix, local_point: Vector) -> Vector:
    return matrix_world @ local_point


def _transform_direction(matrix_world: Matrix, local_direction: Vector, fallback: Vector) -> Vector:
    world_direction = matrix_world.to_3x3() @ local_direction
    return _normalized(world_direction, fallback)


def _constraint_basis(twist_axis: Vector, plane_axis: Vector) -> tuple[Vector, Vector, Vector]:
    twist = _normalized(twist_axis, Vector((0.0, 0.0, 1.0)))
    plane = plane_axis - (twist * plane_axis.dot(twist))
    if plane.length <= 1e-6:
        plane = twist.orthogonal()
    plane.normalize()
    side = twist.cross(plane)
    if side.length <= 1e-6:
        side = twist.orthogonal()
    side.normalize()
    plane = side.cross(twist)
    plane.normalize()
    return twist, plane, side


def _append_polyline_segments(segments: list[tuple[Vector, Vector]], points: list[Vector], closed: bool = False) -> None:
    if len(points) < 2:
        return
    for index in range(len(points) - 1):
        segments.append((points[index].copy(), points[index + 1].copy()))
    if closed:
        segments.append((points[-1].copy(), points[0].copy()))


def _plane_cone_half_angle(limit_value: float) -> float:
    clamped_limit = min(max(abs(float(limit_value)), 0.0), math.pi * 0.5)
    return (math.pi * 0.5) - clamped_limit


def _direction_outside_plane_cones(
    direction: Vector,
    plane_axis: Vector,
    plane_min: float,
    plane_max: float,
) -> bool:
    normalized_direction = _normalized(direction, Vector((0.0, 0.0, 1.0)))
    normalized_plane = _normalized(plane_axis, Vector((1.0, 0.0, 0.0)))
    plane_dot = normalized_direction.dot(normalized_plane)
    max_half_angle = _plane_cone_half_angle(plane_max)
    min_half_angle = _plane_cone_half_angle(plane_min)
    max_cone_limit = math.cos(max_half_angle)
    min_cone_limit = math.cos(min_half_angle)
    inside_max_cone = plane_dot > (max_cone_limit + 1e-6)
    inside_min_cone = (-plane_dot) > (min_cone_limit + 1e-6)
    return not (inside_max_cone or inside_min_cone)


def _build_axis_cone_segments(
    pivot: Vector,
    axis: Vector,
    reference_axis: Vector,
    half_angle: float,
    length_scale: float,
    band_factors: tuple[float, ...] = (0.25, 0.5, 0.75, 1.0),
    sample_count: int = 48,
) -> list[tuple[Vector, Vector]]:
    segments: list[tuple[Vector, Vector]] = []
    clamped_half_angle = max(0.0, min(float(half_angle), math.pi * 0.5))
    if clamped_half_angle <= 1e-5:
        tip = pivot + (_normalized(axis, Vector((0.0, 0.0, 1.0))) * max(length_scale, 0.05))
        segments.append((pivot.copy(), tip))
        return segments

    cone_axis = _normalized(axis, Vector((0.0, 0.0, 1.0)))
    basis_x = reference_axis - (cone_axis * reference_axis.dot(cone_axis))
    if basis_x.length <= 1e-6:
        basis_x = cone_axis.orthogonal()
    basis_x.normalize()
    basis_y = cone_axis.cross(basis_x)
    basis_y = _normalized(basis_y, cone_axis.orthogonal())
    max_length = max(length_scale, 0.05)
    ring_bands: list[list[Vector]] = []

    for band_factor in band_factors:
        band_points: list[Vector] = []
        for step in range(sample_count):
            azimuth = (step / sample_count) * math.tau
            radial = (basis_x * math.cos(azimuth)) + (basis_y * math.sin(azimuth))
            direction = (cone_axis * math.cos(clamped_half_angle)) + (radial * math.sin(clamped_half_angle))
            direction = _normalized(direction, cone_axis)
            band_points.append(pivot + (direction * (max_length * band_factor)))
        ring_bands.append(band_points)
        _append_polyline_segments(segments, band_points, closed=True)

    meridian_indices = {0, sample_count // 4, sample_count // 2, (sample_count * 3) // 4}
    for meridian_index in sorted(meridian_indices):
        meridian_points = [pivot.copy()]
        for band_points in ring_bands:
            meridian_points.append(band_points[meridian_index].copy())
        _append_polyline_segments(segments, meridian_points)

    return segments


def _contiguous_allowed_runs(points: list[Vector | None]) -> list[list[Vector]]:
    if not points:
        return []

    sample_count = len(points)
    first_blocked_index = next((index for index, point in enumerate(points) if point is None), None)
    if first_blocked_index is None:
        return [[point.copy() for point in points if point is not None]]

    rotated = points[first_blocked_index + 1:] + points[:first_blocked_index + 1]
    runs: list[list[Vector]] = []
    current_run: list[Vector] = []
    for point in rotated:
        if point is None:
            if len(current_run) >= 2:
                runs.append(current_run)
            current_run = []
            continue
        current_run.append(point.copy())

    if len(current_run) >= 2:
        runs.append(current_run)

    return runs


def _build_hinge_angular_segments(
    pivot: Vector,
    twist_axis: Vector,
    plane_axis: Vector,
    angle_min: float,
    angle_max: float,
    outer_radius: float,
    inner_radius: float,
) -> list[tuple[Vector, Vector]]:
    segments: list[tuple[Vector, Vector]] = []
    clamped_outer = max(float(outer_radius), 0.01)
    clamped_inner = max(min(float(inner_radius), clamped_outer * 0.92), clamped_outer * 0.6)
    sweep = abs(angle_max - angle_min)
    sample_count = max(12, int(max(sweep, math.radians(10.0)) / math.radians(8.0)))
    _twist, plane, side = _constraint_basis(twist_axis, plane_axis)

    outer_points: list[Vector] = []
    inner_points: list[Vector] = []
    for step in range(sample_count + 1):
        factor = step / sample_count
        angle = angle_min + ((angle_max - angle_min) * factor)
        direction = (plane * math.cos(angle)) + (side * math.sin(angle))
        direction = _normalized(direction, plane)
        outer_points.append(pivot + (direction * clamped_outer))
        inner_points.append(pivot + (direction * clamped_inner))

    _append_polyline_segments(segments, outer_points)
    _append_polyline_segments(segments, inner_points)
    segments.append((outer_points[0].copy(), inner_points[0].copy()))
    segments.append((outer_points[-1].copy(), inner_points[-1].copy()))
    return segments


def _build_ragdoll_twist_segments(
    pivot: Vector,
    twist_axis: Vector,
    plane_axis: Vector,
    angle_min: float,
    angle_max: float,
    outer_radius: float,
    inner_radius: float,
) -> list[tuple[Vector, Vector]]:
    segments: list[tuple[Vector, Vector]] = []
    clamped_outer = max(float(outer_radius), 0.01)
    clamped_inner = max(min(float(inner_radius), clamped_outer * 0.92), clamped_outer * 0.6)
    sweep = abs(angle_max - angle_min)
    sample_count = max(12, int(max(sweep, math.radians(10.0)) / math.radians(8.0)))
    _twist, plane, side = _constraint_basis(twist_axis, plane_axis)

    outer_points: list[Vector] = []
    inner_points: list[Vector] = []
    for step in range(sample_count + 1):
        factor = step / sample_count
        angle = angle_min + ((angle_max - angle_min) * factor)
        direction = (side * math.cos(angle)) - (plane * math.sin(angle))
        direction = _normalized(direction, side)
        outer_points.append(pivot + (direction * clamped_outer))
        inner_points.append(pivot + (direction * clamped_inner))

    _append_polyline_segments(segments, outer_points)
    _append_polyline_segments(segments, inner_points)
    segments.append((outer_points[0].copy(), inner_points[0].copy()))
    segments.append((outer_points[-1].copy(), inner_points[-1].copy()))
    return segments


def _build_ragdoll_cone_plane_segments(
    pivot: Vector,
    twist_axis: Vector,
    plane_axis: Vector,
    cone_angle: float,
    plane_min: float,
    plane_max: float,
    length_scale: float,
    show_plane_min: bool,
    show_plane_max: bool,
) -> tuple[list[tuple[Vector, Vector]], list[tuple[Vector, Vector]]]:
    cone_segments: list[tuple[Vector, Vector]] = []
    plane_segments: list[tuple[Vector, Vector]] = []
    clamped_cone = max(0.0, min(float(cone_angle), math.pi))
    sample_count = 72
    band_factors = (0.25, 0.5, 0.75, 1.0)
    twist, plane, side = _constraint_basis(twist_axis, plane_axis)
    cone_axis = twist

    max_length = max(length_scale, 0.05)
    allowed_direction_points: list[Vector | None] = []
    for step in range(sample_count):
        factor = step / sample_count
        angle = factor * math.tau
        rim_direction = (plane * math.cos(angle)) + (side * math.sin(angle))
        direction = (cone_axis * math.cos(clamped_cone)) + (_normalized(rim_direction, plane) * math.sin(clamped_cone))
        direction = _normalized(direction, cone_axis)
        if _direction_outside_plane_cones(direction, plane_axis, plane_min, plane_max):
            allowed_direction_points.append(direction)
        else:
            allowed_direction_points.append(None)

    direction_runs = _contiguous_allowed_runs(allowed_direction_points)
    if not direction_runs:
        direction_runs = []

    for direction_run in direction_runs:
        band_runs: list[list[Vector]] = []
        for band_factor in band_factors:
            band_points: list[Vector] = []
            for direction in direction_run:
                band_points.append(pivot + (direction * (max_length * band_factor)))
            band_runs.append(band_points)
            _append_polyline_segments(cone_segments, band_points)

        meridian_count = min(7, len(direction_run))
        last_index = len(direction_run) - 1
        meridian_indices = {
            round((last_index * meridian_index) / max(meridian_count - 1, 1))
            for meridian_index in range(meridian_count)
        }
        for meridian_index in sorted(meridian_indices):
            meridian_points = [pivot.copy()]
            for band_points in band_runs:
                meridian_points.append(band_points[meridian_index].copy())
            _append_polyline_segments(cone_segments, meridian_points)

    plane_max_half_angle = _plane_cone_half_angle(plane_max)
    plane_min_half_angle = _plane_cone_half_angle(plane_min)
    if show_plane_max:
        plane_segments.extend(
            _build_axis_cone_segments(
                pivot,
                plane_axis,
                twist_axis,
                plane_max_half_angle,
                max_length * 0.95,
            )
        )
    if show_plane_min:
        plane_segments.extend(
            _build_axis_cone_segments(
                pivot,
                -plane_axis,
                twist_axis,
                plane_min_half_angle,
                max_length * 0.95,
            )
        )

    return cone_segments, plane_segments


def _choose_constraint_frame(record: dict[str, object]) -> tuple[Vector, Vector, Vector]:
    settings = record["settings"]
    joint_matrix = record["joint_matrix"]
    joint_head = record["joint_head"]

    twist_axis_a = Vector(_dx_vector_to_blender_local(settings["twist_axis_a"]))
    twist_axis_b = Vector(_dx_vector_to_blender_local(settings["twist_axis_b"]))
    plane_axis_a = Vector(_dx_vector_to_blender_local(settings["plane_axis_a"]))
    plane_axis_b = Vector(_dx_vector_to_blender_local(settings["plane_axis_b"]))

    candidates = []
    for current_twist, current_plane in (
        (twist_axis_a, plane_axis_a),
        (twist_axis_b, plane_axis_b),
    ):
        candidates.append(
            (
                joint_head.copy(),
                _transform_direction(joint_matrix, current_twist, Vector((0.0, 0.0, 1.0))),
                _transform_direction(joint_matrix, current_plane, Vector((1.0, 0.0, 0.0))),
            )
        )

    pivot, twist_axis, plane_axis = candidates[1] if len(candidates) > 1 else candidates[0]
    return pivot, twist_axis, plane_axis


def _adapt_ragdoll_presentation_frame(
    pivot: Vector,
    twist_axis: Vector,
    plane_axis: Vector,
    joint_head: Vector,
    joint_tail: Vector,
    display_matrix: Matrix,
) -> tuple[Vector, Vector, Vector]:
    tail_direction = joint_tail - joint_head
    loaded_twist, loaded_plane, _loaded_side = _constraint_basis(twist_axis, plane_axis)
    presentation_twist = _normalized(tail_direction, loaded_twist)

    twist_alignment = loaded_twist.rotation_difference(presentation_twist)
    presentation_plane = twist_alignment @ loaded_plane
    presentation_plane = presentation_plane - (presentation_twist * presentation_plane.dot(presentation_twist))
    if presentation_plane.length <= 1e-6:
        presentation_plane = presentation_twist.orthogonal()
    presentation_plane.normalize()

    display_basis = display_matrix.to_3x3()
    display_side = display_basis @ Vector((0.0, 0.0, 1.0))
    display_side = display_side - (presentation_twist * display_side.dot(presentation_twist))
    if display_side.length > 1e-6:
        display_side.normalize()
        presentation_side = presentation_twist.cross(presentation_plane)
        presentation_side = _normalized(presentation_side, display_side)
        signed_roll = math.atan2(
            presentation_twist.dot(presentation_side.cross(display_side)),
            presentation_side.dot(display_side),
        )
        presentation_plane = (Matrix.Rotation(signed_roll, 4, presentation_twist).to_3x3() @ presentation_plane)
        presentation_plane = _normalized(presentation_plane, presentation_twist.orthogonal())

    return pivot, presentation_twist, presentation_plane


def _build_constraint_preview_segments(
    record: dict[str, object]
) -> tuple[list[tuple[Vector, Vector]], list[tuple[Vector, Vector]], list[tuple[Vector, Vector]]]:
    settings = record["settings"]
    pivot, twist_axis, plane_axis = _choose_constraint_frame(record)
    preview_scale = float(record["preview_scale"])
    show_plane_min = bool(record["show_plane_min"])
    show_plane_max = bool(record["show_plane_max"])
    cone_segments: list[tuple[Vector, Vector]] = []
    plane_segments: list[tuple[Vector, Vector]] = []
    angular_segments: list[tuple[Vector, Vector]] = []
    constraint_type = str(settings["constraint_type"])

    if constraint_type == "limited_hinge":
        angular_segments.extend(
            _build_hinge_angular_segments(
                pivot,
                twist_axis,
                plane_axis,
                float(settings["hinge_min"]),
                float(settings["hinge_max"]),
                preview_scale * 0.9,
                preview_scale * 0.65,
            )
        )
        return cone_segments, plane_segments, angular_segments

    record_cone_segments, record_plane_segments = (
        _build_ragdoll_cone_plane_segments(
            pivot,
            twist_axis,
            plane_axis,
            float(settings["cone_angle"]),
            float(settings["plane_min"]),
            float(settings["plane_max"]),
            preview_scale,
            show_plane_min,
            show_plane_max,
        )
    )
    cone_segments.extend(record_cone_segments)
    plane_segments.extend(record_plane_segments)
    angular_segments.extend(
        _build_ragdoll_twist_segments(
            pivot,
            twist_axis,
            plane_axis,
            float(settings["twist_min"]),
            float(settings["twist_max"]),
            preview_scale * 0.72,
            preview_scale * 0.52,
        )
    )
    return cone_segments, plane_segments, angular_segments


def _positions_from_segments(segments: list[tuple[Vector, Vector]]) -> list[tuple[float, float, float]]:
    return [tuple(point) for segment in segments for point in segment]


def _draw_constraint_preview_overlay() -> None:
    preview_enabled = _constraint_preview_enabled()
    body_object = _constraint_preview_overlay_body()
    if not preview_enabled and body_object is None:
        return

    region_data = getattr(bpy.context, "region_data", None)
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    arrow_line_positions = _positions_from_segments(_CONSTRAINT_PREVIEW_ARROW_SEGMENTS)
    cone_positions = _positions_from_segments(_CONSTRAINT_PREVIEW_CONE_SEGMENTS)
    plane_positions = _positions_from_segments(_CONSTRAINT_PREVIEW_PLANE_SEGMENTS)
    angular_positions = _positions_from_segments(_CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS)
    if preview_enabled and (arrow_line_positions or cone_positions or plane_positions or angular_positions):
        arrow_triangle_positions: list[tuple[float, float, float]] = []
        if region_data is not None:
            view_direction = region_data.view_rotation @ Vector((0.0, 0.0, -1.0))
            for start, end in _CONSTRAINT_PREVIEW_ARROW_SEGMENTS:
                arrow = _constraint_arrow_triangle(start, end, view_direction)
                if arrow is None:
                    continue
                arrow_triangle_positions.extend(tuple(point) for point in arrow)

        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("NONE")
        gpu.state.line_width_set(3.0)

        shader.bind()
        if arrow_line_positions:
            shader.uniform_float("color", (1.0, 0.15, 0.1, 0.95))
            batch_for_shader(shader, "LINES", {"pos": arrow_line_positions}).draw(shader)
        if arrow_triangle_positions:
            shader.uniform_float("color", (1.0, 0.15, 0.1, 0.95))
            batch_for_shader(shader, "TRIS", {"pos": arrow_triangle_positions}).draw(shader)

        if cone_positions:
            shader.uniform_float("color", (0.22, 0.82, 1.0, 0.88))
            batch_for_shader(shader, "LINES", {"pos": cone_positions}).draw(shader)

        if plane_positions:
            shader.uniform_float("color", (0.2, 0.45, 1.0, 0.9))
            batch_for_shader(shader, "LINES", {"pos": plane_positions}).draw(shader)

        if angular_positions:
            shader.uniform_float("color", (1.0, 0.78, 0.24, 0.92))
            batch_for_shader(shader, "LINES", {"pos": angular_positions}).draw(shader)

        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set("LESS_EQUAL")
        gpu.state.blend_set("NONE")

def _constraint_preview_overlay_body() -> bpy.types.Object | None:
    context = getattr(bpy, "context", None)
    if context is None:
        return None

    active_body = resolve_ragdoll_body_object(getattr(context, "active_object", None))
    selected_body_names = _selected_ragdoll_body_names()
    if active_body is not None and active_body.name in selected_body_names:
        return active_body

    for body_name in selected_body_names:
        body_object = bpy.data.objects.get(body_name)
        if body_object is not None:
            return body_object
    return None


def _draw_constraint_preview_text_line(
    font_id: int,
    x: float,
    y: float,
    text: str,
    color: tuple[float, float, float, float],
) -> None:
    blf.position(font_id, x, y, 0.0)
    blf.color(font_id, *color)
    blf.draw(font_id, text)


def _draw_constraint_preview_text_overlay() -> None:
    body_object = _constraint_preview_overlay_body()

    context = getattr(bpy, "context", None)
    region = getattr(context, "region", None) if context is not None else None
    preview_enabled = _constraint_preview_enabled()
    if body_object is None:
        return
    if region is None:
        return

    body_shape = str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE") or "CAPSULE").upper()
    font_id = 0
    line_height = 18.0
    x = 104.0
    y = region.height - 148.0
    text_color = (0.96, 0.98, 1.0, 1.0)
    muted_color = (0.78, 0.84, 0.9, 1.0)
    arrow_color = (1.0, 0.15, 0.1, 0.95)
    cone_color = (0.22, 0.82, 1.0, 0.95)
    plane_color = (0.2, 0.45, 1.0, 0.95)
    angular_color = (1.0, 0.78, 0.24, 0.95)

    blf.size(font_id, 12.0)

    lines: list[tuple[str, tuple[float, float, float, float]]] = [
        (f"Ragdoll body: {body_object.name}", text_color),
    ]
    if body_shape == "CAPSULE":
        lines.append(("Capsule shortcuts: Ctrl+Alt+Wheel or Ctrl+Up/Down = length", muted_color))
        lines.append(("Capsule shortcuts: Ctrl+Shift+Wheel or Ctrl+Left/Right = radius", muted_color))
    else:
        lines.append(("Capsule shortcuts apply only when the selected ragdoll body is a capsule", muted_color))

    lines.append(("", text_color))

    if not preview_enabled:
        lines.append(("Constraint previews are currently hidden", muted_color))

    lines.append(("Preview colors:", text_color))
    lines.append(("Red = parent/child body link", arrow_color))
    lines.append(("Aqua = cone angle limit", cone_color))
    lines.append(("Blue = plane min/max limits", plane_color))
    lines.append(("Yellow = twist or hinge angular limits", angular_color))

    visible_lines = [text for text, _color in lines if text]
    max_width = max((blf.dimensions(font_id, text)[0] for text in visible_lines), default=0.0)
    box_left = x - 14.0
    box_top = y + 12.0
    box_right = x + max_width + 14.0
    box_bottom = y - (line_height * max(len(lines) - 1, 0)) - 10.0

    bg_shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    bg_shader.bind()
    gpu.state.blend_set("ALPHA")
    bg_shader.uniform_float("color", (0.03, 0.05, 0.07, 0.74))
    batch_for_shader(
        bg_shader,
        "TRI_FAN",
        {
            "pos": [
                (box_left, box_top),
                (box_right, box_top),
                (box_right, box_bottom),
                (box_left, box_bottom),
            ]
        },
    ).draw(bg_shader)
    bg_shader.uniform_float("color", (0.62, 0.72, 0.82, 0.55))
    batch_for_shader(
        bg_shader,
        "LINE_LOOP",
        {
            "pos": [
                (box_left, box_top),
                (box_right, box_top),
                (box_right, box_bottom),
                (box_left, box_bottom),
            ]
        },
    ).draw(bg_shader)
    gpu.state.blend_set("NONE")

    current_y = y
    for text, color in lines:
        if text:
            _draw_constraint_preview_text_line(font_id, x, current_y, text, color)
        current_y -= line_height


def sync_constraint_preview_objects() -> int:
    global _CONSTRAINT_PREVIEW_ARROW_SEGMENTS
    global _CONSTRAINT_PREVIEW_CONE_SEGMENTS
    global _CONSTRAINT_PREVIEW_PLANE_SEGMENTS
    global _CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS
    global _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE
    global _CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES
    global _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME
    global _CONSTRAINT_PREVIEW_WAS_ENABLED

    register_constraint_preview_draw_handler()

    if not _constraint_preview_enabled():
        if _CONSTRAINT_PREVIEW_WAS_ENABLED:
            clear_constraint_preview_objects()
        return 0

    _CONSTRAINT_PREVIEW_WAS_ENABLED = True
    show_plane_min, show_plane_max = _constraint_preview_plane_flags()
    selected_body_names = _selected_ragdoll_body_names()
    selected_body_key = tuple(sorted(selected_body_names))
    selection_changed = selected_body_key != _CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES
    arrow_segments: list[tuple[Vector, Vector]] = []
    records: list[dict[str, object]] = []
    signature_items: list[object] = [
        ("plane_preview_flags", show_plane_min, show_plane_max),
    ]
    for skeleton_object in bpy.data.objects:
        if not is_ragdoll_skeleton_object(skeleton_object):
            continue
        body_by_name = _body_object_by_bone_name(skeleton_object)
        for bone in _ragdoll_bones_in_order(skeleton_object):
            if bone.parent is None:
                continue
            parent_body = body_by_name.get(bone.parent.name)
            child_body = body_by_name.get(bone.name)
            if parent_body is None or child_body is None:
                continue
            if child_body.name not in selected_body_names:
                continue

            start = _body_anchor_toward(parent_body, child_body.matrix_world.translation.copy())
            end = _body_anchor_toward(child_body, parent_body.matrix_world.translation.copy())
            if (end - start).length <= 1e-6:
                continue

            arrow_segments.append((start.copy(), end.copy()))
            settings = read_constraint_settings(bone)
            display_matrix = skeleton_object.matrix_world @ bone.matrix_local
            joint_matrix = remove_bone_axis_adapter(
                display_matrix,
                skeleton_object,
            )
            records.append(
                {
                    "bone_name": bone.name,
                    "settings": settings,
                    "display_matrix": display_matrix.copy(),
                    "joint_matrix": joint_matrix.copy(),
                    "joint_head": skeleton_object.matrix_world @ bone.head_local,
                    "joint_tail": skeleton_object.matrix_world @ bone.tail_local,
                    "preview_scale": max(_body_preview_scale(parent_body), _body_preview_scale(child_body)),
                    "show_plane_min": show_plane_min,
                    "show_plane_max": show_plane_max,
                }
            )
            signature_items.append(
                (
                    skeleton_object.name,
                    bone.name,
                    _matrix_signature(joint_matrix),
                    _body_preview_signature(parent_body),
                    _body_preview_signature(child_body),
                    _constraint_settings_signature(settings),
                )
            )

    signature = tuple(signature_items)
    now = time.monotonic()
    if selection_changed:
        _CONSTRAINT_PREVIEW_LAST_SELECTED_BODIES = selected_body_key
        _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE = signature
        _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME = now
    elif signature != _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE:
        _CONSTRAINT_PREVIEW_LAST_SEEN_SIGNATURE = signature
        _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME = now

    if not records:
        _CONSTRAINT_PREVIEW_ARROW_SEGMENTS = arrow_segments
        _CONSTRAINT_PREVIEW_CONE_SEGMENTS = []
        _CONSTRAINT_PREVIEW_PLANE_SEGMENTS = []
        _CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS = []
        _tag_constraint_preview_redraw()
        return 0

    stable_for = now - _CONSTRAINT_PREVIEW_LAST_CHANGE_TIME
    if not selection_changed and stable_for < _CONSTRAINT_PREVIEW_DEBOUNCE_SECONDS:
        _CONSTRAINT_PREVIEW_ARROW_SEGMENTS = arrow_segments
        _tag_constraint_preview_redraw()
        return len(records)

    cone_segments: list[tuple[Vector, Vector]] = []
    plane_segments: list[tuple[Vector, Vector]] = []
    angular_segments: list[tuple[Vector, Vector]] = []
    for record in records:
        record_cone_segments, record_plane_segments, record_angular_segments = _build_constraint_preview_segments(record)
        cone_segments.extend(record_cone_segments)
        plane_segments.extend(record_plane_segments)
        angular_segments.extend(record_angular_segments)

    _CONSTRAINT_PREVIEW_CONE_SEGMENTS = cone_segments
    _CONSTRAINT_PREVIEW_PLANE_SEGMENTS = plane_segments
    _CONSTRAINT_PREVIEW_ANGULAR_SEGMENTS = angular_segments

    _CONSTRAINT_PREVIEW_ARROW_SEGMENTS = arrow_segments
    _tag_constraint_preview_redraw()
    return len(records)


def remove_legacy_constraint_preview_objects() -> None:
    _remove_legacy_constraint_preview_objects()