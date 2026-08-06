from __future__ import annotations

from typing import TYPE_CHECKING, List

import bpy
from mathutils import Vector

from ..chunk_lib import RelicChunk, find_chunks, get_chunk
from ..utils import dx_to_blender_matrix, find_object_by_name, link_object_to_collection
from .import_types import ImportBone
from .skeleton_space import (
    apply_bone_axis_adapter,
    armature_uses_bone_axis_adapter,
    compose_import_world_matrix,
    mark_armature_bone_axis_adapter,
    remove_bone_axis_adapter,
    take_model_root_proxy_matrix,
)

if TYPE_CHECKING:
    from .importer import DoW2ModelImporter


def _apply_legacy_bone_length(edit_bone: bpy.types.EditBone):
    if len(edit_bone.children) != 1:
        return

    new_length = (edit_bone.children[0].head - edit_bone.head).length
    if new_length > 1e-3:
        edit_bone.length = new_length


def import_bones(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import skeleton from the SKEL chunk."""

    skel_chunk = get_chunk("SKEL", chunks)
    if not skel_chunk:
        print("No skeleton found")
        return

    print("Importing bones...")
    info_chunk = get_chunk("INFO", skel_chunk.children)
    if info_chunk:
        importer.reader.seek_chunk(info_chunk)
        num_bones = importer.reader.read_long()
        print(f"  Skeleton has {num_bones} bones")

    bone_chunks = find_chunks("BONE", skel_chunk.children)
    for index, bone_chunk in enumerate(bone_chunks):
        importer.reader.seek_chunk(bone_chunk)

        bone = ImportBone()
        bone.name = bone_chunk.name or f"Bone_{index}"
        bone.parent_index = importer.reader.read_long(unsigned=False)
        importer.reader.read_long()
        bone.matrix = dx_to_blender_matrix(importer.reader.read_matrix())

        importer.bone_map[bone.name] = len(importer.bones)
        importer.bones.append(bone)

    if not importer.bones:
        return

    root_proxy_matrix = take_model_root_proxy_matrix(importer.bones)

    for bone in importer.bones:
        if 0 <= bone.parent_index < len(importer.bones):
            bone.import_transform = compose_import_world_matrix(
                bone.matrix,
                importer.bones[bone.parent_index].import_transform,
            )
        else:
            bone.import_transform = bone.matrix.copy()

        bone.transform = bone.import_transform.copy()

    armature_name = "DoW2_Armature"
    existing_armature = find_object_by_name(armature_name, "ARMATURE") if importer.options.merge else None

    if existing_armature:
        importer.armature = existing_armature
        armature_data = existing_armature.data
        link_object_to_collection(importer.armature, bpy.context.scene.collection)
    else:
        armature_data = bpy.data.armatures.new(armature_name)
        importer.armature = bpy.data.objects.new(armature_name, armature_data)
        bpy.context.scene.collection.objects.link(importer.armature)
        if root_proxy_matrix is not None:
            importer.armature.matrix_world = root_proxy_matrix.copy()
        mark_armature_bone_axis_adapter(armature_data)

    use_bone_axis_adapter = armature_uses_bone_axis_adapter(armature_data)

    existing_world_transforms = {}
    if existing_armature:
        for bone in importer.bones:
            existing_bone = armature_data.bones.get(bone.name)
            if existing_bone is not None:
                existing_world = importer.armature.matrix_world @ existing_bone.matrix_local
                if use_bone_axis_adapter:
                    existing_world = remove_bone_axis_adapter(existing_world)
                existing_world_transforms[bone.name] = existing_world

    for bone in importer.bones:
        if bone.name in existing_world_transforms:
            bone.transform = existing_world_transforms[bone.name].copy()
        elif 0 <= bone.parent_index < len(importer.bones):
            bone.transform = compose_import_world_matrix(
                bone.matrix,
                importer.bones[bone.parent_index].transform,
            )
        else:
            bone.transform = bone.import_transform.copy()

    bpy.context.view_layer.objects.active = importer.armature
    bpy.ops.object.mode_set(mode="EDIT")

    existing_names = set(armature_data.edit_bones.keys()) if existing_armature else set()

    added_bones = 0
    edit_bones = []
    for bone in importer.bones:
        if bone.name in armature_data.edit_bones:
            edit_bone = armature_data.edit_bones[bone.name]
        else:
            edit_bone = armature_data.edit_bones.new(bone.name)
            edit_bone.head = (0.0, 0.0, 0.0)
            edit_bone.tail = (0.5, 0.0, 0.0)
            edit_bone.inherit_scale = 'NONE'
            added_bones += 1
        edit_bones.append(edit_bone)

    for index, bone in enumerate(importer.bones):
        edit_bone = edit_bones[index]
        parent_target = edit_bones[bone.parent_index] if 0 <= bone.parent_index < len(edit_bones) else None
        is_new_bone = bone.name not in existing_names

        if is_new_bone:
            edit_bone.parent = parent_target
        elif edit_bone.parent is None and parent_target:
            edit_bone.parent = parent_target

        if is_new_bone:
            world_matrix = bone.transform.copy()
            if use_bone_axis_adapter:
                world_matrix = apply_bone_axis_adapter(world_matrix)
            edit_bone.matrix = world_matrix

    for bone in edit_bones:
        _apply_legacy_bone_length(bone)

    bpy.ops.object.mode_set(mode="OBJECT")
    for bone in importer.bones:
        armature_bone = armature_data.bones.get(bone.name)
        if armature_bone is not None:
            world_matrix = importer.armature.matrix_world @ armature_bone.matrix_local
            if use_bone_axis_adapter:
                world_matrix = remove_bone_axis_adapter(world_matrix)
            bone.transform = world_matrix

    if existing_armature:
        print(f"  Reused armature '{armature_name}', added {added_bones} bones (total {len(armature_data.bones)})")
    else:
        print(f"  Created {len(importer.bones)} bones")

    if hasattr(bpy.context.scene, "dow2_show_bone_marker_names"):
        armature_data.show_names = bool(bpy.context.scene.dow2_show_bone_marker_names)


def import_markers(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import markers from the MRKS chunk."""

    mrks_chunk = get_chunk("MRKS", chunks)
    if not mrks_chunk:
        print("No markers found")
        return

    print("Importing markers...")
    importer.reader.seek_chunk(mrks_chunk)
    num_markers = importer.reader.read_long()
    markers_created = []

    for _ in range(num_markers):
        name_len = importer.reader.read_long()
        name = importer.reader.read_str(name_len) if name_len > 0 else "Marker"

        parent_len = importer.reader.read_long()
        parent_name = importer.reader.read_str(parent_len) if parent_len > 0 else ""

        matrix = importer.reader.read_matrix()

        params = {}
        num_params = importer.reader.read_long()
        for _ in range(num_params):
            key_len = importer.reader.read_long()
            key = importer.reader.read_str(key_len) if key_len > 0 else ""
            importer.reader.read_long()
            value_len = importer.reader.read_long()
            value = importer.reader.read_str(value_len) if value_len > 0 else ""
            if key:
                params[key] = value

        empty = find_object_by_name(name, "EMPTY") if importer.options.merge else None
        if empty is None:
            empty = bpy.data.objects.new(name, None)
        empty.empty_display_type = "ARROWS"
        empty.empty_display_size = 0.1
        if hasattr(bpy.context.scene, "dow2_show_bone_marker_names"):
            empty.show_name = bool(bpy.context.scene.dow2_show_bone_marker_names)
        link_object_to_collection(empty, bpy.context.collection or bpy.context.scene.collection)

        marker_matrix = dx_to_blender_matrix(matrix)
        empty.parent = None
        empty.parent_type = "OBJECT"
        empty.parent_bone = ""

        if parent_name:
            if parent_name in importer.bone_map and importer.armature:
                bone_world = importer.bones[importer.bone_map[parent_name]].transform @ marker_matrix
                empty.parent = importer.armature
                empty.parent_type = "BONE"
                empty.parent_bone = parent_name
                empty.matrix_world = bone_world
            else:
                for marker in markers_created:
                    if marker.name == parent_name:
                        empty.parent = marker
                        empty.matrix_local = marker_matrix
                        break
                else:
                    if importer.bones and parent_name in importer.bone_map:
                        parent_bone = importer.bones[importer.bone_map[parent_name]]
                        empty.matrix_world = parent_bone.transform @ marker_matrix
                    else:
                        empty.matrix_world = marker_matrix
        else:
            empty.matrix_world = marker_matrix

        for key, value in params.items():
            empty[key] = value

        markers_created.append(empty)
        print(f"  Imported marker: {name}")