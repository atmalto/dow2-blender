from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import bmesh
import bpy
from mathutils import Matrix, Vector

from ..chunk_lib import RelicChunk, find_chunks_direct, get_chunk
from ..utils import dx_to_blender_matrix, find_object_by_name, link_object_to_collection, unpack_vector
from .import_types import ImportVertex, SkinBone, VertexElement
from .importer_utils import bytes_to_weights, dx_to_blender_normal, dx_to_blender_position
from .skeleton_space import remove_bone_axis_adapter

if TYPE_CHECKING:
    from .importer import DoW2ModelImporter


def import_meshes(importer: DoW2ModelImporter, chunks: List[RelicChunk]):
    """Import all meshes from the MESH hierarchy."""

    print("Importing meshes...")
    mesh_fold = get_chunk("MESH", chunks)
    if not mesh_fold:
        print("No MESH chunk found")
        return

    mgrp_chunk = get_chunk("MGRP", mesh_fold.children)
    if not mgrp_chunk:
        print("No MGRP chunk found")
        return

    mesh_groups = find_chunks_direct("MESH", mgrp_chunk.children)
    importer._group_collections = {}
    importer._lod_collections = {}

    for mesh_group in mesh_groups:
        group_name = mesh_group.name or "default"
        print(f"  Mesh group: {group_name}")

        group_collection = None
        if importer.options.group_meshes:
            group_collection = get_or_create_group_collection(importer, group_name)

        imdg = get_chunk("IMDG", mesh_group.children)
        if not imdg:
            continue

        for lod_mesh in find_chunks_direct("MESH", imdg.children):
            imod = get_chunk("IMOD", lod_mesh.children)
            if not imod:
                continue

            if imod.children and imod.children[0].chunk_type == "DATA":
                importer.reader.seek_chunk(imod.children[0])
                lod_level = importer.reader.read_long()
            else:
                lod_level = 0

            print(f"    LOD {lod_level}")

            lod_collection = None
            if importer.options.group_meshes and group_collection:
                lod_collection = get_or_create_lod_collection(importer, group_name, lod_level, group_collection)

            for sub_mesh in find_chunks_direct("MESH", imod.children):
                import_submesh(importer, sub_mesh, group_name, lod_level, lod_collection)


def get_or_create_group_collection(importer: DoW2ModelImporter, group_name: str) -> bpy.types.Collection:
    if group_name in importer._group_collections:
        return importer._group_collections[group_name]

    if importer.options.merge and group_name in bpy.data.collections:
        collection = bpy.data.collections[group_name]
    else:
        collection = bpy.data.collections.new(group_name)
        bpy.context.scene.collection.children.link(collection)

    importer._group_collections[group_name] = collection
    return collection


def get_or_create_lod_collection(
    importer: DoW2ModelImporter,
    group_name: str,
    lod_level: int,
    parent_collection: bpy.types.Collection,
) -> bpy.types.Collection:
    lod_name = f"lod{lod_level}"
    collection_key = f"{group_name}:{lod_name}"

    if collection_key in importer._lod_collections:
        return importer._lod_collections[collection_key]

    existing = None
    if importer.options.merge:
        for child in parent_collection.children:
            if child.name == lod_name:
                existing = child
                break

    if existing:
        collection = existing
    else:
        collection = bpy.data.collections.new(lod_name)
        parent_collection.children.link(collection)

    importer._lod_collections[collection_key] = collection
    return collection


def import_submesh(
    importer: DoW2ModelImporter,
    mesh_chunk: RelicChunk,
    group_name: str,
    lod_level: int,
    lod_collection: Optional[bpy.types.Collection] = None,
):
    """Import a single submesh with all vertex data and skin weights."""

    mesh_name = mesh_chunk.name or f"Mesh_{len(bpy.data.meshes)}"
    importer._current_lod_collection = lod_collection

    trim_chunk = get_chunk("TRIM", mesh_chunk.children)
    if not trim_chunk:
        return

    data_chunk = get_chunk("DATA", trim_chunk.children)
    if not data_chunk:
        return

    importer.reader.seek_chunk(data_chunk)

    num_elements = importer.reader.read_long()
    elements = []
    has_uv2 = False
    has_vertex_color = False

    for _ in range(num_elements):
        element = VertexElement()
        element.element_type = importer.reader.read_long()
        element.version = importer.reader.read_long()
        element.data_type = importer.reader.read_long()
        elements.append(element)

        if element.element_type == 9:
            has_uv2 = True
        if element.element_type == 6:
            has_vertex_color = True

    num_verts = importer.reader.read_long()
    importer.reader.read_long()

    vertices = []
    for _ in range(num_verts):
        vertex = ImportVertex()

        for element in elements:
            if element.element_type == 0:
                vertex.position = Vector(
                    (
                        importer.reader.read_float(),
                        importer.reader.read_float(),
                        importer.reader.read_float(),
                    )
                )
            elif element.element_type == 1:
                vertex.blend_indices = [importer.reader.read_byte() for _ in range(4)]
            elif element.element_type == 2:
                bytes_data = [importer.reader.read_byte() for _ in range(4)]
                vertex.blend_weights = bytes_to_weights(bytes_data)
            elif element.element_type == 3:
                vertex.normal = _read_vector_element(importer, element)
            elif element.element_type == 4:
                vertex.binormal = _read_vector_element(importer, element)
            elif element.element_type == 5:
                vertex.tangent = _read_vector_element(importer, element)
            elif element.element_type == 6:
                vertex.color = (
                    importer.reader.read_byte() / 255.0,
                    importer.reader.read_byte() / 255.0,
                    importer.reader.read_byte() / 255.0,
                    importer.reader.read_byte() / 255.0,
                )
            elif element.element_type == 8:
                vertex.uv[0] = (importer.reader.read_float(), -importer.reader.read_float())
            elif element.element_type == 9:
                vertex.uv[1] = (importer.reader.read_float(), -importer.reader.read_float())
            else:
                _skip_unknown_vertex_element(importer, element)

        vertices.append(vertex)

    importer.reader.read_long()
    num_indices = importer.reader.read_long()
    importer.reader.read_long()
    importer.reader.read_long()

    indices = [importer.reader.read_short() for _ in range(num_indices)]
    faces = [(indices[index], indices[index + 2], indices[index + 1]) for index in range(0, len(indices), 3)]

    mat_name_len = importer.reader.read_long()
    mat_name = importer.reader.read_str(mat_name_len) if mat_name_len > 0 else ""

    skin_bones = []
    num_skin_bones = importer.reader.read_long()
    for _ in range(num_skin_bones):
        skin_bone = SkinBone()
        skin_bone.world_matrix = importer.reader.read_matrix()
        skin_bone.inverse_matrix = importer.reader.read_matrix()
        name_len = importer.reader.read_long()
        skin_bone.name = importer.reader.read_str(name_len) if name_len > 0 else ""
        skin_bones.append(skin_bone)

    importer.reader.read_long()
    importer.reader.read_long()

    create_blender_mesh(
        importer,
        mesh_name,
        vertices,
        faces,
        mat_name,
        skin_bones,
        has_uv2,
        has_vertex_color,
        group_name,
        lod_level,
    )

    if importer.options.import_bounding_volumes:
        from .importer_bvol import import_bounding_volumes

        bone_names = [b.name for b in skin_bones]
        import_bounding_volumes(
            importer, mesh_chunk, group_name, lod_level, mesh_name, bone_names,
            lod_collection, mat_name,
        )


def create_blender_mesh(
    importer: DoW2ModelImporter,
    name: str,
    vertices: List[ImportVertex],
    faces: List[Tuple[int, int, int]],
    mat_name: str,
    skin_bones: List[SkinBone],
    has_uv2: bool,
    has_vertex_color: bool,
    group_name: str,
    lod_level: int,
):
    """Create the Blender mesh object with all imported attributes."""

    lod_collection = getattr(importer, "_current_lod_collection", None)
    target_collection = lod_collection or bpy.context.collection or bpy.context.scene.collection

    existing_obj = find_object_by_name(name, "MESH") if importer.options.merge else None
    if existing_obj:
        obj = existing_obj
        mesh = existing_obj.data
        if hasattr(mesh, "clear_geometry"):
            mesh.clear_geometry()
        else:
            mesh.vertices.clear()
            mesh.edges.clear()
            mesh.polygons.clear()
        for modifier in [item for item in obj.modifiers if item.type == "ARMATURE"]:
            obj.modifiers.remove(modifier)
        link_object_to_collection(obj, target_collection)
        obj.data.materials.clear()
        if obj.vertex_groups:
            obj.vertex_groups.clear()
    else:
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        link_object_to_collection(obj, target_collection)

    obj.location = (0.0, 0.0, 0.0)
    obj.rotation_euler = (0.0, 0.0, 0.0)
    obj.scale = (1.0, 1.0, 1.0)

    merged_positions = None
    merged_normals = None
    if importer.options.merge and skin_bones:
        merged_positions, merged_normals = _merge_skinned_vertices(importer, vertices, skin_bones)

    bm = bmesh.new()
    for index, vertex in enumerate(vertices):
        position = merged_positions[index] if merged_positions else dx_to_blender_position(vertex.position)
        bm.verts.new(position)
    bm.verts.ensure_lookup_table()

    face_vert_indices = []
    for face in faces:
        try:
            if face[0] < len(bm.verts) and face[1] < len(bm.verts) and face[2] < len(bm.verts) and len(set(face)) == 3:
                bm.faces.new([bm.verts[face[0]], bm.verts[face[1]], bm.verts[face[2]]])
                face_vert_indices.append(face)
        except ValueError:
            pass

    bm.faces.ensure_lookup_table()
    _apply_uv_layers(bm, vertices, face_vert_indices, has_uv2)
    _apply_vertex_colors(bm, vertices, face_vert_indices, has_vertex_color)

    bm.to_mesh(mesh)
    bm.free()

    smoothing_mode = getattr(importer.options, "smoothing", "NORMALS")
    if smoothing_mode == "NONE":
        mesh.shade_flat()
    elif smoothing_mode == "SMOOTH_GROUPS":
        _apply_smoothing_groups(mesh)
    elif smoothing_mode == "NORMALS":
        _apply_custom_normals(mesh, vertices, face_vert_indices, merged_normals)

    mesh.update()

    if mat_name and mat_name in importer.materials:
        obj.data.materials.append(importer.materials[mat_name])

    if skin_bones and importer.armature:
        for skin_bone in skin_bones:
            if skin_bone.name not in obj.vertex_groups:
                obj.vertex_groups.new(name=skin_bone.name)

        for vert_idx, vertex in enumerate(vertices):
            for weight_index in range(4):
                bone_idx = vertex.blend_indices[weight_index]
                weight = vertex.blend_weights[weight_index]

                if bone_idx < len(skin_bones) and weight > 0:
                    bone_name = skin_bones[bone_idx].name
                    if bone_name in obj.vertex_groups:
                        obj.vertex_groups[bone_name].add([vert_idx], weight, "ADD")

        modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
        modifier.object = importer.armature
        obj.parent = importer.armature
        obj.matrix_parent_inverse = importer.armature.matrix_world.inverted()

    obj["dow2_group"] = group_name
    obj["dow2_lod"] = lod_level
    obj["dow2_material"] = mat_name

    if importer.options.weld_vertices:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

    print(f"      Created: {name} ({len(vertices)} verts, {len(face_vert_indices)} faces, {len(skin_bones)} skin bones)")


def _read_vector_element(importer: DoW2ModelImporter, element: VertexElement) -> Vector:
    if element.data_type == 2:
        return unpack_vector([importer.reader.read_byte() for _ in range(4)])

    if element.data_type == 4:
        return Vector(
            (
                importer.reader.read_float(),
                importer.reader.read_float(),
                importer.reader.read_float(),
            )
        )

    return Vector((0, 0, 0))


def _skip_unknown_vertex_element(importer: DoW2ModelImporter, element: VertexElement):
    if element.data_type == 2:
        importer.reader.file.read(4)
    elif element.data_type == 3:
        importer.reader.file.read(8)
    elif element.data_type == 4:
        importer.reader.file.read(12)
    elif element.data_type == 14:
        importer.reader.file.read(4)


def _apply_uv_layers(
    bm: bmesh.types.BMesh,
    vertices: List[ImportVertex],
    face_vert_indices: List[Tuple[int, int, int]],
    has_uv2: bool,
):
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face_index, bm_face in enumerate(bm.faces):
        if face_index >= len(face_vert_indices):
            continue
        orig_face = face_vert_indices[face_index]
        for loop_index, loop in enumerate(bm_face.loops):
            vert_idx = orig_face[loop_index]
            if vert_idx < len(vertices):
                loop[uv_layer].uv = vertices[vert_idx].uv[0]

    if not has_uv2:
        return

    uv_layer2 = bm.loops.layers.uv.new("UVMap2")
    for face_index, bm_face in enumerate(bm.faces):
        if face_index >= len(face_vert_indices):
            continue
        orig_face = face_vert_indices[face_index]
        for loop_index, loop in enumerate(bm_face.loops):
            vert_idx = orig_face[loop_index]
            if vert_idx < len(vertices):
                loop[uv_layer2].uv = vertices[vert_idx].uv[1]


def _apply_vertex_colors(
    bm: bmesh.types.BMesh,
    vertices: List[ImportVertex],
    face_vert_indices: List[Tuple[int, int, int]],
    has_vertex_color: bool,
):
    if not has_vertex_color:
        return

    color_layer = bm.loops.layers.color.new("Color")
    for face_index, bm_face in enumerate(bm.faces):
        if face_index >= len(face_vert_indices):
            continue
        orig_face = face_vert_indices[face_index]
        for loop_index, loop in enumerate(bm_face.loops):
            vert_idx = orig_face[loop_index]
            if vert_idx < len(vertices):
                loop[color_layer] = vertices[vert_idx].color


def _apply_smoothing_groups(mesh: bpy.types.Mesh):
    mesh.shade_smooth()
    mesh.update()

    angle_threshold = math.radians(30)
    edge_faces: Dict[Tuple[int, int], List[bpy.types.MeshPolygon]] = {}
    for polygon in mesh.polygons:
        for index in range(len(polygon.vertices)):
            v1 = polygon.vertices[index]
            v2 = polygon.vertices[(index + 1) % len(polygon.vertices)]
            key = (min(v1, v2), max(v1, v2))
            edge_faces.setdefault(key, []).append(polygon)

    for edge in mesh.edges:
        key = (min(edge.vertices[0], edge.vertices[1]), max(edge.vertices[0], edge.vertices[1]))
        linked_faces = edge_faces.get(key, [])
        if len(linked_faces) == 2:
            edge.use_edge_sharp = linked_faces[0].normal.angle(linked_faces[1].normal) > angle_threshold


def _apply_custom_normals(
    mesh: bpy.types.Mesh,
    vertices: List[ImportVertex],
    face_vert_indices: List[Tuple[int, int, int]],
    merged_normals: Optional[List[Vector]] = None,
):
    mesh.shade_smooth()

    normals = []
    for face_verts in face_vert_indices:
        for vert_idx in face_verts:
            if vert_idx < len(vertices):
                if merged_normals is not None and vert_idx < len(merged_normals):
                    normals.append(merged_normals[vert_idx].normalized())
                else:
                    normals.append(dx_to_blender_normal(vertices[vert_idx].normal).normalized())
            else:
                normals.append(Vector((0, 0, 1)))

    if normals and len(normals) == len(mesh.loops):
        try:
            mesh.normals_split_custom_set(normals)
        except Exception as exc:
            print(f"Warning: Could not set custom normals: {exc}")


def _merge_skinned_vertices(
    importer: "DoW2ModelImporter",
    vertices: List[ImportVertex],
    skin_bones: List[SkinBone],
) -> Tuple[List[Vector], List[Vector]]:
    blend_matrices: List[Matrix] = []
    for skin_bone in skin_bones:
        final_world = _resolve_skin_bone_world_matrix(importer, skin_bone.name)
        if final_world is None:
            final_world = dx_to_blender_matrix(skin_bone.world_matrix)

        inverse_bind = dx_to_blender_matrix(skin_bone.inverse_matrix)
        blend_matrices.append(final_world @ inverse_bind)

    merged_positions: List[Vector] = []
    merged_normals: List[Vector] = []
    for vertex in vertices:
        source_position = dx_to_blender_position(vertex.position)
        source_normal = dx_to_blender_normal(vertex.normal).normalized()
        merged_position = Vector((0.0, 0.0, 0.0))
        merged_normal = Vector((0.0, 0.0, 0.0))
        total_weight = 0.0

        for weight_index in range(4):
            bone_idx = vertex.blend_indices[weight_index]
            weight = vertex.blend_weights[weight_index]
            if weight <= 0 or bone_idx >= len(blend_matrices):
                continue

            position_4d = source_position.to_4d()
            position_4d.w = 1.0
            blend_matrix = blend_matrices[bone_idx]
            merged_position += (blend_matrix @ position_4d).to_3d() * weight
            merged_normal += (blend_matrix.to_3x3() @ source_normal) * weight
            total_weight += weight

        if total_weight > 0:
            merged_positions.append(merged_position)
            if merged_normal.length > 0.0:
                merged_normals.append(merged_normal.normalized())
            else:
                merged_normals.append(source_normal)
        else:
            merged_positions.append(source_position)
            merged_normals.append(source_normal)

    return merged_positions, merged_normals


def _resolve_skin_bone_world_matrix(importer: "DoW2ModelImporter", bone_name: str) -> Optional[Matrix]:
    if importer.armature is None:
        return None

    if bone_name == "skeleton_root":
        return importer.armature.matrix_world.copy()

    armature_bone = importer.armature.data.bones.get(bone_name)
    if armature_bone is not None:
        world_matrix = importer.armature.matrix_world @ armature_bone.matrix_local
        return remove_bone_axis_adapter(world_matrix, importer.armature)

    bone_index = importer.bone_map.get(bone_name)
    if bone_index is not None and bone_index < len(importer.bones):
        return importer.bones[bone_index].transform.copy()

    return None