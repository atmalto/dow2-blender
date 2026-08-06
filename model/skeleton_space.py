from __future__ import annotations

import math
from typing import Optional

import bpy
from mathutils import Matrix


ROOT_BONE_NAME = "skeleton_root"
BONE_AXIS_ADAPTER_PROP = "dow2_use_bone_axis_adapter"
BONE_AXIS_ADAPTER = Matrix.Rotation(math.radians(-90.0), 4, 'Z')
BONE_AXIS_ADAPTER_INV = BONE_AXIS_ADAPTER.inverted()


def is_model_root_name(name: str) -> bool:
    return name.lower() == ROOT_BONE_NAME


def armature_uses_bone_axis_adapter(armature_obj_or_data) -> bool:
    if isinstance(armature_obj_or_data, bpy.types.Object):
        armature_data = armature_obj_or_data.data if armature_obj_or_data.type == 'ARMATURE' else None
    else:
        armature_data = armature_obj_or_data

    if armature_data is None:
        return False
    return bool(armature_data.get(BONE_AXIS_ADAPTER_PROP, False))


def mark_armature_bone_axis_adapter(armature_obj_or_data) -> None:
    if isinstance(armature_obj_or_data, bpy.types.Object):
        armature_data = armature_obj_or_data.data if armature_obj_or_data.type == 'ARMATURE' else None
    else:
        armature_data = armature_obj_or_data

    if armature_data is not None:
        armature_data[BONE_AXIS_ADAPTER_PROP] = True


def apply_bone_axis_adapter(matrix: Matrix) -> Matrix:
    return matrix @ BONE_AXIS_ADAPTER


def remove_bone_axis_adapter(matrix: Matrix, armature_obj_or_data=None) -> Matrix:
    if armature_obj_or_data is not None and not armature_uses_bone_axis_adapter(armature_obj_or_data):
        return matrix.copy()
    return matrix @ BONE_AXIS_ADAPTER_INV


def get_export_node_world_matrix(node, armature_obj: Optional[bpy.types.Object] = None) -> Matrix:
    if isinstance(node, bpy.types.Object):
        return node.matrix_world.copy()

    if armature_obj is None:
        raise ValueError("armature_obj is required for armature bone export")

    if isinstance(node, bpy.types.PoseBone):
        matrix = armature_obj.matrix_world @ node.matrix
        if armature_uses_bone_axis_adapter(armature_obj):
            return remove_bone_axis_adapter(matrix)
        return matrix

    if isinstance(node, bpy.types.Bone):
        matrix = armature_obj.matrix_world @ node.matrix_local
        if armature_uses_bone_axis_adapter(armature_obj):
            return remove_bone_axis_adapter(matrix)
        return matrix

    if hasattr(node, "matrix_world"):
        return node.matrix_world.copy()

    raise TypeError(f"Unsupported export node type: {type(node)!r}")


def get_export_local_matrix(node, parent_node=None, armature_obj: Optional[bpy.types.Object] = None) -> Matrix:
    node_world = get_export_node_world_matrix(node, armature_obj)
    if parent_node is None:
        return node_world

    parent_world = get_export_node_world_matrix(parent_node, armature_obj)
    return parent_world.inverted() @ node_world


def compose_import_world_matrix(local_matrix: Matrix, parent_world_matrix: Optional[Matrix] = None) -> Matrix:
    if parent_world_matrix is None:
        return local_matrix.copy()
    return parent_world_matrix @ local_matrix


def take_model_root_proxy_matrix(bones) -> Optional[Matrix]:
    for bone in bones:
        if bone.parent_index < 0 and is_model_root_name(bone.name):
            root_matrix = bone.matrix.copy()
            bone.matrix = Matrix.Identity(4)
            bone.import_transform = Matrix.Identity(4)
            bone.transform = Matrix.Identity(4)
            return root_matrix
    return None


__all__ = [
    "apply_bone_axis_adapter",
    "armature_uses_bone_axis_adapter",
    "BONE_AXIS_ADAPTER",
    "BONE_AXIS_ADAPTER_INV",
    "BONE_AXIS_ADAPTER_PROP",
    "compose_import_world_matrix",
    "get_export_local_matrix",
    "get_export_node_world_matrix",
    "mark_armature_bone_axis_adapter",
    "remove_bone_axis_adapter",
    "ROOT_BONE_NAME",
    "is_model_root_name",
    "take_model_root_proxy_matrix",
]