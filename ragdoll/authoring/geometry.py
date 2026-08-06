from __future__ import annotations

import math
from typing import Sequence

import bpy
import bmesh
from mathutils import Matrix, Quaternion, Vector

from ...utils import blender_to_dx_matrix, blender_to_dx_position


def _capsule_segment_vertices(full_length: float, radius: float) -> tuple[list[float], list[float]]:
    usable_length = max(full_length, 0.001)
    inset = min(max(radius * 1.05, 0.001), usable_length * 0.45)
    half_length = usable_length * 0.5
    line_start = -half_length + inset
    line_end = half_length - inset
    if line_end <= line_start:
        half_line = min(max(usable_length * 0.05, 0.0025), usable_length * 0.5)
        line_start = -half_line
        line_end = half_line
    return [0.0, line_start, 0.0], [0.0, line_end, 0.0]


def _generated_capsule_radius(bone_name: str, segment_length: float, is_leaf: bool, radius_scale_for_ragdoll_bone) -> float:
    base_radius = segment_length * radius_scale_for_ragdoll_bone(bone_name)
    max_radius = 0.05 if is_leaf else 0.12
    min_radius = 0.015 if is_leaf else 0.02
    return max(min_radius, min(max_radius, base_radius))


def _body_world_matrix(head: Vector, tail: Vector) -> tuple[Matrix, float]:
    direction = tail - head
    length = max(direction.length, 0.05)
    if direction.length < 0.001:
        direction = Vector((0.0, length, 0.0))
    rotation = direction.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()
    matrix = rotation
    matrix.translation = head.lerp(tail, 0.5)
    return matrix, length


def _body_world_matrix_from_origin(origin: Vector, target: Vector) -> tuple[Matrix, float]:
    direction = target - origin
    length = max(direction.length, 0.05)
    if direction.length < 0.001:
        direction = Vector((0.0, length, 0.0))
    rotation = direction.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()
    matrix = rotation
    matrix.translation = origin
    return matrix, length


def _body_dx_matrix_from_segment(origin: Vector, target: Vector) -> tuple[Matrix, float]:
    dx_origin = Vector(blender_to_dx_position(origin))
    dx_target = Vector(blender_to_dx_position(target))
    dx_direction = dx_target - dx_origin
    length = max(dx_direction.length, 0.05)
    if dx_direction.length < 0.001:
        dx_direction = Vector((0.0, length, 0.0))
    rotation = dx_direction.normalized().to_track_quat("Y", "Z").to_matrix().to_4x4()
    matrix = Matrix.Translation(dx_origin) @ rotation
    return matrix, length


def _blender_vector_to_dx_local(vector: Sequence[float]) -> list[float]:
    source = Vector(vector[:3])
    return [-source.x, source.z, -source.y]


def _dx_vector_to_blender_local(vector: Sequence[float]) -> list[float]:
    source = Vector(vector[:3])
    return [-source.x, -source.z, source.y]


def _authored_body_dx_transform(
    body_object: bpy.types.Object,
    shape_type: str,
    vertex_a: Sequence[float],
    vertex_b: Sequence[float],
) -> tuple[Vector, Quaternion]:
    del shape_type
    del vertex_a
    del vertex_b
    matrix_dx = blender_to_dx_matrix(body_object.matrix_world)
    position_vec, rotation_quat, _scale = matrix_dx.decompose()
    return position_vec, rotation_quat


def _build_cylinder_mesh(mesh: bpy.types.Mesh, radius: float, length: float, segments: int = 12) -> None:
    half_length = max(length * 0.5, 0.001)
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for ring_y in (-half_length, half_length):
        for index in range(segments):
            angle = (index / segments) * (math.pi * 2.0)
            verts.append((math.cos(angle) * radius, ring_y, math.sin(angle) * radius))
    bottom_center = len(verts)
    verts.append((0.0, -half_length, 0.0))
    top_center = len(verts)
    verts.append((0.0, half_length, 0.0))

    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((index, next_index, segments + next_index, segments + index))
        faces.append((bottom_center, next_index, index))
        faces.append((top_center, segments + index, segments + next_index))

    mesh.clear_geometry()
    mesh.from_pydata(verts, [], faces)
    mesh.update()


def _build_capsule_preview_mesh(
    mesh: bpy.types.Mesh,
    radius: float,
    vertex_a: Sequence[float],
    vertex_b: Sequence[float],
    segments: int = 16,
    cap_rings: int = 4,
) -> None:
    start = Vector(vertex_a[:3])
    end = Vector(vertex_b[:3])
    axis = end - start
    if axis.length < 0.001:
        axis = Vector((0.0, 1.0, 0.0))
        end = start + axis * 0.001
    axis.normalize()

    reference = Vector((0.0, 0.0, 1.0)) if abs(axis.z) < 0.999 else Vector((1.0, 0.0, 0.0))
    side = axis.cross(reference)
    if side.length < 0.001:
        reference = Vector((0.0, 1.0, 0.0))
        side = axis.cross(reference)
    side.normalize()
    up = side.cross(axis)
    up.normalize()

    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    rings: list[list[int]] = []
    actual_radius = max(radius, 0.001)

    start_pole = start - axis * actual_radius
    start_pole_index = len(verts)
    verts.append((start_pole.x, start_pole.y, start_pole.z))

    def _append_ring(ring_center: Vector, ring_radius: float) -> None:
        ring_indices: list[int] = []
        for index in range(segments):
            angle = (index / segments) * (math.pi * 2.0)
            offset = (side * math.cos(angle) + up * math.sin(angle)) * ring_radius
            point = ring_center + offset
            ring_indices.append(len(verts))
            verts.append((point.x, point.y, point.z))
        rings.append(ring_indices)

    for step in range(1, cap_rings + 1):
        theta = (step / cap_rings) * (math.pi * 0.5)
        ring_center = start - axis * (math.cos(theta) * actual_radius)
        ring_radius = math.sin(theta) * actual_radius
        _append_ring(ring_center, ring_radius)

    for step in range(cap_rings, 0, -1):
        theta = (step / cap_rings) * (math.pi * 0.5)
        ring_center = end + axis * (math.cos(theta) * actual_radius)
        ring_radius = math.sin(theta) * actual_radius
        _append_ring(ring_center, ring_radius)

    end_pole = end + axis * actual_radius
    end_pole_index = len(verts)
    verts.append((end_pole.x, end_pole.y, end_pole.z))

    first_ring = rings[0]
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((start_pole_index, first_ring[next_index], first_ring[index]))

    for ring_index in range(len(rings) - 1):
        current_ring = rings[ring_index]
        next_ring = rings[ring_index + 1]
        for index in range(segments):
            next_index = (index + 1) % segments
            faces.append((current_ring[index], current_ring[next_index], next_ring[next_index], next_ring[index]))

    last_ring = rings[-1]
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((end_pole_index, last_ring[index], last_ring[next_index]))

    mesh.clear_geometry()
    mesh.from_pydata(verts, [], faces)
    mesh.update()


def _body_local_origin_offset(shape_type: str, vertex_a: Sequence[float], vertex_b: Sequence[float]) -> Vector:
    del shape_type
    del vertex_a
    del vertex_b
    return Vector((0.0, 0.0, 0.0))


def _build_box_mesh(mesh: bpy.types.Mesh, radius: float, height: float, length: float) -> None:
    half_width = max(radius, 0.001)
    half_length = max(length * 0.5, 0.001)
    half_height = max(height * 0.5, 0.001)
    verts = [
        (-half_width, -half_length, -half_height),
        (half_width, -half_length, -half_height),
        (half_width, half_length, -half_height),
        (-half_width, half_length, -half_height),
        (-half_width, -half_length, half_height),
        (half_width, -half_length, half_height),
        (half_width, half_length, half_height),
        (-half_width, half_length, half_height),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 5, 6, 7),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]
    mesh.clear_geometry()
    mesh.from_pydata(verts, [], faces)
    mesh.update()


def _build_sphere_mesh(mesh: bpy.types.Mesh, radius: float) -> None:
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=max(radius, 0.001))
    mesh.clear_geometry()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()