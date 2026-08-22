from __future__ import annotations

import bpy
from mathutils import Matrix

from ..bodies import create_rigid_bodies_from_skeleton
from ..constraints import create_constraints
from ..skeleton import build_animation_skeleton_from_armature
from .constants import (
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
    RAGDOLL_BODY_COLLISION_FILTER_PROP,
    RAGDOLL_BODY_FRICTION_PROP,
    RAGDOLL_BODY_HALF_EXTENTS_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_LINEAR_DAMPING_PROP,
    RAGDOLL_BODY_MASS_PROP,
    RAGDOLL_BODY_MOTION_TYPE_PROP,
    RAGDOLL_BODY_QUALITY_TYPE_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_RESTITUTION_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_BODY_VERTEX_A_PROP,
    RAGDOLL_BODY_VERTEX_B_PROP,
    RAGDOLL_MAPPING_TRANSFORM_PROP,
    RAGDOLL_SOURCE_BONE_PROP,
)
from .constraint_props import read_constraint_settings
from .geometry import _authored_body_dx_transform, _blender_vector_to_dx_local
from .queries import _body_object_by_bone_name, _bone_local_transform, _ragdoll_bones_in_order
from ...utils import blender_to_dx_matrix


def build_authored_ragdoll_data(
    source_armature: bpy.types.Object,
    skeleton_object: bpy.types.Object,
    auto_generate_missing_bodies: bool = True,
) -> dict:
    animation_skeleton, bone_name_to_idx = build_animation_skeleton_from_armature(source_armature)
    ragdoll_bones = _ragdoll_bones_in_order(skeleton_object)
    ragdoll_names = [bone.name for bone in ragdoll_bones]
    authored_bodies = _body_object_by_bone_name(skeleton_object)
    missing_bone_names = [bone_name for bone_name in ragdoll_names if bone_name not in authored_bodies]
    if missing_bone_names and not auto_generate_missing_bodies:
        preview_names = ", ".join(missing_bone_names[:8])
        if len(missing_bone_names) > 8:
            preview_names = f"{preview_names}, ..."
        raise RuntimeError(
            "Export requires a rigid body for every ragdoll bone when Auto-generate Missing Bodies is disabled. "
            f"Missing bones: {preview_names}"
        )
    ragdoll_bone_to_idx = {bone_name: index for index, bone_name in enumerate(ragdoll_names)}
    ragdoll_skeleton = {
        "name": ragdoll_names[0] if ragdoll_names else "Ragdoll_Bip01",
        "bones": ragdoll_names,
        "parent_indices": [
            -1 if bone.parent is None else ragdoll_bone_to_idx[bone.parent.name]
            for bone in ragdoll_bones
        ],
        "reference_pose": [_bone_local_transform(bone) for bone in ragdoll_bones],
    }

    ragdoll_bone_map = {
        bone.name: str(bone.get(RAGDOLL_SOURCE_BONE_PROP, "") or "").lower()
        for bone in ragdoll_bones
        if str(bone.get(RAGDOLL_SOURCE_BONE_PROP, "") or "")
    }
    bone_mappings = []
    ragdoll_bone_by_name = {bone.name: bone for bone in ragdoll_bones}
    for index, bone_name in enumerate(ragdoll_names):
        source_bone_name = ragdoll_bone_map.get(bone_name)
        if source_bone_name and source_bone_name in bone_name_to_idx:
            mapping_bone = ragdoll_bone_by_name.get(bone_name)
            stored = list(mapping_bone.get(RAGDOLL_MAPPING_TRANSFORM_PROP, [])) if mapping_bone is not None else []
            if len(stored) == 10:
                transform = {
                    "pos": [stored[0], stored[1], stored[2]],
                    "rot": [stored[3], stored[4], stored[5], stored[6]],
                    "scale": [stored[7], stored[8], stored[9]],
                }
            else:
                transform = {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scale": [1, 1, 1]}
            bone_mappings.append(
                {
                    "ragdoll_bone": index,
                    "anim_bone": bone_name_to_idx[source_bone_name],
                    "transform": transform,
                }
            )

    default_rigid_bodies = create_rigid_bodies_from_skeleton(ragdoll_skeleton, source_armature, ragdoll_bone_map)
    body_by_name = {body["name"]: body for body in default_rigid_bodies}
    for bone_name, body_object in authored_bodies.items():
        body_data = body_by_name.get(bone_name)
        if body_data is None:
            continue
        shape = str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, body_data["shape_type"]))
        radius = float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, body_data["radius"]))
        height = float(body_object.get(RAGDOLL_BODY_HEIGHT_PROP, radius * 2.0))
        length = float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, radius * 2.0))
        vertex_a = list(body_object.get(RAGDOLL_BODY_VERTEX_A_PROP, [0.0, 0.0, 0.0]))
        vertex_b = list(body_object.get(RAGDOLL_BODY_VERTEX_B_PROP, [0.0, 0.0, 0.0]))
        vertex_a_dx = _blender_vector_to_dx_local(vertex_a)
        vertex_b_dx = _blender_vector_to_dx_local(vertex_b)
        position_vec, rotation_quat = _authored_body_dx_transform(body_object, shape.lower(), vertex_a, vertex_b)
        body_data.update(
            {
                "shape_type": shape.lower(),
                "radius": radius,
                "mass": float(body_object.get(RAGDOLL_BODY_MASS_PROP, body_data["mass"])),
                "friction": float(body_object.get(RAGDOLL_BODY_FRICTION_PROP, body_data["friction"])),
                "restitution": float(body_object.get(RAGDOLL_BODY_RESTITUTION_PROP, body_data["restitution"])),
                "motion_type": str(body_object.get(RAGDOLL_BODY_MOTION_TYPE_PROP, body_data["motion_type"])),
                "position": [position_vec.x, position_vec.y, position_vec.z],
                "rotation": [rotation_quat.x, rotation_quat.y, rotation_quat.z, rotation_quat.w],
                "linear_damping": float(body_object.get(RAGDOLL_BODY_LINEAR_DAMPING_PROP, body_data["linear_damping"])),
                "angular_damping": float(body_object.get(RAGDOLL_BODY_ANGULAR_DAMPING_PROP, body_data["angular_damping"])),
                "collision_filter_info": int(body_object.get(RAGDOLL_BODY_COLLISION_FILTER_PROP, body_data["collision_filter_info"])),
                "quality_type": int(body_object.get(RAGDOLL_BODY_QUALITY_TYPE_PROP, body_data["quality_type"])),
            }
        )
        if RAGDOLL_BODY_HALF_EXTENTS_PROP in body_object:
            body_data["half_extents"] = list(body_object.get(RAGDOLL_BODY_HALF_EXTENTS_PROP, []))
        if body_data["shape_type"] == "sphere":
            body_data["vertex_a"] = vertex_a_dx
            body_data["vertex_b"] = vertex_b_dx
        elif body_data["shape_type"] == "box":
            body_data["half_extents"] = list(body_object.get(RAGDOLL_BODY_HALF_EXTENTS_PROP, [radius, max(length * 0.5, 0.001), max(height * 0.5, 0.001)]))
        else:
            body_data["vertex_a"] = vertex_a_dx
            body_data["vertex_b"] = vertex_b_dx

        # Bodies whose collision shape is offset from the joint (imported from a
        # convex-translate wrapper) sit at the shape centre, but their joints and
        # mass frame belong at the bone. Writing the body at the shape centre
        # dislocates every joint on it (they tear loose on the first sim step).
        # Restore the shipped encoding: place the body ON its bone and record the
        # offset so the writer re-wraps the shape in a convex-translate.
        bone = skeleton_object.data.bones.get(bone_name)
        if bone is not None:
            bone_world = skeleton_object.matrix_world @ bone.head_local
            gap_world = body_object.matrix_world.translation - bone_world
            if gap_world.length > 1.0e-4:
                gap_local = body_object.matrix_world.to_quaternion().inverted() @ gap_world
                true_matrix = (
                    Matrix.Translation(bone_world)
                    @ body_object.matrix_world.to_quaternion().to_matrix().to_4x4()
                )
                true_pos = blender_to_dx_matrix(true_matrix).decompose()[0]
                body_data["position"] = [true_pos.x, true_pos.y, true_pos.z]
                body_data["shape_offset"] = _blender_vector_to_dx_local(gap_local)

    constraints = create_constraints(ragdoll_skeleton)
    constraint_by_name = {constraint["name"]: constraint for constraint in constraints}
    for bone in ragdoll_bones:
        if bone.parent is None:
            continue
        constraint = constraint_by_name.get(bone.name)
        if constraint is None:
            continue
        settings = read_constraint_settings(bone)
        constraint.update(
            {
                "constraint_type": str(settings["constraint_type"]),
                "pivot_a": list(settings["pivot_a"]),
                "pivot_b": list(settings["pivot_b"]),
                "twist_axis_a": list(settings["twist_axis_a"]),
                "twist_axis_b": list(settings["twist_axis_b"]),
                "plane_axis_a": list(settings["plane_axis_a"]),
                "plane_axis_b": list(settings["plane_axis_b"]),
                "twist_min": float(settings["twist_min"]),
                "twist_max": float(settings["twist_max"]),
                "cone_angle": float(settings["cone_angle"]),
                "plane_min": float(settings["plane_min"]),
                "plane_max": float(settings["plane_max"]),
                "hinge_min": float(settings["hinge_min"]),
                "hinge_max": float(settings["hinge_max"]),
                "friction_torque": float(settings["friction_torque"]),
            }
        )

    return {
        "animation_skeleton": animation_skeleton,
        "ragdoll_skeleton": ragdoll_skeleton,
        "bone_mappings": bone_mappings,
        "rigid_bodies": default_rigid_bodies,
        "constraints": constraints,
    }