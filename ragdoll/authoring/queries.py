from __future__ import annotations

import bpy

from ...utils import blender_to_dx_matrix
from .constants import (
    RAGDOLL_BODIES_COLLECTION_NAME,
    RAGDOLL_BONE_ORDER_PROP,
    RAGDOLL_BODY_BONE_PROP,
    RAGDOLL_BODY_HEIGHT_PROP,
    RAGDOLL_BODY_LENGTH_PROP,
    RAGDOLL_BODY_PROP,
    RAGDOLL_BODY_RADIUS_PROP,
    RAGDOLL_BODY_SHAPE_PROP,
    RAGDOLL_CAPSULE_HANDLE_BODY_PROP,
    RAGDOLL_CAPSULE_HANDLE_PROP,
    RAGDOLL_LOCAL_POS_PROP,
    RAGDOLL_LOCAL_ROT_PROP,
    RAGDOLL_LOCAL_SCALE_PROP,
    RAGDOLL_SOURCE_ARMATURE_PROP,
    RAGDOLL_SKELETON_PROP,
)


def is_ragdoll_skeleton_object(obj: bpy.types.Object | None) -> bool:
    return bool(obj and obj.type == "ARMATURE" and obj.get(RAGDOLL_SKELETON_PROP, False))


def is_ragdoll_body_object(obj: bpy.types.Object | None) -> bool:
    return bool(obj and obj.type == "MESH" and obj.get(RAGDOLL_BODY_PROP, False))


def is_ragdoll_capsule_handle_object(obj: bpy.types.Object | None) -> bool:
    return bool(obj and obj.type == "EMPTY" and obj.get(RAGDOLL_CAPSULE_HANDLE_PROP, False))


def resolve_ragdoll_body_object(obj: bpy.types.Object | None) -> bpy.types.Object | None:
    if is_ragdoll_body_object(obj):
        return obj
    if not is_ragdoll_capsule_handle_object(obj):
        return None
    if is_ragdoll_body_object(obj.parent):
        return obj.parent
    body_name = str(obj.get(RAGDOLL_CAPSULE_HANDLE_BODY_PROP, "") or "")
    body_object = bpy.data.objects.get(body_name) if body_name else None
    return body_object if is_ragdoll_body_object(body_object) else None


def find_source_armature(context: bpy.types.Context) -> bpy.types.Object | None:
    active_object = context.active_object
    if active_object is not None and active_object.type == "ARMATURE" and not is_ragdoll_skeleton_object(active_object):
        return active_object

    armatures = [
        obj for obj in context.scene.objects
        if obj.type == "ARMATURE" and not is_ragdoll_skeleton_object(obj)
    ]
    if len(armatures) == 1:
        return armatures[0]
    return None


def resolve_selected_ragdoll_bones(context: bpy.types.Context) -> list[str]:
    body_object = resolve_ragdoll_body_object(context.active_object)
    if body_object is not None:
        bone_name = str(body_object.get(RAGDOLL_BODY_BONE_PROP, "") or "")
        return [bone_name] if bone_name else []

    active_object = context.active_object
    if active_object is None:
        return []

    if not is_ragdoll_skeleton_object(active_object):
        return []

    if context.mode == "POSE":
        selected = [bone.name for bone in context.selected_pose_bones or []]
        return selected or [bone.name for bone in active_object.data.bones]
    if context.mode == "EDIT_ARMATURE":
        selected = [bone.name for bone in context.selected_editable_bones or []]
        return selected or [bone.name for bone in active_object.data.bones]
    return [bone.name for bone in active_object.data.bones]


def active_ragdoll_bone(context: bpy.types.Context) -> bpy.types.Bone | None:
    body_object = resolve_ragdoll_body_object(context.active_object)
    if body_object is not None:
        skeleton_object = find_ragdoll_skeleton_for_body(body_object)
        if skeleton_object is None:
            return None
        return skeleton_object.data.bones.get(body_object.get(RAGDOLL_BODY_BONE_PROP, ""))

    active_object = context.active_object
    if active_object is None:
        return None

    if not is_ragdoll_skeleton_object(active_object):
        return None

    if context.mode == "POSE" and context.active_pose_bone is not None:
        return active_object.data.bones.get(context.active_pose_bone.name)
    if context.mode == "EDIT_ARMATURE" and context.active_bone is not None:
        return active_object.data.bones.get(context.active_bone.name)
    return None


def find_ragdoll_skeleton_for_body(body_object: bpy.types.Object) -> bpy.types.Object | None:
    body_collection = body_object.users_collection[0] if body_object.users_collection else None
    if body_collection is None:
        return None
    for obj in bpy.data.objects:
        if is_ragdoll_skeleton_object(obj):
            for collection in obj.users_collection:
                if collection == body_collection or body_collection.name in collection.children:
                    return obj
            if obj.name == body_collection.name:
                return obj
    source_name = body_object.get(RAGDOLL_SOURCE_ARMATURE_PROP, "")
    if source_name:
        obj = bpy.data.objects.get(source_name)
        if is_ragdoll_skeleton_object(obj):
            return obj
    return None


def active_constraint_subject(context: bpy.types.Context) -> tuple[str, bpy.types.Object | bpy.types.Bone | None]:
    body_object = resolve_ragdoll_body_object(context.active_object)
    if body_object is not None:
        return "BODY", body_object
    active_object = context.active_object
    bone = active_ragdoll_bone(context)
    if bone is not None:
        return "BONE", bone
    if is_ragdoll_skeleton_object(active_object):
        return "SKELETON", active_object
    return "NONE", None


def active_body_dimensions(body_object: bpy.types.Object) -> dict[str, float | str]:
    return {
        "shape": str(body_object.get(RAGDOLL_BODY_SHAPE_PROP, "CAPSULE")),
        "radius": float(body_object.get(RAGDOLL_BODY_RADIUS_PROP, 0.1)),
        "height": float(body_object.get(RAGDOLL_BODY_HEIGHT_PROP, 0.2)),
        "length": float(body_object.get(RAGDOLL_BODY_LENGTH_PROP, 0.4)),
    }


def find_ragdoll_skeleton_for_source(source_armature: bpy.types.Object) -> bpy.types.Object | None:
    matches = [
        obj for obj in bpy.data.objects
        if is_ragdoll_skeleton_object(obj) and str(obj.get(RAGDOLL_SOURCE_ARMATURE_PROP, "") or "") == source_armature.name
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        matches.sort(key=lambda obj: obj.name)
        return matches[0]
    return None


def _ragdoll_bones_in_order(skeleton_object: bpy.types.Object) -> list[bpy.types.Bone]:
    bones_by_name = {bone.name: bone for bone in skeleton_object.data.bones}
    stored_order = skeleton_object.get(RAGDOLL_BONE_ORDER_PROP, None)
    if stored_order:
        ordered = [bones_by_name[name] for name in stored_order if name in bones_by_name]
        # Append any bones added after import that are not in the stored order.
        ordered.extend(bone for bone in skeleton_object.data.bones if bone.name not in set(stored_order))
        if len(ordered) == len(skeleton_object.data.bones):
            return ordered
    return list(skeleton_object.data.bones)


def _bone_local_transform(bone: bpy.types.Bone) -> dict[str, list[float]]:
    if RAGDOLL_LOCAL_POS_PROP in bone and RAGDOLL_LOCAL_ROT_PROP in bone:
        return {
            "pos": list(bone.get(RAGDOLL_LOCAL_POS_PROP, [0.0, 0.0, 0.0])),
            "rot": list(bone.get(RAGDOLL_LOCAL_ROT_PROP, [0.0, 0.0, 0.0, 1.0])),
            "scale": list(bone.get(RAGDOLL_LOCAL_SCALE_PROP, [1.0, 1.0, 1.0])),
        }
    if bone.parent is not None:
        local_matrix = bone.parent.matrix_local.inverted() @ bone.matrix_local
    else:
        local_matrix = bone.matrix_local
    local_matrix = blender_to_dx_matrix(local_matrix)
    loc, rot, scale = local_matrix.decompose()
    return {
        "pos": [loc.x, loc.y, loc.z],
        "rot": [rot.x, rot.y, rot.z, rot.w],
        "scale": [scale.x, scale.y, scale.z],
    }


def _body_object_by_bone_name(skeleton_object: bpy.types.Object) -> dict[str, bpy.types.Object]:
    result: dict[str, bpy.types.Object] = {}
    bodies_collection = skeleton_object.users_collection[0].children.get(RAGDOLL_BODIES_COLLECTION_NAME) if skeleton_object.users_collection else None
    if bodies_collection is None:
        return result
    for obj in bodies_collection.objects:
        if is_ragdoll_body_object(obj):
            bone_name = str(obj.get(RAGDOLL_BODY_BONE_PROP, "") or "")
            if bone_name:
                result[bone_name] = obj
    return result


def find_ragdoll_body_for_bone(skeleton_object: bpy.types.Object, bone_name: str) -> bpy.types.Object | None:
    return _body_object_by_bone_name(skeleton_object).get(bone_name)


def find_missing_ragdoll_body_bones(skeleton_object: bpy.types.Object) -> list[str]:
    body_by_name = _body_object_by_bone_name(skeleton_object)
    return [bone.name for bone in _ragdoll_bones_in_order(skeleton_object) if bone.name not in body_by_name]