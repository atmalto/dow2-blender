from typing import TYPE_CHECKING, Optional

import bpy

from ..utils import blender_to_dx_matrix
from .skeleton_space import ROOT_BONE_NAME, get_export_local_matrix, get_export_node_world_matrix, is_model_root_name

if TYPE_CHECKING:
    from .exporter import DoW2ModelExporter


def get_or_create_skeleton_root(exporter: "DoW2ModelExporter") -> Optional[bpy.types.Object]:
    """Get or create skeleton root matching MaxScript GetSkeletonRoot."""
    root = bpy.data.objects.get("skeleton_root")
    if root:
        return root

    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            return obj

    # TODO: Deprecate the object/empty skeleton fallback once model export is fully armature-backed.
    root_bones = []
    for obj in bpy.data.objects:
        if obj.type == "EMPTY" and obj.get("dow2_is_bone"):
            if obj.parent is None or not obj.parent.get("dow2_is_bone"):
                root_bones.append(obj)

    if root_bones:
        print("Creating skeleton_root for orphan bones...")
        root = bpy.data.objects.new("skeleton_root", None)
        root.empty_display_type = "CUBE"
        root.empty_display_size = 0.5
        root.location = (0, 0, 0)
        root["dow2_is_bone"] = True

        bpy.context.scene.collection.objects.link(root)

        for bone in root_bones:
            bone.parent = root

        return root

    return None


def get_skeleton_root(exporter: "DoW2ModelExporter") -> Optional[bpy.types.Object]:
    """Get skeleton root for backwards compatibility."""
    # TODO: Deprecate this compatibility wrapper after callers switch to the normalized root-space path.
    return get_or_create_skeleton_root(exporter)


def export_bones(exporter: "DoW2ModelExporter"):
    """Export bones matching MaxScript ExportBones."""
    root = exporter._get_skeleton_root()
    if not root:
        print("No skeleton root found")
        return

    print("Exporting bones...")

    exporter.bones = []
    exporter.bone_names = []

    if root.type == "ARMATURE":
        exporter._collect_armature_bones(root)
    else:
        # TODO: Deprecate object-based skeleton export once legacy empty-bone scenes are migrated.
        exporter._collect_bone_hierarchy(root, -1)

    if not exporter.bones:
        print("No bones found")
        return

    skel_header_pos = exporter.writer.file.tell()
    skel_data_pos = exporter.writer.write_chunk_header("FOLD", "SKEL", 3, 0, None, 0)

    exporter.writer.write_chunk_header("DATA", "INFO", 1, 4, None, -1)
    exporter.writer.write_long(len(exporter.bones))

    for index, (bone, parent_idx) in enumerate(exporter.bones):
        bone_name = exporter.bone_names[index]
        parent_bone = exporter.bones[parent_idx][0] if 0 <= parent_idx < len(exporter.bones) else None

        exporter.writer.write_chunk_header("DATA", "BONE", 7, 64, bone_name, 1)
        exporter.writer.write_long(parent_idx, unsigned=False)
        exporter.writer.write_long(0xFFFFFFFF)

        local_mat = get_export_local_matrix(
            bone,
            parent_bone,
            root if root.type == "ARMATURE" else None,
        )

        dx_matrix = blender_to_dx_matrix(local_mat)
        exporter.writer.write_matrix(dx_matrix)

        exporter.writer.write_long(0)
        exporter.writer.write_long(0)

        print(f"Exported '{bone_name}' bone")

    exporter.writer.update_chunk_size(skel_header_pos, skel_data_pos)


def collect_armature_bones(exporter: "DoW2ModelExporter", armature_obj: bpy.types.Object):
    """Collect bones from an armature into a flat list with parent indices."""
    arm = armature_obj.data
    root_bones = [bone for bone in arm.bones if bone.parent is None]

    exporter.bones.append((armature_obj, -1))
    exporter.bone_names.append(ROOT_BONE_NAME)

    for root_bone in root_bones:
        if is_model_root_name(root_bone.name):
            for child in root_bone.children:
                exporter._add_bone_recursive(child, 0, armature_obj)
            continue
        exporter._add_bone_recursive(root_bone, 0, armature_obj)


def add_bone_recursive(exporter: "DoW2ModelExporter", bone, parent_idx: int, armature_obj: bpy.types.Object):
    """Recursively add an armature bone and its children."""
    index = len(exporter.bones)
    if exporter.options.export_rest_pose:
        exporter.bones.append((bone, parent_idx))
    else:
        pose_bone = armature_obj.pose.bones.get(bone.name)
        exporter.bones.append((pose_bone, parent_idx))
    exporter.bone_names.append(bone.name)

    for child in bone.children:
        exporter._add_bone_recursive(child, index, armature_obj)


def collect_bone_hierarchy(exporter: "DoW2ModelExporter", obj: bpy.types.Object, parent_idx: int):
    """Collect object-based bone hierarchy."""
    index = len(exporter.bones)
    exporter.bones.append((obj, parent_idx))
    exporter.bone_names.append(obj.name)

    for child in obj.children:
        if child.type in ["EMPTY", "ARMATURE"] or getattr(child, "bone_enable", False):
            exporter._collect_bone_hierarchy(child, index)


def export_markers(exporter: "DoW2ModelExporter"):
    """Export markers matching MaxScript ExportMarkers."""
    print("Exporting markers...")

    markers = []
    for obj in bpy.data.objects:
        if obj.type == "EMPTY" and not obj.get("bone_enable", False):
            if obj.name != "skeleton_root" and obj.name not in exporter.bone_names:
                markers.append(obj)

    mrks_header_pos = exporter.writer.file.tell()
    mrks_data_pos = exporter.writer.write_chunk_header("DATA", "MRKS", 1, 0, None, -1)

    exporter.writer.write_long(len(markers))

    for marker in markers:
        exporter.writer.write_long(len(marker.name))
        exporter.writer.write_str(marker.name)

        parent_name = ""
        if marker.parent and marker.parent_type == "BONE" and marker.parent_bone:
            parent_name = marker.parent_bone
            if exporter.options.export_rest_pose:
                parent_bone = marker.parent.data.bones.get(marker.parent_bone)
            else:
                parent_bone = marker.parent.pose.bones.get(marker.parent_bone)

            if parent_bone is not None:
                parent_world = get_export_node_world_matrix(parent_bone, marker.parent)
                local_mat = parent_world.inverted() @ marker.matrix_world
            else:
                local_mat = marker.matrix_world
        elif marker.parent:
            parent_name = marker.parent.name
            local_mat = marker.parent.matrix_world.inverted() @ marker.matrix_world
        else:
            local_mat = marker.matrix_world

        exporter.writer.write_long(len(parent_name))
        if parent_name:
            exporter.writer.write_str(parent_name)

        rot_mat = local_mat.to_3x3().to_4x4()
        rot_mat.translation = local_mat.translation
        dx_matrix = blender_to_dx_matrix(rot_mat)
        exporter.writer.write_matrix(dx_matrix)

        params = []
        for key, value in marker.items():
            if not key.startswith("_"):
                params.append((key, str(value)))

        exporter.writer.write_long(len(params))
        for key, value in params:
            exporter.writer.write_long(len(key))
            exporter.writer.write_str(key)
            exporter.writer.write_long(11)
            exporter.writer.write_long(len(value))
            exporter.writer.write_str(value)

        print(f"Exported '{marker.name}' marker")

    exporter.writer.update_chunk_size(mrks_header_pos, mrks_data_pos)


__all__ = [
    "add_bone_recursive",
    "collect_armature_bones",
    "collect_bone_hierarchy",
    "export_bones",
    "export_markers",
    "get_or_create_skeleton_root",
    "get_skeleton_root",
]