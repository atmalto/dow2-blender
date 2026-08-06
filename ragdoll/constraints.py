from math import pi

from .naming import canonicalize_bone_name
from .templates import apply_constraint_template


def joint_limits_for_ragdoll_bone(rag_bone_name):
    normalized = canonicalize_bone_name(rag_bone_name)
    if "calf" in normalized:
        return {"twist": [-0.05, 0.05], "cone": 0.05, "plane": [0.0, 2.5]}
    if "forearm" in normalized:
        return {"twist": [-1.0, 1.0], "cone": 0.05, "plane": [-0.05, 2.5]}
    if "upperarm" in normalized or "thigh" in normalized:
        return {"twist": [-1.2, 1.2], "cone": 1.0, "plane": [-0.8, 0.8]}
    if "hand" in normalized or "foot" in normalized or "toe" in normalized:
        return {"twist": [-0.4, 0.4], "cone": 0.35, "plane": [-0.5, 0.8]}
    if "head" in normalized or "neck" in normalized:
        return {"twist": [-0.6, 0.6], "cone": 0.45, "plane": [-0.5, 0.5]}
    if "spine" in normalized or "tail" in normalized:
        return {"twist": [-0.35, 0.35], "cone": 0.35, "plane": [-0.35, 0.35]}
    return {"twist": [-0.5, 0.5], "cone": 0.5, "plane": [-0.5, 0.5]}


def create_constraints(ragdoll_skeleton, template_bundle=None):
    constraints = []
    ragdoll_bone_to_idx = {bone_name: index for index, bone_name in enumerate(ragdoll_skeleton["bones"])}

    for bone_name, parent_idx, child_idx in zip(
        ragdoll_skeleton["bones"],
        ragdoll_skeleton["parent_indices"],
        range(len(ragdoll_skeleton["bones"])),
    ):
        if parent_idx < 0:
            continue

        limits = joint_limits_for_ragdoll_bone(bone_name)
        constraint = {
            "name": bone_name,
            "body_a_index": parent_idx,
            "body_b_index": child_idx,
            "constraint_type": "ragdoll",
            "pivot_a": [0.0, 0.0, 0.1],
            "pivot_b": [0.0, 0.0, 0.0],
            "twist_axis_a": [0.0, 0.0, 1.0],
            "twist_axis_b": [0.0, 0.0, 1.0],
            "plane_axis_a": [1.0, 0.0, 0.0],
            "plane_axis_b": [1.0, 0.0, 0.0],
            "twist_min": limits["twist"][0],
            "twist_max": limits["twist"][1],
            "cone_angle": limits["cone"],
            "plane_min": limits["plane"][0],
            "plane_max": limits["plane"][1],
            "hinge_min": -pi,
            "hinge_max": pi,
            "friction_torque": 0.0,
        }

        template_constraint = None if template_bundle is None else template_bundle["constraints"].get(bone_name)
        if template_constraint is not None:
            constraint = apply_constraint_template(constraint, template_constraint, ragdoll_bone_to_idx)

        constraints.append(constraint)

    return constraints