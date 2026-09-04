from __future__ import annotations

import json

from .import_types import (
    ImportedBoneMapping,
    ImportedConstraint,
    ImportedRagdollScene,
    ImportedRigidBody,
    ImportedSkeleton,
    ImportedTransform,
    RagdollImportError,
)


def parse_ragdoll_json(json_path: str, source_format: str) -> ImportedRagdollScene:
    try:
        with open(json_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except OSError as exc:
        raise RagdollImportError(f"Failed to read ragdoll JSON: {exc}") from exc
    except ValueError as exc:
        raise RagdollImportError(f"Failed to parse ragdoll JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise RagdollImportError("The ragdoll JSON root must be an object")

    animation_skeleton = _parse_skeleton(payload.get("animation_skeleton"), "animation_skeleton")
    ragdoll_skeleton = _parse_skeleton(payload.get("ragdoll_skeleton"), "ragdoll_skeleton")
    bone_mappings = _parse_bone_mappings(
        payload.get("bone_mappings"),
        animation_bone_count=len(animation_skeleton.bones),
        ragdoll_bone_count=len(ragdoll_skeleton.bones),
    )
    rigid_bodies = _parse_rigid_bodies(
        payload.get("rigid_bodies"),
        ragdoll_bone_count=len(ragdoll_skeleton.bones),
    )
    constraints = _parse_constraints(
        payload.get("constraints"),
        rigid_body_count=len(rigid_bodies),
    )

    return ImportedRagdollScene(
        animation_skeleton=animation_skeleton,
        ragdoll_skeleton=ragdoll_skeleton,
        bone_mappings=bone_mappings,
        rigid_bodies=rigid_bodies,
        constraints=constraints,
        source_format=source_format,
    )


def _parse_skeleton(raw_skeleton: object, label: str) -> ImportedSkeleton:
    if not isinstance(raw_skeleton, dict):
        raise RagdollImportError(f"Missing or invalid {label} object")

    bones = raw_skeleton.get("bones")
    if not isinstance(bones, list) or not bones:
        raise RagdollImportError(f"{label}.bones must be a non-empty list")

    parsed_bones: list[str] = []
    for index, bone_name in enumerate(bones):
        name = str(bone_name or "").strip()
        if not name:
            raise RagdollImportError(f"{label}.bones[{index}] must be a non-empty string")
        parsed_bones.append(name)

    parent_indices = raw_skeleton.get("parent_indices")
    if not isinstance(parent_indices, list) or len(parent_indices) != len(parsed_bones):
        raise RagdollImportError(
            f"{label}.parent_indices must contain exactly {len(parsed_bones)} entries"
        )

    parsed_parent_indices: list[int] = []
    root_count = 0
    for index, parent_index in enumerate(parent_indices):
        value = _require_int(parent_index, f"{label}.parent_indices[{index}]")
        if value == -1:
            root_count += 1
        elif value < 0 or value >= len(parsed_bones):
            raise RagdollImportError(
                f"{label}.parent_indices[{index}]={value} is out of range for {len(parsed_bones)} bones"
            )
        elif value == index:
            raise RagdollImportError(f"{label}.parent_indices[{index}] cannot reference itself")
        parsed_parent_indices.append(value)

    if root_count != 1:
        raise RagdollImportError(f"{label} must contain exactly one root bone")

    reference_pose = raw_skeleton.get("reference_pose")
    if not isinstance(reference_pose, list) or len(reference_pose) != len(parsed_bones):
        raise RagdollImportError(
            f"{label}.reference_pose must contain exactly {len(parsed_bones)} entries"
        )

    parsed_reference_pose = [
        _parse_transform(transform, f"{label}.reference_pose[{index}]")
        for index, transform in enumerate(reference_pose)
    ]

    return ImportedSkeleton(
        name=str(raw_skeleton.get("name") or label),
        bones=parsed_bones,
        parent_indices=parsed_parent_indices,
        reference_pose=parsed_reference_pose,
    )


def _parse_bone_mappings(
    raw_mappings: object,
    animation_bone_count: int,
    ragdoll_bone_count: int,
) -> list[ImportedBoneMapping]:
    if not isinstance(raw_mappings, list) or not raw_mappings:
        raise RagdollImportError("bone_mappings must be a non-empty list")

    mappings: list[ImportedBoneMapping] = []
    seen_ragdoll_bones: set[int] = set()
    seen_anim_bones: set[int] = set()
    for index, raw_mapping in enumerate(raw_mappings):
        if not isinstance(raw_mapping, dict):
            raise RagdollImportError(f"bone_mappings[{index}] must be an object")

        ragdoll_bone = _require_int(raw_mapping.get("ragdoll_bone"), f"bone_mappings[{index}].ragdoll_bone")
        anim_bone = _require_int(raw_mapping.get("anim_bone"), f"bone_mappings[{index}].anim_bone")
        if ragdoll_bone < 0 or ragdoll_bone >= ragdoll_bone_count:
            raise RagdollImportError(
                f"bone_mappings[{index}].ragdoll_bone={ragdoll_bone} is out of range"
            )
        if anim_bone < 0 or anim_bone >= animation_bone_count:
            raise RagdollImportError(
                f"bone_mappings[{index}].anim_bone={anim_bone} is out of range"
            )
        if ragdoll_bone in seen_ragdoll_bones:
            raise RagdollImportError(f"Duplicate ragdoll bone mapping for index {ragdoll_bone}")
        if anim_bone in seen_anim_bones:
            raise RagdollImportError(f"Duplicate animation bone mapping for index {anim_bone}")

        seen_ragdoll_bones.add(ragdoll_bone)
        seen_anim_bones.add(anim_bone)
        mappings.append(
            ImportedBoneMapping(
                ragdoll_bone=ragdoll_bone,
                anim_bone=anim_bone,
                transform=_parse_transform(
                    raw_mapping.get("transform"),
                    f"bone_mappings[{index}].transform",
                ),
            )
        )

    return mappings


def _parse_rigid_bodies(raw_bodies: object, ragdoll_bone_count: int) -> list[ImportedRigidBody]:
    if not isinstance(raw_bodies, list) or not raw_bodies:
        raise RagdollImportError("rigid_bodies must be a non-empty list")

    rigid_bodies: list[ImportedRigidBody] = []
    seen_bone_indices: set[int] = set()
    for index, raw_body in enumerate(raw_bodies):
        if not isinstance(raw_body, dict):
            raise RagdollImportError(f"rigid_bodies[{index}] must be an object")

        bone_index = _require_int(raw_body.get("bone_index"), f"rigid_bodies[{index}].bone_index")
        if bone_index < 0 or bone_index >= ragdoll_bone_count:
            raise RagdollImportError(f"rigid_bodies[{index}].bone_index={bone_index} is out of range")
        if bone_index in seen_bone_indices:
            raise RagdollImportError(f"Duplicate rigid body for ragdoll bone index {bone_index}")
        seen_bone_indices.add(bone_index)

        shape_type = str(raw_body.get("shape_type") or "").strip().lower()
        if shape_type not in {"sphere", "capsule", "box"}:
            raise RagdollImportError(
                f"rigid_bodies[{index}].shape_type must be sphere, capsule, or box"
            )

        rigid_bodies.append(
            ImportedRigidBody(
                name=str(raw_body.get("name") or f"RigidBody {index + 1}"),
                bone_index=bone_index,
                shape_type=shape_type,
                radius=_require_float(raw_body.get("radius"), f"rigid_bodies[{index}].radius"),
                shape_offset=_require_vector(
                    raw_body.get("shape_offset", [0.0, 0.0, 0.0]),
                    3,
                    f"rigid_bodies[{index}].shape_offset",
                ),
                vertex_a=_require_vector(raw_body.get("vertex_a"), 3, f"rigid_bodies[{index}].vertex_a"),
                vertex_b=_require_vector(raw_body.get("vertex_b"), 3, f"rigid_bodies[{index}].vertex_b"),
                half_extents=_require_vector(
                    raw_body.get("half_extents"),
                    3,
                    f"rigid_bodies[{index}].half_extents",
                ),
                mass=_require_float(raw_body.get("mass"), f"rigid_bodies[{index}].mass"),
                friction=_require_float(raw_body.get("friction"), f"rigid_bodies[{index}].friction"),
                restitution=_require_float(
                    raw_body.get("restitution"),
                    f"rigid_bodies[{index}].restitution",
                ),
                motion_type=str(raw_body.get("motion_type") or "").strip(),
                position=_require_vector(
                    raw_body.get("position"),
                    3,
                    f"rigid_bodies[{index}].position",
                ),
                rotation=_require_vector(
                    raw_body.get("rotation"),
                    4,
                    f"rigid_bodies[{index}].rotation",
                ),
                linear_damping=_require_float(
                    raw_body.get("linear_damping"),
                    f"rigid_bodies[{index}].linear_damping",
                ),
                angular_damping=_require_float(
                    raw_body.get("angular_damping"),
                    f"rigid_bodies[{index}].angular_damping",
                ),
                collision_filter_info=_require_int(
                    raw_body.get("collision_filter_info"),
                    f"rigid_bodies[{index}].collision_filter_info",
                ),
                quality_type=_require_int(
                    raw_body.get("quality_type"),
                    f"rigid_bodies[{index}].quality_type",
                ),
            )
        )

    return rigid_bodies


def _parse_constraints(raw_constraints: object, rigid_body_count: int) -> list[ImportedConstraint]:
    if not isinstance(raw_constraints, list):
        raise RagdollImportError("constraints must be a list")

    constraints: list[ImportedConstraint] = []
    for index, raw_constraint in enumerate(raw_constraints):
        if not isinstance(raw_constraint, dict):
            raise RagdollImportError(f"constraints[{index}] must be an object")

        body_a_index = _require_int(raw_constraint.get("body_a_index"), f"constraints[{index}].body_a_index")
        body_b_index = _require_int(raw_constraint.get("body_b_index"), f"constraints[{index}].body_b_index")
        if body_a_index < 0 or body_a_index >= rigid_body_count:
            raise RagdollImportError(f"constraints[{index}].body_a_index={body_a_index} is out of range")
        if body_b_index < 0 or body_b_index >= rigid_body_count:
            raise RagdollImportError(f"constraints[{index}].body_b_index={body_b_index} is out of range")

        constraint_type = str(raw_constraint.get("constraint_type") or "").strip().lower()
        if constraint_type not in {"ragdoll", "limited_hinge"}:
            raise RagdollImportError(
                f"constraints[{index}].constraint_type must be ragdoll or limited_hinge"
            )

        constraints.append(
            ImportedConstraint(
                name=str(raw_constraint.get("name") or f"Constraint {index + 1}"),
                body_a_index=body_a_index,
                body_b_index=body_b_index,
                constraint_type=constraint_type,
                pivot_a=_require_vector(raw_constraint.get("pivot_a"), 3, f"constraints[{index}].pivot_a"),
                pivot_b=_require_vector(raw_constraint.get("pivot_b"), 3, f"constraints[{index}].pivot_b"),
                twist_axis_a=_require_vector(
                    raw_constraint.get("twist_axis_a"),
                    3,
                    f"constraints[{index}].twist_axis_a",
                ),
                twist_axis_b=_require_vector(
                    raw_constraint.get("twist_axis_b"),
                    3,
                    f"constraints[{index}].twist_axis_b",
                ),
                plane_axis_a=_require_vector(
                    raw_constraint.get("plane_axis_a"),
                    3,
                    f"constraints[{index}].plane_axis_a",
                ),
                plane_axis_b=_require_vector(
                    raw_constraint.get("plane_axis_b"),
                    3,
                    f"constraints[{index}].plane_axis_b",
                ),
                twist_min=_require_float(raw_constraint.get("twist_min"), f"constraints[{index}].twist_min"),
                twist_max=_require_float(raw_constraint.get("twist_max"), f"constraints[{index}].twist_max"),
                cone_angle=_require_float(raw_constraint.get("cone_angle"), f"constraints[{index}].cone_angle"),
                plane_min=_require_float(raw_constraint.get("plane_min"), f"constraints[{index}].plane_min"),
                plane_max=_require_float(raw_constraint.get("plane_max"), f"constraints[{index}].plane_max"),
                hinge_min=_require_float(raw_constraint.get("hinge_min"), f"constraints[{index}].hinge_min"),
                hinge_max=_require_float(raw_constraint.get("hinge_max"), f"constraints[{index}].hinge_max"),
                friction_torque=_require_float(
                    raw_constraint.get("friction_torque"),
                    f"constraints[{index}].friction_torque",
                ),
            )
        )

    return constraints


def _parse_transform(raw_transform: object, label: str) -> ImportedTransform:
    if not isinstance(raw_transform, dict):
        raise RagdollImportError(f"{label} must be an object")

    return ImportedTransform(
        pos=_require_vector(raw_transform.get("pos"), 3, f"{label}.pos"),
        rot=_require_vector(raw_transform.get("rot"), 4, f"{label}.rot"),
        scale=_require_vector(raw_transform.get("scale"), 3, f"{label}.scale"),
    )


def _require_vector(value: object, length: int, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < length:
        raise RagdollImportError(f"{label} must be a list with at least {length} numbers")

    vector: list[float] = []
    for index in range(length):
        vector.append(_require_float(value[index], f"{label}[{index}]") )
    return vector


def _require_float(value: object, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise RagdollImportError(f"{label} must be a number") from exc


def _require_int(value: object, label: str) -> int:
    number = _require_float(value, label)
    if int(number) != number:
        raise RagdollImportError(f"{label} must be an integer")
    return int(number)


__all__ = [
    "parse_ragdoll_json",
]