"""Import bounding volumes from BVOL chunks inside a sub-mesh TRIM.

Matching MaxScript ST2Import ImportBoundingVolume / ImportBoundingVolumes.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

import bpy
from mathutils import Vector

from ..chunk_lib import RelicChunk, get_chunk
from .importer_utils import dx_to_blender_position

if TYPE_CHECKING:
    from .importer import DoW2ModelImporter


BVOL_COLOR = (0.2, 1.0, 0.2, 1.0)


def import_bounding_volumes(
    importer: "DoW2ModelImporter",
    mesh_chunk: RelicChunk,
    group_name: str,
    lod_level: int,
    submesh_name: str,
    skin_bone_names: List[str],
    target_collection: "bpy.types.Collection | None" = None,
    material_name: str = "",
):
    """Import BVOL chunks from a sub-mesh's TRIM.

    The first BVOL is the mesh-level AABB. Subsequent ones correspond
    to each skin bone in index order. Creates green wire-cube objects.
    """
    trim_chunk = get_chunk("TRIM", mesh_chunk.children)
    if not trim_chunk:
        return

    bvol_chunks = [
        c for c in trim_chunk.children
        if c.chunk_kind == "DATA" and c.chunk_type == "BVOL"
    ]
    if not bvol_chunks:
        return

    for idx, bvol_chunk in enumerate(bvol_chunks):
        importer.reader.seek_chunk(bvol_chunk)

        importer.reader.read_byte()

        center_dx = Vector((
            importer.reader.read_float(),
            importer.reader.read_float(),
            importer.reader.read_float(),
        ))
        center = dx_to_blender_position(center_dx)

        hx = importer.reader.read_float()
        hz = importer.reader.read_float()
        hy = importer.reader.read_float()
        half_extents = Vector((hx, hy, hz))

        for _ in range(9):
            importer.reader.read_float()

        bvol_type = "mesh" if idx == 0 else "bone"
        bone_name = ""
        if idx == 0:
            obj_name = "BVOL_{}_mesh".format(submesh_name)
        else:
            bone_idx = idx - 1
            if bone_idx < len(skin_bone_names):
                bone_name = skin_bone_names[bone_idx]
                obj_name = "BVOL_{}_{}".format(submesh_name, bone_name)
            else:
                obj_name = "BVOL_{}_bone_{}".format(submesh_name, idx)

        _create_bounding_volume_object(
            obj_name, center, half_extents, bvol_type, submesh_name, bone_name,
            material_name,
            target_collection,
        )


def _create_bounding_volume_object(
    name: str,
    location: Vector,
    scale: Vector,
    bvol_type: str,
    submesh_name: str,
    bone_name: str,
    material_name: str = "",
    target_collection=None,
):
    """Create a green wire cube representing a single bounding volume."""
    mesh = bpy.data.meshes.new(name + "::Mesh")
    mesh.from_pydata(
        [
            (-1.0, -1.0, -1.0),
            (-1.0, -1.0, 1.0),
            (-1.0, 1.0, -1.0),
            (-1.0, 1.0, 1.0),
            (1.0, -1.0, -1.0),
            (1.0, -1.0, 1.0),
            (1.0, 1.0, -1.0),
            (1.0, 1.0, 1.0),
        ],
        [
            (0, 1), (0, 2), (0, 4),
            (1, 3), (1, 5),
            (2, 3), (2, 6),
            (3, 7),
            (4, 5), (4, 6),
            (5, 7),
            (6, 7),
        ],
        [],
    )
    obj = bpy.data.objects.new(name, mesh)
    if target_collection is not None:
        target_collection.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)
    obj.display_type = "WIRE"
    obj.show_in_front = True
    obj.color = BVOL_COLOR
    obj.show_wire = True
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = scale
    obj["dow2_bvol_type"] = bvol_type
    obj["dow2_bvol_submesh"] = submesh_name
    if material_name:
        obj["dow2_bvol_material"] = material_name
    if bone_name:
        obj["dow2_bvol_bone_name"] = bone_name