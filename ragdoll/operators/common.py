from __future__ import annotations

import os

import bpy

from ..authoring import (
    find_ragdoll_skeleton_for_body,
    find_source_armature,
    is_ragdoll_skeleton_object,
    resolve_ragdoll_body_object,
)
from ..naming import to_title_case
from ..skeleton import infer_ragdoll_bone_map


def _resolve_active_armature(context):
    source_armature = find_source_armature(context)
    if source_armature is not None:
        return source_armature
    raise RuntimeError("Select a source animation armature to export, or keep exactly one non-ragdoll armature in the scene")


def _resolve_export_path(path_value, label):
    export_path = bpy.path.abspath(path_value).strip()
    if not export_path:
        raise RuntimeError(f"Choose an output path for {label}")
    os.makedirs(os.path.dirname(export_path) or ".", exist_ok=True)
    return export_path


def _resolve_active_ragdoll_skeleton(context):
    active_object = context.active_object
    if is_ragdoll_skeleton_object(active_object):
        return active_object
    body_object = resolve_ragdoll_body_object(active_object)
    if body_object is not None:
        skeleton_object = find_ragdoll_skeleton_for_body(body_object)
        if skeleton_object is not None:
            return skeleton_object
    return None


def _selected_source_bone_names(context, source_armature):
    if context.active_object != source_armature:
        return []
    if context.mode == "POSE":
        return [bone.name for bone in context.selected_pose_bones or []]
    if context.mode == "EDIT_ARMATURE":
        return [bone.name for bone in context.selected_editable_bones or []]
    return []


def _derive_ragdoll_bone_name(animation_bone_name):
    return f"Ragdoll_{to_title_case(animation_bone_name)}"


def _resolve_selected_source_ragdoll_bone_order(context, source_armature):
    selected_bone_names = _selected_source_bone_names(context, source_armature)
    if not selected_bone_names:
        return None

    ragdoll_bone_order = []
    seen = set()
    for bone_name in selected_bone_names:
        rag_name = _derive_ragdoll_bone_name(bone_name)
        if rag_name in seen:
            continue
        seen.add(rag_name)
        ragdoll_bone_order.append(rag_name)

    if not ragdoll_bone_order:
        raise RuntimeError("Selected source bones do not map to any known ragdoll bones")

    infer_ragdoll_bone_map(source_armature, ragdoll_bone_order)
    return ragdoll_bone_order