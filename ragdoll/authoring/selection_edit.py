from __future__ import annotations

from collections.abc import Sequence

import bpy

from .body_authoring import apply_body_data_to_object
from .body_shape_helpers import build_shape_switch_payload, normalize_body_shape
from .constants import (
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP,
    RAGDOLL_BODY_BONE_PROP,
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
    RAGDOLL_BODY_SHAPE_OFFSET_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_CONE_ANGLE_PROP,
    RAGDOLL_CONSTRAINT_TYPE_PROP,
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
from .preview import sync_constraint_preview_objects
from .queries import find_ragdoll_skeleton_for_body, resolve_ragdoll_body_object


_SELECTION_EDIT_STATE: dict[str, object] | None = None
_SELECTION_EDIT_IN_PROGRESS = False

_BODY_PROP_DEFAULTS: dict[str, object] = {
    RAGDOLL_BODY_RADIUS_PROP: 0.1,
    RAGDOLL_BODY_HEIGHT_PROP: 0.2,
    RAGDOLL_BODY_LENGTH_PROP: 0.4,
    RAGDOLL_BODY_HALF_EXTENTS_PROP: [0.1, 0.2, 0.1],
    RAGDOLL_BODY_SHAPE_OFFSET_PROP: [0.0, 0.0, 0.0],
    RAGDOLL_BODY_MASS_PROP: 5.0,
    RAGDOLL_BODY_FRICTION_PROP: 1.0,
    RAGDOLL_BODY_MOTION_TYPE_PROP: "MOTION_BOX_INERTIA",
    RAGDOLL_BODY_LINEAR_DAMPING_PROP: 1.0,
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP: 3.0,
    RAGDOLL_BODY_COLLISION_FILTER_PROP: 65984,
    RAGDOLL_BODY_QUALITY_TYPE_PROP: 4,
    RAGDOLL_BODY_RESTITUTION_PROP: 0.0,
}

_BODY_PROP_COMPATIBILITY: dict[str, str] = {
    RAGDOLL_BODY_RADIUS_PROP: "shape",
    RAGDOLL_BODY_HEIGHT_PROP: "shape",
    RAGDOLL_BODY_LENGTH_PROP: "shape",
    RAGDOLL_BODY_HALF_EXTENTS_PROP: "shape",
    RAGDOLL_BODY_SHAPE_OFFSET_PROP: "common",
    RAGDOLL_BODY_MASS_PROP: "common",
    RAGDOLL_BODY_FRICTION_PROP: "common",
    RAGDOLL_BODY_MOTION_TYPE_PROP: "common",
    RAGDOLL_BODY_LINEAR_DAMPING_PROP: "common",
    RAGDOLL_BODY_ANGULAR_DAMPING_PROP: "common",
    RAGDOLL_BODY_COLLISION_FILTER_PROP: "common",
    RAGDOLL_BODY_QUALITY_TYPE_PROP: "common",
    RAGDOLL_BODY_RESTITUTION_PROP: "common",
}

_BODY_GEOMETRY_PROPS = {
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_HALF_EXTENTS_PROP,
    RAGDOLL_BODY_SHAPE_OFFSET_PROP,
}

_CONSTRAINT_PROP_DEFAULTS: dict[str, object] = {
    RAGDOLL_HINGE_MIN_PROP: -3.141592653589793,
    RAGDOLL_HINGE_MAX_PROP: 3.141592653589793,
    RAGDOLL_TWIST_MIN_PROP: -0.5,
    RAGDOLL_TWIST_MAX_PROP: 0.5,
    RAGDOLL_CONE_ANGLE_PROP: 0.5,
    RAGDOLL_PLANE_MIN_PROP: -0.5,
    RAGDOLL_PLANE_MAX_PROP: 0.5,
    RAGDOLL_FRICTION_TORQUE_PROP: 0.0,
    RAGDOLL_PIVOT_A_PROP: [0.0, 0.0, 0.1],
    RAGDOLL_PIVOT_B_PROP: [0.0, 0.0, 0.0],
    RAGDOLL_TWIST_AXIS_A_PROP: [0.0, 0.0, 1.0],
    RAGDOLL_TWIST_AXIS_B_PROP: [0.0, 0.0, 1.0],
    RAGDOLL_PLANE_AXIS_A_PROP: [1.0, 0.0, 0.0],
    RAGDOLL_PLANE_AXIS_B_PROP: [1.0, 0.0, 0.0],
}

_CONSTRAINT_PROP_COMPATIBILITY: dict[str, str] = {
    RAGDOLL_HINGE_MIN_PROP: "constraint",
    RAGDOLL_HINGE_MAX_PROP: "constraint",
    RAGDOLL_TWIST_MIN_PROP: "constraint",
    RAGDOLL_TWIST_MAX_PROP: "constraint",
    RAGDOLL_CONE_ANGLE_PROP: "constraint",
    RAGDOLL_PLANE_MIN_PROP: "constraint",
    RAGDOLL_PLANE_MAX_PROP: "constraint",
    RAGDOLL_FRICTION_TORQUE_PROP: "common",
    RAGDOLL_PIVOT_A_PROP: "common",
    RAGDOLL_PIVOT_B_PROP: "common",
    RAGDOLL_TWIST_AXIS_A_PROP: "common",
    RAGDOLL_TWIST_AXIS_B_PROP: "common",
    RAGDOLL_PLANE_AXIS_A_PROP: "common",
    RAGDOLL_PLANE_AXIS_B_PROP: "common",
}

_CONSTRAINT_REQUIRED_TYPE: dict[str, str] = {
    RAGDOLL_HINGE_MIN_PROP: "limited_hinge",
    RAGDOLL_HINGE_MAX_PROP: "limited_hinge",
    RAGDOLL_TWIST_MIN_PROP: "ragdoll",
    RAGDOLL_TWIST_MAX_PROP: "ragdoll",
    RAGDOLL_CONE_ANGLE_PROP: "ragdoll",
    RAGDOLL_PLANE_MIN_PROP: "ragdoll",
    RAGDOLL_PLANE_MAX_PROP: "ragdoll",
}


def _normalized_value(value):
    if hasattr(value, "to_list"):
        value = value.to_list()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(_normalized_value(item) for item in value)
    if isinstance(value, float):
        return round(float(value), 6)
    if isinstance(value, int):
        return int(value)
    return value


def _copy_prop_value(value):
    if hasattr(value, "to_list"):
        return list(value.to_list())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [
            _copy_prop_value(item)
            for item in value
        ]
    return value


def _selected_ragdoll_bodies(context: bpy.types.Context) -> list[bpy.types.Object]:
    bodies: list[bpy.types.Object] = []
    seen: set[int] = set()
    active_body = resolve_ragdoll_body_object(context.active_object)
    if active_body is not None:
        bodies.append(active_body)
        seen.add(active_body.as_pointer())
    for obj in context.selected_objects or []:
        body_object = resolve_ragdoll_body_object(obj)
        if body_object is None:
            continue
        object_key = body_object.as_pointer()
        if object_key in seen:
            continue
        seen.add(object_key)
        bodies.append(body_object)
    return bodies


def _constraint_bone_for_body(body_object: bpy.types.Object) -> bpy.types.Bone | None:
    skeleton_object = find_ragdoll_skeleton_for_body(body_object)
    if skeleton_object is None:
        return None
    bone_name = str(body_object.get(RAGDOLL_BODY_BONE_PROP, "") or "")
    if not bone_name:
        return None
    return skeleton_object.data.bones.get(bone_name)


def _build_selection_state(context: bpy.types.Context) -> dict[str, object] | None:
    selected_bodies = _selected_ragdoll_bodies(context)
    if not selected_bodies:
        return None
    active_body = selected_bodies[0]
    active_bone = _constraint_bone_for_body(active_body)
    constraint_type = None
    if active_bone is not None and active_bone.parent is not None:
        constraint_type = str(active_bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll") or "ragdoll")
    return {
        "leader": active_body.as_pointer(),
        "selection": tuple(body.as_pointer() for body in selected_bodies),
        "body_shape": normalize_body_shape(active_body.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE")),
        "constraint_type": constraint_type,
        "body_values": {
            prop_name: _normalized_value(active_body.get(prop_name, _BODY_PROP_DEFAULTS[prop_name]))
            for prop_name in _BODY_PROP_COMPATIBILITY
        },
        "constraint_values": {
            prop_name: _normalized_value(active_bone.get(prop_name, _CONSTRAINT_PROP_DEFAULTS[prop_name]))
            for prop_name in _CONSTRAINT_PROP_COMPATIBILITY
        } if active_bone is not None and active_bone.parent is not None else {},
    }


def _refresh_selection_state(context: bpy.types.Context) -> None:
    global _SELECTION_EDIT_STATE
    _SELECTION_EDIT_STATE = _build_selection_state(context)


def apply_body_shape_to_selected(context: bpy.types.Context, shape: str) -> list[bpy.types.Object]:
    from .body_sync import sync_ragdoll_body_object

    selected_bodies = _selected_ragdoll_bodies(context)
    if not selected_bodies:
        return []

    reference_body = selected_bodies[0]
    reference_shape = normalize_body_shape(reference_body.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE"))
    changed_bodies: list[bpy.types.Object] = []
    for body_object in selected_bodies:
        if normalize_body_shape(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE")) != reference_shape:
            continue
        current_radius = float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1))
        current_height = float(body_object.get(RAGDOLL_BODY_HEIGHT_PROP, 0.2))
        current_length = float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, 0.4))
        payload = build_shape_switch_payload(shape, current_radius, current_height, current_length)
        apply_body_data_to_object(body_object, payload, apply_world_transform=False)
        sync_ragdoll_body_object(body_object, force=True)
        changed_bodies.append(body_object)

    _refresh_selection_state(context)
    return changed_bodies


def apply_constraint_type_to_selected(context: bpy.types.Context, constraint_type: str) -> list[bpy.types.Bone]:
    selected_bodies = _selected_ragdoll_bodies(context)
    if not selected_bodies:
        return []

    reference_bone = _constraint_bone_for_body(selected_bodies[0])
    if reference_bone is None or reference_bone.parent is None:
        return []

    reference_type = str(reference_bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll") or "ragdoll")
    changed_bones: list[bpy.types.Bone] = []
    for body_object in selected_bodies:
        bone = _constraint_bone_for_body(body_object)
        if bone is None or bone.parent is None:
            continue
        if str(bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll") or "ragdoll") != reference_type:
            continue
        bone[RAGDOLL_CONSTRAINT_TYPE_PROP] = constraint_type
        changed_bones.append(bone)

    sync_constraint_preview_objects()
    _refresh_selection_state(context)
    return changed_bones


def propagate_selected_ragdoll_edits(context: bpy.types.Context | None = None) -> int:
    from .body_sync import sync_ragdoll_body_object

    global _SELECTION_EDIT_IN_PROGRESS

    if _SELECTION_EDIT_IN_PROGRESS:
        return 0

    context = context or bpy.context
    current_state = _build_selection_state(context)
    if current_state is None:
        _refresh_selection_state(context)
        return 0

    previous_state = _SELECTION_EDIT_STATE
    if previous_state is None:
        _refresh_selection_state(context)
        return 0

    if previous_state.get("leader") != current_state.get("leader") or previous_state.get("selection") != current_state.get("selection"):
        _refresh_selection_state(context)
        return 0

    selected_bodies = _selected_ragdoll_bodies(context)
    if len(selected_bodies) < 2:
        _refresh_selection_state(context)
        return 0

    reference_body = selected_bodies[0]
    reference_shape = str(current_state.get("body_shape", "CAPSULE") or "CAPSULE")
    reference_constraint_type = current_state.get("constraint_type")
    total_updates = 0
    preview_dirty = False

    _SELECTION_EDIT_IN_PROGRESS = True
    try:
        body_changes = previous_state.get("body_values", {}) != current_state.get("body_values", {})
        if body_changes:
            current_values = dict(current_state.get("body_values", {}))
            previous_values = dict(previous_state.get("body_values", {}))
            for prop_name, compatibility in _BODY_PROP_COMPATIBILITY.items():
                if previous_values.get(prop_name) == current_values.get(prop_name):
                    continue
                source_value = _copy_prop_value(reference_body.get(prop_name, _BODY_PROP_DEFAULTS[prop_name]))
                for body_object in selected_bodies[1:]:
                    if compatibility == "shape":
                        target_shape = normalize_body_shape(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE"))
                        if target_shape != reference_shape:
                            continue
                    body_object[prop_name] = source_value if not isinstance(source_value, list) else list(source_value)
                    if prop_name in _BODY_GEOMETRY_PROPS:
                        sync_ragdoll_body_object(body_object, force=True)
                    total_updates += 1
                    preview_dirty = True

        active_bone = _constraint_bone_for_body(reference_body)
        if active_bone is not None and active_bone.parent is not None and reference_constraint_type is not None:
            current_values = dict(current_state.get("constraint_values", {}))
            previous_values = dict(previous_state.get("constraint_values", {}))
            if previous_values != current_values:
                for prop_name, compatibility in _CONSTRAINT_PROP_COMPATIBILITY.items():
                    if previous_values.get(prop_name) == current_values.get(prop_name):
                        continue
                    source_value = _copy_prop_value(active_bone.get(prop_name, _CONSTRAINT_PROP_DEFAULTS[prop_name]))
                    required_type = _CONSTRAINT_REQUIRED_TYPE.get(prop_name)
                    for body_object in selected_bodies[1:]:
                        target_bone = _constraint_bone_for_body(body_object)
                        if target_bone is None or target_bone.parent is None:
                            continue
                        target_type = str(target_bone.get(RAGDOLL_CONSTRAINT_TYPE_PROP, "ragdoll") or "ragdoll")
                        if compatibility == "constraint" and target_type != reference_constraint_type:
                            continue
                        if required_type is not None and target_type != required_type:
                            continue
                        target_bone[prop_name] = source_value if not isinstance(source_value, list) else list(source_value)
                        total_updates += 1
                        preview_dirty = True
    finally:
        _SELECTION_EDIT_IN_PROGRESS = False

    if preview_dirty:
        sync_constraint_preview_objects()
    _refresh_selection_state(context)
    return total_updates


__all__ = [
    "apply_body_shape_to_selected",
    "apply_constraint_type_to_selected",
    "propagate_selected_ragdoll_edits",
]