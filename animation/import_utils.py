import os

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import bpy
from mathutils import Matrix

from .action_compat import iter_action_fcurves, remove_action_fcurve
from ..model.skeleton_space import remove_bone_axis_adapter


@dataclass
class ImportBoneMapping:
    matched_pose_bones: Dict[int, bpy.types.PoseBone] = field(default_factory=dict)
    bone_mapping: Dict[int, bpy.types.PoseBone] = field(default_factory=dict)
    parent_anim_idx: Dict[int, int] = field(default_factory=dict)
    rest_local_by_anim_idx: Dict[int, Matrix] = field(default_factory=dict)
    missing_bones: List[str] = field(default_factory=list)


def find_pose_bone_case_insensitive(armature: bpy.types.Object, bone_name: str) -> Optional[bpy.types.PoseBone]:
    """Find a pose bone by name on an armature, case-insensitively."""
    bone_name_lower = bone_name.lower()
    for pose_bone in armature.pose.bones:
        if pose_bone.name.lower() == bone_name_lower:
            return pose_bone
    return None


def get_selected_armature_bone_names(context: bpy.types.Context, armature: bpy.types.Object) -> set[str]:
    """Return selected bone names for the target armature across pose/edit/object contexts."""
    selected_bones: set[str] = set()
    selected_pose_bones = getattr(context, "selected_pose_bones_from_active_object", None)
    if selected_pose_bones is None:
        selected_pose_bones = getattr(context, "selected_pose_bones", None)

    if context.mode == 'POSE' and context.active_object == armature:
        if selected_pose_bones:
            selected_bones.update(
                pose_bone.name
                for pose_bone in selected_pose_bones
                if getattr(pose_bone, "id_data", None) == armature
            )
        if selected_bones:
            return selected_bones

        selected_bones.update(pose_bone.name for pose_bone in armature.pose.bones if getattr(pose_bone, "select", False))
        return selected_bones

    if context.mode == 'EDIT_ARMATURE' and context.active_object == armature:
        selected_edit_bones = getattr(context, "selected_editable_bones", None)
        if selected_edit_bones:
            selected_bones.update(edit_bone.name for edit_bone in selected_edit_bones)
        else:
            selected_bones.update(edit_bone.name for edit_bone in armature.data.edit_bones if edit_bone.select)
        return selected_bones

    if selected_pose_bones:
        selected_bones.update(
            pose_bone.name
            for pose_bone in selected_pose_bones
            if getattr(pose_bone, "id_data", None) == armature
        )
        if selected_bones:
            return selected_bones

    selected_bones.update(
        bone.name
        for bone in armature.data.bones
        if getattr(bone, "select", False)
    )
    return selected_bones


def resolve_batch_relative_animation_path(anim_path: str, input_directory: str, unpack_root: str | None) -> str:
    """Return the logical source-relative animation path for loose files or unpacked .hkanim contents."""
    normalized_anim_path = os.path.normpath(anim_path)
    normalized_input = os.path.normpath(input_directory)
    normalized_unpack_root = os.path.normpath(unpack_root) if unpack_root else None

    if normalized_unpack_root:
        try:
            common_path = os.path.commonpath([normalized_anim_path, normalized_unpack_root])
        except ValueError:
            common_path = None
        if common_path == normalized_unpack_root:
            return os.path.relpath(normalized_anim_path, normalized_unpack_root)

    return os.path.relpath(normalized_anim_path, normalized_input)


def get_rest_local_matrix(
    pose_bone: bpy.types.PoseBone,
    parent_pose_bone: Optional[bpy.types.PoseBone] = None,
) -> Matrix:
    """Return a bone's rest transform relative to its direct or sparse parent rest transform."""
    rest_world = remove_bone_axis_adapter(pose_bone.bone.matrix_local, pose_bone.id_data)
    rest_local = rest_world
    if parent_pose_bone is None:
        parent_pose_bone = pose_bone.parent
    if parent_pose_bone:
        parent_rest_world = remove_bone_axis_adapter(parent_pose_bone.bone.matrix_local, pose_bone.id_data)
        rest_local = parent_rest_world.inverted() @ rest_world
    return rest_local


def get_armature_space_pose_matrix(armature: bpy.types.Object, pose_bone: bpy.types.PoseBone) -> Matrix:
    """Return a pose bone matrix in armature space."""
    return remove_bone_axis_adapter(armature.matrix_world.inverted() @ pose_bone.matrix, armature)


def build_import_bone_mapping(
    anim_bone_names: List[str],
    armature: bpy.types.Object,
    parent_indices: Optional[List[int]] = None,
    selected_bone_names: Optional[set[str]] = None,
) -> ImportBoneMapping:
    """Resolve animation bone indices against an armature and optional selected-bone filter."""
    mapping = ImportBoneMapping()
    selected_name_filter = {name.lower() for name in selected_bone_names} if selected_bone_names else None
    bone_name_to_anim_idx = {bone_name.lower(): index for index, bone_name in enumerate(anim_bone_names)}

    for index, bone_name in enumerate(anim_bone_names):
        pose_bone = find_pose_bone_case_insensitive(armature, bone_name)
        if pose_bone is None:
            mapping.missing_bones.append(bone_name)
            continue

        mapping.matched_pose_bones[index] = pose_bone

    for index, pose_bone in mapping.matched_pose_bones.items():
        sparse_parent_index = None
        if parent_indices and index < len(parent_indices):
            parent_index = parent_indices[index]
            if 0 <= parent_index < len(anim_bone_names):
                sparse_parent_index = parent_index
                mapping.parent_anim_idx[index] = parent_index
        elif pose_bone.parent:
            parent_name = pose_bone.parent.name.lower()
            if parent_name in bone_name_to_anim_idx:
                sparse_parent_index = bone_name_to_anim_idx[parent_name]
                mapping.parent_anim_idx[index] = sparse_parent_index

        sparse_parent_bone = mapping.matched_pose_bones.get(sparse_parent_index) if sparse_parent_index is not None else None
        mapping.rest_local_by_anim_idx[index] = get_rest_local_matrix(pose_bone, parent_pose_bone=sparse_parent_bone)

        if selected_name_filter is not None and pose_bone.name.lower() not in selected_name_filter:
            continue

        mapping.bone_mapping[index] = pose_bone

    return mapping


def ensure_import_action(
    armature: bpy.types.Object,
    action_name: str,
    selected_bone_names: Optional[set[str]] = None,
) -> bpy.types.Action:
    """Return the action to write into, preserving the current action for selected-bone imports."""
    if armature.animation_data is None:
        armature.animation_data_create()

    current_action = armature.animation_data.action
    if selected_bone_names and current_action is not None:
        return current_action

    action = bpy.data.actions.new(name=action_name)
    armature.animation_data.action = action
    return action


def clear_action_curves_for_bones(action: bpy.types.Action, bone_names: set[str]):
    """Remove existing FCurves for a set of bones from an action."""
    if action is None or not bone_names:
        return

    bone_names_lower = {bone_name.lower() for bone_name in bone_names}
    curves_to_remove = []
    for fcurve in iter_action_fcurves(action):
        data_path = fcurve.data_path or ""
        if not data_path.startswith('pose.bones["'):
            continue
        parts = data_path.split('"')
        if len(parts) < 2:
            continue
        if parts[1].lower() in bone_names_lower:
            curves_to_remove.append(fcurve)

    for fcurve in curves_to_remove:
        remove_action_fcurve(action, fcurve)


def get_current_world_matrices_by_anim_idx(
    armature: bpy.types.Object,
    mapping: ImportBoneMapping,
) -> Dict[int, Matrix]:
    """Capture the current armature-space pose matrices for matched animation bones."""
    current_world_by_anim_idx: Dict[int, Matrix] = {}
    for bone_idx, pose_bone in mapping.matched_pose_bones.items():
        current_world_by_anim_idx[bone_idx] = get_armature_space_pose_matrix(armature, pose_bone)
    return current_world_by_anim_idx


def get_runtime_world_matrix(
    bone_idx: int,
    frame_data: List[Matrix],
    mapping: ImportBoneMapping,
    runtime_world_cache: Dict[int, Matrix],
    current_world_by_anim_idx: Optional[Dict[int, Matrix]] = None,
) -> Optional[Matrix]:
    """Return the world matrix a bone will have under a partial import mapping."""
    if bone_idx in runtime_world_cache:
        return runtime_world_cache[bone_idx]

    if current_world_by_anim_idx and bone_idx in current_world_by_anim_idx and bone_idx not in mapping.bone_mapping:
        world_matrix = current_world_by_anim_idx[bone_idx]
        runtime_world_cache[bone_idx] = world_matrix
        return world_matrix

    parent_idx = mapping.parent_anim_idx.get(bone_idx)
    parent_world = Matrix.Identity(4)
    if parent_idx is not None:
        parent_matrix = get_runtime_world_matrix(
            parent_idx,
            frame_data,
            mapping,
            runtime_world_cache,
            current_world_by_anim_idx=current_world_by_anim_idx,
        )
        if parent_matrix is None:
            return None
        parent_world = parent_matrix

    if bone_idx in mapping.bone_mapping:
        world_matrix = frame_data[bone_idx]
    else:
        rest_local = mapping.rest_local_by_anim_idx.get(bone_idx)
        if rest_local is None:
            return None
        world_matrix = parent_world @ rest_local

    runtime_world_cache[bone_idx] = world_matrix
    return world_matrix


def compute_import_local_matrix(
    bone_idx: int,
    frame_data: List[Matrix],
    mapping: ImportBoneMapping,
    runtime_world_cache: Dict[int, Matrix],
    current_world_by_anim_idx: Optional[Dict[int, Matrix]] = None,
) -> Optional[Matrix]:
    """Return a bone's local matrix under the current partial import mapping."""
    parent_world = Matrix.Identity(4)
    parent_idx = mapping.parent_anim_idx.get(bone_idx)
    if parent_idx is not None:
        parent_matrix = get_runtime_world_matrix(
            parent_idx,
            frame_data,
            mapping,
            runtime_world_cache,
            current_world_by_anim_idx=current_world_by_anim_idx,
        )
        if parent_matrix is None:
            return None
        parent_world = parent_matrix

    return parent_world.inverted() @ frame_data[bone_idx]


__all__ = [
    "ImportBoneMapping",
    "build_import_bone_mapping",
    "clear_action_curves_for_bones",
    "compute_import_local_matrix",
    "ensure_import_action",
    "find_pose_bone_case_insensitive",
    "get_armature_space_pose_matrix",
    "get_current_world_matrices_by_anim_idx",
    "get_rest_local_matrix",
    "get_runtime_world_matrix",
    "resolve_batch_relative_animation_path",
    "get_selected_armature_bone_names",
]