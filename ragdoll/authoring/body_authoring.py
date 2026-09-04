from __future__ import annotations

from typing import Iterable, Sequence

import bpy
from mathutils import Matrix, Quaternion, Vector

from ...utils import dx_to_blender_matrix, link_object_to_collection
from ..bodies import radius_scale_for_ragdoll_bone
from .collections import ensure_ragdoll_bodies_collection
from .constants import (
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
    RAGDOLL_BODY_BONE_PROP,
    RAGDOLL_BODY_COLLISION_FILTER_PROP,
    RAGDOLL_BODY_FRICTION_PROP,
    RAGDOLL_BODY_HALF_EXTENTS_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_JOINT_ORIGIN_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_LINEAR_DAMPING_PROP,
    RAGDOLL_BODY_MASS_PROP,
    RAGDOLL_MIN_BODY_DIMENSION,
    RAGDOLL_BODY_MOTION_TYPE_PROP,
    RAGDOLL_BODY_PROP,
    RAGDOLL_BODY_QUALITY_TYPE_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_RESTITUTION_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_BODY_SHAPE_OFFSET_PROP,
    RAGDOLL_BODY_VERTEX_A_PROP,
    RAGDOLL_BODY_VERTEX_B_PROP,
    RAGDOLL_SOURCE_ARMATURE_PROP,
)
from .geometry import (
    _body_local_origin_offset,
    _body_world_matrix_from_export_bone_frame,
    _body_world_matrix_from_origin,
    _build_box_mesh,
    _build_capsule_preview_mesh,
    _build_cylinder_mesh,
    _build_sphere_mesh,
    _capsule_segment_vertices,
    _capsule_segment_vertices_from_origin,
    _dx_vector_to_blender_local,
    _generated_capsule_radius,
)
from .body_offset_helpers import has_shape_offset, shape_offset_vector
from .body_shape_helpers import box_half_extents, normalize_body_shape, resolved_creation_dimensions, sphere_half_extents
from .props import _normalized_vector_values
from .queries import active_ragdoll_bone
from .skeleton_authoring import _generated_capsule_segment, _immediate_child_on_path


def _capsule_handles_from_body(body_object: bpy.types.Object, radius: float, vertex_a: Sequence[float], vertex_b: Sequence[float]) -> None:
    from .body_sync import _sync_capsule_handles

    _sync_capsule_handles(body_object, radius, vertex_a, vertex_b)


def _reframe_local_point(point: Sequence[float], source_matrix: Matrix, target_matrix: Matrix) -> list[float]:
    world_point = source_matrix @ Vector(point[:3])
    local_point = target_matrix.inverted() @ world_point
    return [float(local_point.x), float(local_point.y), float(local_point.z)]


def update_body_mesh(
    body_object: bpy.types.Object,
    shape: str,
    radius: float,
    height: float,
    length: float,
    vertex_a: Sequence[float] | None = None,
    vertex_b: Sequence[float] | None = None,
    half_extents: Sequence[float] | None = None,
    shape_offset: Sequence[float] | None = None,
) -> None:
    mesh = body_object.data
    offset = shape_offset_vector(shape_offset)
    if shape == "BOX":
        if half_extents is not None and len(half_extents) >= 3:
            # half_extents are in DX/Havok local axes [hx, hy, hz]. The body's
            # rotation is converted DX->Blender with DX-Y -> Blender-Z and
            # DX-Z -> Blender-Y (see _dx_vector_to_blender_local = [-x,-z,y]),
            # so the box extents must follow the same swap: Blender Y gets hz,
            # Blender Z gets hy. Without this, anisotropic boxes (e.g. the flat
            # zoanthrope fins) display rotated 90deg; near-cubes hide it.
            _build_box_mesh(mesh, float(half_extents[0]), float(half_extents[1]) * 2.0, float(half_extents[2]) * 2.0)
        else:
            _build_box_mesh(mesh, radius, height, length)
    elif shape == "SPHERE":
        _build_sphere_mesh(mesh, radius)
    else:
        if vertex_a is not None and vertex_b is not None:
            _build_capsule_preview_mesh(mesh, radius, vertex_a, vertex_b)
        else:
            _build_cylinder_mesh(mesh, radius, length)
    if has_shape_offset(offset):
        mesh.transform(Matrix.Translation(offset))
        mesh.update()
    body_object.display_type = "WIRE"
    body_object.show_in_front = True
    body_object.hide_render = True
    body_object[RAGDOLL_BODY_SHAPE_PROP] = shape
    body_object[RAGDOLL_BODY_RADIUS_PROP] = float(radius)
    body_object[RAGDOLL_BODY_HEIGHT_PROP] = float(height)
    body_object[RAGDOLL_BODY_LENGTH_PROP] = float(length)
    body_object[RAGDOLL_BODY_SHAPE_OFFSET_PROP] = list(offset)
    if RAGDOLL_BODY_MASS_PROP not in body_object:
        body_object[RAGDOLL_BODY_MASS_PROP] = 5.0
    if RAGDOLL_BODY_FRICTION_PROP not in body_object:
        body_object[RAGDOLL_BODY_FRICTION_PROP] = 1.0
    if RAGDOLL_BODY_RESTITUTION_PROP not in body_object:
        body_object[RAGDOLL_BODY_RESTITUTION_PROP] = 0.0
    if RAGDOLL_BODY_MOTION_TYPE_PROP not in body_object:
        body_object[RAGDOLL_BODY_MOTION_TYPE_PROP] = "MOTION_BOX_INERTIA"
    if RAGDOLL_BODY_LINEAR_DAMPING_PROP not in body_object:
        body_object[RAGDOLL_BODY_LINEAR_DAMPING_PROP] = 1.0
    if RAGDOLL_BODY_ANGULAR_DAMPING_PROP not in body_object:
        body_object[RAGDOLL_BODY_ANGULAR_DAMPING_PROP] = 3.0
    if RAGDOLL_BODY_COLLISION_FILTER_PROP not in body_object:
        body_object[RAGDOLL_BODY_COLLISION_FILTER_PROP] = 65984
    if RAGDOLL_BODY_QUALITY_TYPE_PROP not in body_object:
        body_object[RAGDOLL_BODY_QUALITY_TYPE_PROP] = 4
    if shape == "CAPSULE" and vertex_a is not None and vertex_b is not None:
        body_object.lock_scale = (True, True, True)
        _capsule_handles_from_body(body_object, radius, Vector(vertex_a) + offset, Vector(vertex_b) + offset)
    else:
        from .body_sync import _remove_capsule_handles

        body_object.lock_scale = (False, False, False)
        _remove_capsule_handles(body_object)


def apply_body_data_to_object(
    body_object: bpy.types.Object,
    body_data: dict[str, float | str | list[float]],
    apply_world_transform: bool = True,
) -> None:
    shape_type = str(body_data.get("shape_type", body_object.get(RAGDOLL_BODY_SHAPE_PROP, "capsule"))).upper()
    radius = float(body_data.get("radius", body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)))
    half_extents = _normalized_vector_values(body_data.get("half_extents"), [radius, 0.2, 0.1])
    if "shape_offset" in body_data:
        shape_offset = _dx_vector_to_blender_local(
            _normalized_vector_values(body_data.get("shape_offset"), [0.0, 0.0, 0.0])
        )
    else:
        shape_offset = _normalized_vector_values(
            body_object.get(RAGDOLL_BODY_SHAPE_OFFSET_PROP, [0.0, 0.0, 0.0]),
            [0.0, 0.0, 0.0],
        )
    vertex_a_dx = _normalized_vector_values(body_data.get("vertex_a"), [0.0, -0.2, 0.0])
    vertex_b_dx = _normalized_vector_values(body_data.get("vertex_b"), [0.0, 0.2, 0.0])
    vertex_a = _dx_vector_to_blender_local(vertex_a_dx)
    vertex_b = _dx_vector_to_blender_local(vertex_b_dx)
    height = max(float(half_extents[2] * 2.0), RAGDOLL_MIN_BODY_DIMENSION)
    length = max((Vector(vertex_b) - Vector(vertex_a)).length, float(half_extents[1] * 2.0), RAGDOLL_MIN_BODY_DIMENSION)
    if shape_type == "SPHERE":
        height = radius * 2.0
        length = radius * 2.0
    elif shape_type == "BOX":
        # A box has no radius in the source data (it is 0), but the sync path
        # reconstructs the box X half-extent from RADIUS_PROP. Seed it from the
        # X half-extent so a later force-sync does not collapse X to the minimum
        # clamp.
        radius = max(float(half_extents[0]), RAGDOLL_MIN_BODY_DIMENSION)

    update_body_mesh(
        body_object,
        shape_type,
        radius,
        height,
        length,
        vertex_a=vertex_a,
        vertex_b=vertex_b,
        half_extents=half_extents,
        shape_offset=shape_offset,
    )
    body_object[RAGDOLL_BODY_VERTEX_A_PROP] = vertex_a
    body_object[RAGDOLL_BODY_VERTEX_B_PROP] = vertex_b
    body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = list(body_data.get("half_extents", [radius, max(length * 0.5, RAGDOLL_MIN_BODY_DIMENSION), max(height * 0.5, RAGDOLL_MIN_BODY_DIMENSION)]))
    body_object[RAGDOLL_BODY_SHAPE_OFFSET_PROP] = list(shape_offset)
    body_object[RAGDOLL_BODY_MASS_PROP] = float(body_data.get("mass", body_object.get(RAGDOLL_BODY_MASS_PROP, 5.0)))
    body_object[RAGDOLL_BODY_FRICTION_PROP] = float(body_data.get("friction", body_object.get(RAGDOLL_BODY_FRICTION_PROP, 1.0)))
    body_object[RAGDOLL_BODY_RESTITUTION_PROP] = float(body_data.get("restitution", body_object.get(RAGDOLL_BODY_RESTITUTION_PROP, 0.0)))
    body_object[RAGDOLL_BODY_MOTION_TYPE_PROP] = str(body_data.get("motion_type", body_object.get(RAGDOLL_BODY_MOTION_TYPE_PROP, "MOTION_BOX_INERTIA")))
    body_object[RAGDOLL_BODY_LINEAR_DAMPING_PROP] = float(body_data.get("linear_damping", body_object.get(RAGDOLL_BODY_LINEAR_DAMPING_PROP, 1.0)))
    body_object[RAGDOLL_BODY_ANGULAR_DAMPING_PROP] = float(body_data.get("angular_damping", body_object.get(RAGDOLL_BODY_ANGULAR_DAMPING_PROP, 3.0)))
    body_object[RAGDOLL_BODY_COLLISION_FILTER_PROP] = int(body_data.get("collision_filter_info", body_object.get(RAGDOLL_BODY_COLLISION_FILTER_PROP, 65984)))
    body_object[RAGDOLL_BODY_QUALITY_TYPE_PROP] = int(body_data.get("quality_type", body_object.get(RAGDOLL_BODY_QUALITY_TYPE_PROP, 4)))

    position = body_data.get("position")
    rotation = body_data.get("rotation")
    if apply_world_transform and position is not None and rotation is not None:
        rotation_quaternion = Quaternion((rotation[3], rotation[0], rotation[1], rotation[2]))
        local_origin_offset = _body_local_origin_offset(shape_type, vertex_a, vertex_b)
        origin_position = Vector(position) - (rotation_quaternion.to_matrix() @ local_origin_offset)
        dx_matrix = Matrix.Translation(origin_position) @ rotation_quaternion.to_matrix().to_4x4()
        body_object.matrix_world = dx_to_blender_matrix(dx_matrix)
        # The origin now sits at the authoritative Havok joint with asymmetric
        # capsule vertices. Flag it so the live capsule sync never recenters it
        # onto the geometric midpoint (which would drift the body off its joint
        # and desync it from the constraint pivots on export).
        body_object[RAGDOLL_BODY_JOINT_ORIGIN_PROP] = True
    for prop_name in ("dow2_ragdoll_body_position", "dow2_ragdoll_body_rotation"):
        if prop_name in body_object:
            del body_object[prop_name]


def create_or_update_body_for_bone(
    skeleton_object: bpy.types.Object,
    bone_name: str,
    shape: str,
    radius: float,
    height: float,
    length: float,
    preferred_descendant_name: str | None = None,
) -> bpy.types.Object:
    shape = normalize_body_shape(shape)
    bodies_collection = ensure_ragdoll_bodies_collection(skeleton_object)
    body_name = f"ragdoll_body::{bone_name}"
    body_object = bpy.data.objects.get(body_name)
    had_existing_body = body_object is not None and body_object.type == "MESH"
    if body_object is None or body_object.type != "MESH":
        mesh = bpy.data.meshes.new(body_name)
        body_object = bpy.data.objects.new(body_name, mesh)
        link_object_to_collection(body_object, bodies_collection)
    else:
        link_object_to_collection(body_object, bodies_collection)

    head, tail, used_leaf_fallback = _generated_capsule_segment(skeleton_object, bone_name, preferred_descendant_name)
    bone_length = max((tail - head).length, 0.05)
    if shape == "CAPSULE":
        body_matrix = _body_world_matrix_from_export_bone_frame(skeleton_object, bone_name, head)
    else:
        body_matrix = _body_world_matrix_from_export_bone_frame(skeleton_object, bone_name, head.lerp(tail, 0.5))
    body_object.matrix_world = body_matrix
    body_object[RAGDOLL_BODY_PROP] = True
    body_object[RAGDOLL_BODY_BONE_PROP] = bone_name
    body_object[RAGDOLL_SOURCE_ARMATURE_PROP] = skeleton_object.name

    if shape == "CAPSULE":
        requested_radius, _requested_height, requested_length = resolved_creation_dimensions(shape, radius, height, length)
        capsule_radius = requested_radius if had_existing_body else _generated_capsule_radius(
            bone_name,
            bone_length,
            used_leaf_fallback,
            radius_scale_for_ragdoll_bone,
        )
        capsule_length = requested_length if had_existing_body else bone_length
        axis_matrix, _axis_length = _body_world_matrix_from_origin(head, tail)
        default_vertex_a, default_vertex_b = _capsule_segment_vertices_from_origin(capsule_length, capsule_radius)
        vertex_a = _reframe_local_point(default_vertex_a, axis_matrix, body_matrix)
        vertex_b = _reframe_local_point(default_vertex_b, axis_matrix, body_matrix)
        update_body_mesh(
            body_object,
            shape,
            capsule_radius,
            capsule_radius * 2.0,
            capsule_length,
            vertex_a=vertex_a,
            vertex_b=vertex_b,
            shape_offset=[0.0, 0.0, 0.0],
        )
        body_object[RAGDOLL_BODY_VERTEX_A_PROP] = vertex_a
        body_object[RAGDOLL_BODY_VERTEX_B_PROP] = vertex_b
        body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = [capsule_radius, capsule_length * 0.5, capsule_radius]
        body_object[RAGDOLL_BODY_JOINT_ORIGIN_PROP] = True
    else:
        resolved_radius, resolved_height, resolved_length = resolved_creation_dimensions(shape, radius, height, length if length > 0.0 else bone_length)
        body_object[RAGDOLL_BODY_JOINT_ORIGIN_PROP] = False
        if shape == "SPHERE":
            update_body_mesh(body_object, shape, resolved_radius, resolved_height, resolved_length, shape_offset=[0.0, 0.0, 0.0])
            body_object[RAGDOLL_BODY_VERTEX_A_PROP] = [0.0, 0.0, 0.0]
            body_object[RAGDOLL_BODY_VERTEX_B_PROP] = [0.0, 0.0, 0.0]
            body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = sphere_half_extents(resolved_radius)
        else:
            half_extents = box_half_extents(resolved_radius, resolved_height, resolved_length)
            update_body_mesh(body_object, shape, resolved_radius, resolved_height, resolved_length, half_extents=half_extents, shape_offset=[0.0, 0.0, 0.0])
            body_object[RAGDOLL_BODY_VERTEX_A_PROP] = [0.0, 0.0, 0.0]
            body_object[RAGDOLL_BODY_VERTEX_B_PROP] = [0.0, 0.0, 0.0]
            body_object[RAGDOLL_BODY_HALF_EXTENTS_PROP] = half_extents
    return body_object


def create_or_update_bodies_for_selection(
    context: bpy.types.Context,
    skeleton_object: bpy.types.Object,
    bone_names: Iterable[str],
    shape: str,
    radius: float,
    height: float,
    length: float,
) -> list[bpy.types.Object]:
    created: list[bpy.types.Object] = []
    requested_bone_names = [bone_name for bone_name in bone_names if bone_name]
    active_bone = active_ragdoll_bone(context)
    active_bone_name = active_bone.name if active_bone is not None else None
    for bone_name in requested_bone_names:
        preferred_descendant_name = None
        if active_bone_name and active_bone_name != bone_name:
            root_bone = skeleton_object.data.bones.get(bone_name)
            active_bone_data = skeleton_object.data.bones.get(active_bone_name)
            if root_bone is not None and _immediate_child_on_path(root_bone, active_bone_data) is not None:
                preferred_descendant_name = active_bone_name
        created.append(
            create_or_update_body_for_bone(
                skeleton_object,
                bone_name,
                shape,
                radius,
                height,
                length,
                preferred_descendant_name=preferred_descendant_name,
            )
        )
    return created