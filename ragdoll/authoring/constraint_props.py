from __future__ import annotations

import math

import bpy

from .constants import (
    RAGDOLL_CONSTRAINT_TYPE_PROP,
    RAGDOLL_CONE_ANGLE_PROP,
    RAGDOLL_FRICTION_TORQUE_PROP,
    RAGDOLL_HINGE_MAX_PROP,
    RAGDOLL_HINGE_MIN_PROP,
    RAGDOLL_PIVOT_A_PROP,
    RAGDOLL_PIVOT_B_PROP,
    RAGDOLL_PLANE_AXIS_A_PROP,
    RAGDOLL_PLANE_AXIS_B_PROP,
    RAGDOLL_PLANE_MAX_PROP,
    RAGDOLL_PLANE_MIN_PROP,
    RAGDOLL_TWIST_AXIS_A_PROP,
    RAGDOLL_TWIST_AXIS_B_PROP,
    RAGDOLL_TWIST_MAX_PROP,
    RAGDOLL_TWIST_MIN_PROP,
)


def _apply_constraint_frame_defaults(bone: bpy.types.Bone) -> None:
    bone[RAGDOLL_PIVOT_A_PROP] = [0.0, 0.0, 0.1]
    bone[RAGDOLL_PIVOT_B_PROP] = [0.0, 0.0, 0.0]
    bone[RAGDOLL_TWIST_AXIS_A_PROP] = [0.0, 0.0, 1.0]
    bone[RAGDOLL_TWIST_AXIS_B_PROP] = [0.0, 0.0, 1.0]
    bone[RAGDOLL_PLANE_AXIS_A_PROP] = [1.0, 0.0, 0.0]
    bone[RAGDOLL_PLANE_AXIS_B_PROP] = [1.0, 0.0, 0.0]


def _initialize_constraint_defaults(bone: bpy.types.Bone) -> None:
    bone[RAGDOLL_CONSTRAINT_TYPE_PROP] = "ragdoll"
    bone[RAGDOLL_TWIST_MIN_PROP] = -0.5
    bone[RAGDOLL_TWIST_MAX_PROP] = 0.5
    bone[RAGDOLL_CONE_ANGLE_PROP] = 0.5
    bone[RAGDOLL_PLANE_MIN_PROP] = -0.5
    bone[RAGDOLL_PLANE_MAX_PROP] = 0.5
    bone[RAGDOLL_HINGE_MIN_PROP] = -math.pi
    bone[RAGDOLL_HINGE_MAX_PROP] = math.pi
    bone[RAGDOLL_FRICTION_TORQUE_PROP] = 0.0
    _apply_constraint_frame_defaults(bone)


def read_constraint_settings(bone: bpy.types.Bone) -> dict[str, float | str]:
    defaults = {
        "constraint_type": "ragdoll",
        "twist_min": -0.5,
        "twist_max": 0.5,
        "cone_angle": 0.5,
        "plane_min": -0.5,
        "plane_max": 0.5,
        "hinge_min": -math.pi,
        "hinge_max": math.pi,
        "friction_torque": 0.0,
        "pivot_a": [0.0, 0.0, 0.1],
        "pivot_b": [0.0, 0.0, 0.0],
        "twist_axis_a": [0.0, 0.0, 1.0],
        "twist_axis_b": [0.0, 0.0, 1.0],
        "plane_axis_a": [1.0, 0.0, 0.0],
        "plane_axis_b": [1.0, 0.0, 0.0],
    }
    return {
        "constraint_type": bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, defaults["constraint_type"]),
        "twist_min": float(bone.get(RAGDOLL_TWIST_MIN_PROP, defaults["twist_min"])),
        "twist_max": float(bone.get(RAGDOLL_TWIST_MAX_PROP, defaults["twist_max"])),
        "cone_angle": float(bone.get(RAGDOLL_CONE_ANGLE_PROP, defaults["cone_angle"])),
        "plane_min": float(bone.get(RAGDOLL_PLANE_MIN_PROP, defaults["plane_min"])),
        "plane_max": float(bone.get(RAGDOLL_PLANE_MAX_PROP, defaults["plane_max"])),
        "hinge_min": float(bone.get(RAGDOLL_HINGE_MIN_PROP, defaults["hinge_min"])),
        "hinge_max": float(bone.get(RAGDOLL_HINGE_MAX_PROP, defaults["hinge_max"])),
        "friction_torque": float(bone.get(RAGDOLL_FRICTION_TORQUE_PROP, defaults["friction_torque"])),
        "pivot_a": list(bone.get(RAGDOLL_PIVOT_A_PROP, defaults["pivot_a"])),
        "pivot_b": list(bone.get(RAGDOLL_PIVOT_B_PROP, defaults["pivot_b"])),
        "twist_axis_a": list(bone.get(RAGDOLL_TWIST_AXIS_A_PROP, defaults["twist_axis_a"])),
        "twist_axis_b": list(bone.get(RAGDOLL_TWIST_AXIS_B_PROP, defaults["twist_axis_b"])),
        "plane_axis_a": list(bone.get(RAGDOLL_PLANE_AXIS_A_PROP, defaults["plane_axis_a"])),
        "plane_axis_b": list(bone.get(RAGDOLL_PLANE_AXIS_B_PROP, defaults["plane_axis_b"])),
    }


def apply_constraint_data_to_bone(bone: bpy.types.Bone, constraint_data: dict[str, float | str | list[float]]) -> None:
    if "constraint_type" in constraint_data:
        bone[RAGDOLL_CONSTRAINT_TYPE_PROP] = str(constraint_data["constraint_type"])
    if "twist_min" in constraint_data:
        bone[RAGDOLL_TWIST_MIN_PROP] = float(constraint_data["twist_min"])
    if "twist_max" in constraint_data:
        bone[RAGDOLL_TWIST_MAX_PROP] = float(constraint_data["twist_max"])
    if "cone_angle" in constraint_data:
        bone[RAGDOLL_CONE_ANGLE_PROP] = float(constraint_data["cone_angle"])
    if "plane_min" in constraint_data:
        bone[RAGDOLL_PLANE_MIN_PROP] = float(constraint_data["plane_min"])
    if "plane_max" in constraint_data:
        bone[RAGDOLL_PLANE_MAX_PROP] = float(constraint_data["plane_max"])
    if "hinge_min" in constraint_data:
        bone[RAGDOLL_HINGE_MIN_PROP] = float(constraint_data["hinge_min"])
    if "hinge_max" in constraint_data:
        bone[RAGDOLL_HINGE_MAX_PROP] = float(constraint_data["hinge_max"])
    if "friction_torque" in constraint_data:
        bone[RAGDOLL_FRICTION_TORQUE_PROP] = float(constraint_data["friction_torque"])
    if "pivot_a" in constraint_data:
        bone[RAGDOLL_PIVOT_A_PROP] = list(constraint_data["pivot_a"])
    if "pivot_b" in constraint_data:
        bone[RAGDOLL_PIVOT_B_PROP] = list(constraint_data["pivot_b"])
    if "twist_axis_a" in constraint_data:
        bone[RAGDOLL_TWIST_AXIS_A_PROP] = list(constraint_data["twist_axis_a"])
    if "twist_axis_b" in constraint_data:
        bone[RAGDOLL_TWIST_AXIS_B_PROP] = list(constraint_data["twist_axis_b"])
    if "plane_axis_a" in constraint_data:
        bone[RAGDOLL_PLANE_AXIS_A_PROP] = list(constraint_data["plane_axis_a"])
    if "plane_axis_b" in constraint_data:
        bone[RAGDOLL_PLANE_AXIS_B_PROP] = list(constraint_data["plane_axis_b"])