from __future__ import annotations

from typing import Sequence

import bpy
from mathutils import Matrix, Quaternion, Vector

from ...utils import dx_to_blender_matrix, link_object_to_collection
from ..skeleton import create_ragdoll_skeleton_from_armature
from .collections import ensure_child_collection, ragdoll_collection_name, remove_collection_tree
from .constants import (
    RAGDOLL_LOCAL_POS_PROP,
    RAGDOLL_LOCAL_ROT_PROP,
    RAGDOLL_LOCAL_SCALE_PROP,
    RAGDOLL_SOURCE_ARMATURE_PROP,
    RAGDOLL_SOURCE_BONE_PROP,
    RAGDOLL_SKELETON_PROP,
)
from .constraint_props import _initialize_constraint_defaults


def apply_reference_pose_to_bone(bone: bpy.types.Bone, transform: dict[str, list[float]]) -> None:
    bone[RAGDOLL_LOCAL_POS_PROP] = list(transform["pos"])
    bone[RAGDOLL_LOCAL_ROT_PROP] = list(transform["rot"])
    bone[RAGDOLL_LOCAL_SCALE_PROP] = list(transform.get("scale", [1.0, 1.0, 1.0]))


def _matrix_from_raw_transform(transform: dict[str, Sequence[float]]) -> Matrix:
    quaternion = Quaternion((transform["rot"][3], transform["rot"][0], transform["rot"][1], transform["rot"][2]))
    rotation = quaternion.to_matrix().to_4x4()
    scale = Matrix.Diagonal((transform["scale"][0], transform["scale"][1], transform["scale"][2], 1.0))
    matrix = Matrix.Translation(Vector(transform["pos"])) @ rotation @ scale
    return dx_to_blender_matrix(matrix)


def _resolve_bone_length(source_armature: bpy.types.Object, source_bone_name: str | None) -> float:
    if not source_bone_name:
        return 0.1
    source_bone = source_armature.data.bones.get(source_bone_name)
    if source_bone is None:
        return 0.1
    return max(source_bone.length, 0.05)


def create_scene_ragdoll_skeleton(
    context: bpy.types.Context,
    source_armature: bpy.types.Object,
    ragdoll_name: str,
    ragdoll_bone_order: list[str] | None = None,
) -> bpy.types.Object:
    collection_name = ragdoll_collection_name(ragdoll_name)
    existing_collection = context.scene.collection.children.get(collection_name)
    if existing_collection is not None:
        remove_collection_tree(existing_collection)

    ragdoll_collection = ensure_child_collection(context.scene.collection, collection_name)
    animation_skeleton, ragdoll_skeleton, _bone_mappings, ragdoll_bone_map = create_ragdoll_skeleton_from_armature(
        source_armature,
        ragdoll_bone_order=ragdoll_bone_order,
    )
    del animation_skeleton

    armature_data = bpy.data.armatures.new(collection_name)
    armature_obj = bpy.data.objects.new(collection_name, armature_data)
    armature_obj.matrix_world = source_armature.matrix_world.copy()
    armature_obj[RAGDOLL_SKELETON_PROP] = True
    armature_obj[RAGDOLL_SOURCE_ARMATURE_PROP] = source_armature.name
    link_object_to_collection(armature_obj, ragdoll_collection)

    prior_active = context.view_layer.objects.active
    if prior_active is not None and context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    context.view_layer.objects.active = armature_obj
    armature_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones: list[bpy.types.EditBone] = []
    world_matrices: list[Matrix] = []
    for index, transform in enumerate(ragdoll_skeleton["reference_pose"]):
        local_matrix = _matrix_from_raw_transform(transform)
        parent_index = ragdoll_skeleton["parent_indices"][index]
        world_matrix = local_matrix if parent_index < 0 else world_matrices[parent_index] @ local_matrix
        world_matrices.append(world_matrix)

        bone_name = ragdoll_skeleton["bones"][index]
        edit_bone = armature_data.edit_bones.new(bone_name)
        edit_bone.use_connect = False
        if parent_index >= 0:
            edit_bone.parent = edit_bones[parent_index]
        edit_bone.matrix = world_matrix
        head = world_matrix.to_translation()
        length = _resolve_bone_length(source_armature, ragdoll_bone_map.get(bone_name))
        tail_direction = world_matrix.to_3x3() @ Vector((0.0, length, 0.0))
        if tail_direction.length < 0.001:
            tail_direction = Vector((0.0, length, 0.0))
        edit_bone.head = head
        edit_bone.tail = head + tail_direction
        edit_bones.append(edit_bone)

    bpy.ops.object.mode_set(mode="OBJECT")
    pose_by_name = dict(zip(ragdoll_skeleton["bones"], ragdoll_skeleton["reference_pose"]))
    for bone_name in ragdoll_skeleton["bones"]:
        bone = armature_data.bones.get(bone_name)
        if bone is None:
            continue
        bone[RAGDOLL_SOURCE_BONE_PROP] = ragdoll_bone_map.get(bone_name, "")
        apply_reference_pose_to_bone(bone, pose_by_name[bone_name])
        _initialize_constraint_defaults(bone)

    if prior_active is not None:
        context.view_layer.objects.active = prior_active
    return armature_obj


def _bone_world_points(armature_obj: bpy.types.Object, bone_name: str) -> tuple[Vector, Vector]:
    bone = armature_obj.data.bones.get(bone_name)
    if bone is None:
        raise KeyError(bone_name)
    head = armature_obj.matrix_world @ bone.head_local
    tail = armature_obj.matrix_world @ bone.tail_local
    return head, tail


def _immediate_child_on_path(root_bone: bpy.types.Bone, descendant_bone: bpy.types.Bone | None) -> bpy.types.Bone | None:
    current = descendant_bone
    while current is not None and current.parent is not None:
        if current.parent == root_bone:
            return current
        current = current.parent
    return None


def _preferred_generation_child(
    bone: bpy.types.Bone,
    preferred_descendant: bpy.types.Bone | None = None,
) -> bpy.types.Bone | None:
    explicit_child = _immediate_child_on_path(bone, preferred_descendant)
    if explicit_child is not None:
        return explicit_child

    if not bone.children:
        return None

    parent_children = [child for child in bone.children if child.children]
    if parent_children:
        return parent_children[0]
    return bone.children[0]


def _mapped_animation_leaf_target(
    skeleton_object: bpy.types.Object,
    ragdoll_bone: bpy.types.Bone,
    ragdoll_head: Vector,
    ragdoll_tail: Vector,
) -> Vector | None:
    source_armature_name = str(skeleton_object.get(RAGDOLL_SOURCE_ARMATURE_PROP, "") or "")
    source_bone_name = str(ragdoll_bone.get(RAGDOLL_SOURCE_BONE_PROP, "") or "")
    if not source_armature_name or not source_bone_name:
        return None

    source_armature = bpy.data.objects.get(source_armature_name)
    if source_armature is None or source_armature.type != "ARMATURE":
        return None

    source_bone = source_armature.data.bones.get(source_bone_name)
    if source_bone is None:
        return None

    source_child = _preferred_generation_child(source_bone)
    if source_child is None:
        return None

    source_head = source_armature.matrix_world @ source_bone.head_local
    source_tail = source_armature.matrix_world @ source_bone.tail_local
    source_child_head = source_armature.matrix_world @ source_child.head_local
    source_axis = source_tail - source_head
    source_vector = source_child_head - source_head
    if source_vector.length < 0.001:
        return None

    ragdoll_axis = ragdoll_tail - ragdoll_head
    if source_axis.length >= 0.001 and ragdoll_axis.length >= 0.001:
        mapped_vector = source_axis.normalized().rotation_difference(ragdoll_axis.normalized()) @ source_vector
    elif ragdoll_axis.length >= 0.001:
        mapped_vector = ragdoll_axis.normalized() * source_vector.length
    else:
        mapped_vector = source_vector.copy()

    if mapped_vector.length < 0.001:
        return None
    return ragdoll_head + mapped_vector


def _generated_capsule_segment(
    armature_obj: bpy.types.Object,
    bone_name: str,
    preferred_descendant_name: str | None = None,
) -> tuple[Vector, Vector, bool]:
    bone = armature_obj.data.bones.get(bone_name)
    if bone is None:
        raise KeyError(bone_name)

    head = armature_obj.matrix_world @ bone.head_local
    tail = armature_obj.matrix_world @ bone.tail_local

    preferred_descendant = armature_obj.data.bones.get(preferred_descendant_name) if preferred_descendant_name else None
    child = _preferred_generation_child(bone, preferred_descendant)
    if child is not None:
        child_head = armature_obj.matrix_world @ child.head_local
        if (child_head - head).length >= 0.001:
            return head, child_head, False

    mapped_target = _mapped_animation_leaf_target(armature_obj, bone, head, tail)
    if mapped_target is not None and (mapped_target - head).length >= 0.001:
        return head, mapped_target, False

    direction = tail - head
    if bone.parent is not None:
        parent_head = armature_obj.matrix_world @ bone.parent.head_local
        parent_direction = head - parent_head
        if parent_direction.length >= 0.001:
            direction = parent_direction
    fallback_length = max(0.04, min(max(direction.length, 0.0) * 0.5, 0.12))
    if direction.length < 0.001:
        direction = Vector((0.0, fallback_length, 0.0))
    return head, head + direction.normalized() * fallback_length, True