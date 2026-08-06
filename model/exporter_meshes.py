from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

import bpy
from mathutils import Vector

from ..utils import blender_to_dx_matrix, pack_vector
from .export_utils import ExportSkinBone, ExportSubMesh, ExportValidationError, ExportVertex, blender_to_dx_normal, blender_to_dx_position, weights_to_bytes
from .skeleton_space import remove_bone_axis_adapter
from .exporter_mesh_plan import (
    MAX_INFLUENCING_BONES_PER_MESH,
    PlannedTriangle,
    clone_skin_bone,
    collect_vertex_influence_bone_names,
    combine_compatible_sub_meshes,
    count_sub_mesh_influencing_bones,
    partition_triangles_by_bone_limit,
)

if TYPE_CHECKING:
    from .exporter import DoW2ModelExporter


def export_meshes(exporter: "DoW2ModelExporter", materials: List[bpy.types.Material]) -> List[str]:
    """Export meshes matching MaxScript ExportMeshes."""
    print("Collecting meshes...")

    mesh_groups = exporter._collect_mesh_groups(materials)
    return export_mesh_groups(exporter, mesh_groups)


def export_mesh_groups(
    exporter: "DoW2ModelExporter",
    mesh_groups: Dict[str, List[List[ExportSubMesh]]],
) -> List[str]:
    """Write pre-collected mesh groups to the model stream."""

    mesh_header_pos = exporter.writer.file.tell()
    mesh_data_pos = exporter.writer.write_chunk_header("FOLD", "MESH", 3, 0, None, 0)

    mgrp_header_pos = exporter.writer.file.tell()
    mgrp_data_pos = exporter.writer.write_chunk_header("FOLD", "MGRP", 3, 0, None, 0)
    _validate_mesh_group_bone_limits(exporter, mesh_groups)

    if mesh_groups:
        print("Exporting meshes...")
    else:
        print("No meshes found")

    for group_name, lods in mesh_groups.items():
        exporter._export_mesh_group(group_name, lods)

    for group_name in mesh_groups.keys():
        size = 4 * 2 + len(group_name) * 2
        exporter.writer.write_chunk_header("DATA", "NODE", 3, size, None, -1)
        exporter.writer.write_long(len(group_name))
        exporter.writer.write_str(group_name)
        exporter.writer.write_long(len(group_name))
        exporter.writer.write_str(group_name)

    exporter.writer.update_chunk_size(mgrp_header_pos, mgrp_data_pos)
    exporter.writer.update_chunk_size(mesh_header_pos, mesh_data_pos)

    return list(mesh_groups.keys())


def collect_mesh_groups(
    exporter: "DoW2ModelExporter",
    materials: List[bpy.types.Material],
) -> Dict[str, List[List[ExportSubMesh]]]:
    """Collect and organize meshes into export mesh groups."""
    mesh_groups: Dict[str, List[List[ExportSubMesh]]] = {}
    material_lookup = {material.name: material for material in materials}

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue

        group_name = None
        lod_idx = 0
        mesh_name = obj.name

        if "dow2_group" in obj:
            group_name = obj["dow2_group"]
        if "dow2_lod" in obj:
            lod_idx = obj["dow2_lod"]

        if group_name is None:
            for collection in obj.users_collection:
                if collection.name.startswith("lod"):
                    try:
                        lod_idx = int(collection.name[3:].split(".")[0])
                    except Exception:
                        pass
                    for parent_collection in bpy.data.collections:
                        if collection.name in [child.name for child in parent_collection.children]:
                            group_name = parent_collection.name
                            break
                elif collection.name in ["healthy", "light_damage", "heavy_damage", "wreck"]:
                    group_name = collection.name

        if group_name is None:
            name_parts = obj.name.split(":")
            if len(name_parts) >= 3:
                group_name = name_parts[0]
                lod_str = name_parts[1]
                mesh_name = ":".join(name_parts[2:])
                if lod_str.startswith("lod"):
                    try:
                        lod_idx = int(lod_str[3:])
                    except Exception:
                        pass

        if group_name is None:
            group_name = "healthy"

        lod_idx = max(0, min(2, lod_idx))

        if group_name not in mesh_groups:
            mesh_groups[group_name] = [[], [], []]

        sub_meshes = exporter._process_mesh_object(obj, materials, mesh_name)
        mesh_groups[group_name][lod_idx].extend(sub_meshes)

    if exporter.options.combine_same_material_meshes:
        for group_name, lods in mesh_groups.items():
            for lod_idx, lod_meshes in enumerate(lods):
                lods[lod_idx] = combine_compatible_sub_meshes(
                    lod_meshes,
                    material_lookup,
                    max_bones=MAX_INFLUENCING_BONES_PER_MESH,
                )

    return mesh_groups


def process_mesh_object(
    exporter: "DoW2ModelExporter",
    obj: bpy.types.Object,
    materials: List[bpy.types.Material],
    base_name: str,
) -> List[ExportSubMesh]:
    """Process a mesh object into export sub-meshes."""
    import bmesh

    if exporter.options.export_rest_pose:
        return process_mesh_object_rest_pose(exporter, obj, materials, base_name)

    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    source_mesh = bpy.data.meshes.new_from_object(
        eval_obj,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )

    bm = bmesh.new()
    bm.from_mesh(source_mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    temp_mesh = bpy.data.meshes.new("temp_export_mesh")
    bm.to_mesh(temp_mesh)
    bm.free()
    bpy.data.meshes.remove(source_mesh)
    try:
        return _process_mesh_data(
            exporter,
            obj,
            temp_mesh,
            materials,
            base_name,
            eval_obj.matrix_world,
            _get_pose_bone_world_matrix,
        )
    finally:
        bpy.data.meshes.remove(temp_mesh)


def process_mesh_object_rest_pose(
    exporter: "DoW2ModelExporter",
    obj: bpy.types.Object,
    materials: List[bpy.types.Material],
    base_name: str,
) -> List[ExportSubMesh]:
    """Process a mesh object into export sub-meshes using undeformed rest-pose geometry."""
    import bmesh

    source_mesh = obj.data.copy()

    bm = bmesh.new()
    bm.from_mesh(source_mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    temp_mesh = bpy.data.meshes.new("temp_export_mesh")
    bm.to_mesh(temp_mesh)
    bm.free()
    bpy.data.meshes.remove(source_mesh)
    try:
        return _process_mesh_data(
            exporter,
            obj,
            temp_mesh,
            materials,
            base_name,
            obj.matrix_world,
            _get_rest_bone_world_matrix,
        )
    finally:
        bpy.data.meshes.remove(temp_mesh)


def _process_mesh_data(
    exporter: "DoW2ModelExporter",
    obj: bpy.types.Object,
    mesh: bpy.types.Mesh,
    materials: List[bpy.types.Material],
    base_name: str,
    position_matrix,
    bone_matrix_getter,
) -> List[ExportSubMesh]:
    has_uvs = len(mesh.uv_layers) > 0
    has_uvs2 = len(mesh.uv_layers) > 1
    uv_layer = mesh.uv_layers.active.data if mesh.uv_layers else None
    armature = _find_armature(obj)
    vertex_influence_names = collect_vertex_influence_bone_names(obj, mesh) if armature else [set() for _ in mesh.vertices]
    slot_to_global = _build_slot_to_global_map(obj, materials)
    all_skin_bones = _build_skin_bones_for_object(armature, vertex_influence_names, bone_matrix_getter)
    triangles_by_material = _collect_triangles_by_material(mesh, slot_to_global, vertex_influence_names)

    if not triangles_by_material:
        triangles_by_material[0] = []

    result: List[ExportSubMesh] = []
    for global_mat_idx, triangles in triangles_by_material.items():
        buckets = [triangles]
        if exporter.options.apply_bone_limit and triangles:
            buckets = partition_triangles_by_bone_limit(
                triangles,
                max_bones=MAX_INFLUENCING_BONES_PER_MESH,
            )

        if not buckets:
            buckets = [[]]

        for bucket_index, bucket in enumerate(buckets):
            influencing_bones: Set[str] = set()
            for triangle in bucket:
                influencing_bones.update(triangle.influencing_bones)

            sub_mesh = _create_sub_mesh(materials, global_mat_idx, base_name, bucket_index, len(buckets), has_uvs, has_uvs2)
            sub_mesh.influencing_bone_names = tuple(sorted(influencing_bones))
            skin_bones, skin_bone_indices = _build_sub_mesh_skin_bones(all_skin_bones, influencing_bones)
            skin_bone_lookup = {bone.name: bone for bone in skin_bones}

            for triangle in bucket:
                face_indices = []
                for loop_idx in triangle.loop_indices:
                    loop = mesh.loops[loop_idx]
                    vertex = mesh.vertices[loop.vertex_index]

                    export_vert = ExportVertex()
                    export_vert.position = position_matrix @ vertex.co

                    if hasattr(mesh, "corner_normals") and len(mesh.corner_normals) > loop_idx:
                        export_vert.normal = Vector(mesh.corner_normals[loop_idx].vector)
                    else:
                        export_vert.normal = vertex.normal.copy()

                    orig_vert_normal = tuple(round(value, 4) for value in vertex.normal)

                    if uv_layer:
                        uv = uv_layer[loop_idx].uv
                        export_vert.uv[0] = (uv[0], uv[1])

                    if skin_bone_indices:
                        weights = []
                        for group in vertex.groups:
                            if group.group >= len(obj.vertex_groups):
                                continue
                            vertex_group = obj.vertex_groups[group.group]
                            if vertex_group.name in skin_bone_indices and group.weight > 0:
                                weights.append((skin_bone_indices[vertex_group.name], group.weight))

                        weights.sort(key=lambda item: item[1], reverse=True)
                        weights = weights[:4]

                        total = sum(weight for _, weight in weights)
                        if total > 0:
                            for weight_index, (bone_idx, weight) in enumerate(weights):
                                export_vert.blend_indices[weight_index] = bone_idx
                                export_vert.blend_weights[weight_index] = weight / total
                            sub_mesh.has_skin = True

                    exporter._update_bounds(sub_mesh, export_vert.position)

                    if sub_mesh.has_skin:
                        skin_bone_names = [bone.name for bone in skin_bones]
                        for weight_index, bone_idx in enumerate(export_vert.blend_indices):
                            if export_vert.blend_weights[weight_index] <= 0 or bone_idx >= len(skin_bone_names):
                                continue
                            bone_name = skin_bone_names[bone_idx]
                            bone_data = skin_bone_lookup.get(bone_name)
                            if bone_data is not None:
                                exporter._update_bounds_obj(bone_data, export_vert.position)

                    vert_index = exporter._find_or_add_vertex(sub_mesh, export_vert, orig_vert_normal)
                    face_indices.append(vert_index)

                sub_mesh.faces.append(tuple(face_indices))

            if sub_mesh.has_skin:
                sub_mesh.skin_bones = skin_bones

            if sub_mesh.vertices:
                exporter._compute_tangent_space(sub_mesh)
                result.append(sub_mesh)

    return result


def _find_armature(obj: bpy.types.Object) -> Optional[bpy.types.Object]:
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object:
            return modifier.object
    return None


def _build_slot_to_global_map(obj: bpy.types.Object, materials: List[bpy.types.Material]) -> Dict[int, int]:
    slot_to_global: Dict[int, int] = {}
    material_lookup = {material.name: index for index, material in enumerate(materials)}

    for slot_idx, slot in enumerate(obj.material_slots):
        if slot.material:
            slot_to_global[slot_idx] = material_lookup.get(slot.material.name, 0)
        else:
            slot_to_global[slot_idx] = 0

    if not slot_to_global:
        slot_to_global[0] = 0

    return slot_to_global


def _build_skin_bones_for_object(
    armature: Optional[bpy.types.Object],
    vertex_influence_names: List[Set[str]],
    bone_matrix_getter,
) -> Dict[str, ExportSkinBone]:
    skin_bones: Dict[str, ExportSkinBone] = {}
    if armature is None:
        return skin_bones

    used_bones: Set[str] = set()
    for bone_names in vertex_influence_names:
        used_bones.update(bone_names)

    if not used_bones:
        return skin_bones

    root_mat = blender_to_dx_matrix(armature.matrix_world)
    skin_bones["skeleton_root"] = ExportSkinBone(
        name="skeleton_root",
        matrix=root_mat,
        imatrix=root_mat.inverted(),
    )

    for bone_name in sorted(used_bones):
        world_mat = bone_matrix_getter(armature, bone_name)
        if world_mat is None:
            continue
        dx_mat = blender_to_dx_matrix(world_mat)
        skin_bones[bone_name] = ExportSkinBone(
            name=bone_name,
            matrix=dx_mat,
            imatrix=dx_mat.inverted(),
        )

    return skin_bones


def _collect_triangles_by_material(
    mesh: bpy.types.Mesh,
    slot_to_global: Dict[int, int],
    vertex_influence_names: List[Set[str]],
) -> Dict[int, List[PlannedTriangle]]:
    triangles_by_material: Dict[int, List[PlannedTriangle]] = {}

    for poly in mesh.polygons:
        global_mat_idx = slot_to_global.get(poly.material_index, 0)
        loop_indices = list(poly.loop_indices)
        triangles = []
        if len(loop_indices) == 3:
            triangles.append(tuple(loop_indices))
        else:
            for index in range(1, len(loop_indices) - 1):
                triangles.append((loop_indices[0], loop_indices[index], loop_indices[index + 1]))

        for triangle in triangles:
            influencing_bones: Set[str] = set()
            for loop_idx in triangle:
                vertex_index = mesh.loops[loop_idx].vertex_index
                influencing_bones.update(vertex_influence_names[vertex_index])
            triangles_by_material.setdefault(global_mat_idx, []).append(
                PlannedTriangle(loop_indices=triangle, influencing_bones=frozenset(influencing_bones))
            )

    return triangles_by_material


def _create_sub_mesh(
    materials: List[bpy.types.Material],
    global_mat_idx: int,
    base_name: str,
    bucket_index: int,
    bucket_count: int,
    has_uvs: bool,
    has_uvs2: bool,
) -> ExportSubMesh:
    sub_mesh = ExportSubMesh()
    if 0 <= global_mat_idx < len(materials):
        material = materials[global_mat_idx]
        sub_mesh.material_name = material.name
        sub_mesh.name = f"merged material-[{material.name}]"
    else:
        sub_mesh.material_name = ""
        sub_mesh.name = base_name

    if bucket_count > 1:
        sub_mesh.name = f"{sub_mesh.name} [{bucket_index + 1}]"

    sub_mesh.has_map = [has_uvs, has_uvs2]
    return sub_mesh


def _build_sub_mesh_skin_bones(
    all_skin_bones: Dict[str, ExportSkinBone],
    influencing_bones: Set[str],
) -> Tuple[List[ExportSkinBone], Dict[str, int]]:
    if not influencing_bones:
        return [], {}

    skin_bones: List[ExportSkinBone] = []
    skin_bone_indices: Dict[str, int] = {}

    if "skeleton_root" in all_skin_bones:
        skin_bone_indices["skeleton_root"] = len(skin_bones)
        skin_bones.append(clone_skin_bone(all_skin_bones["skeleton_root"]))

    for bone_name in sorted(influencing_bones):
        bone_data = all_skin_bones.get(bone_name)
        if bone_data is None:
            continue
        skin_bone_indices[bone_name] = len(skin_bones)
        skin_bones.append(clone_skin_bone(bone_data))

    return skin_bones, skin_bone_indices


def _get_pose_bone_world_matrix(armature: bpy.types.Object, bone_name: str):
    pose_bone = armature.pose.bones.get(bone_name)
    if pose_bone is None:
        return None
    world_matrix = armature.matrix_world @ pose_bone.matrix
    return remove_bone_axis_adapter(world_matrix, armature)


def _get_rest_bone_world_matrix(armature: bpy.types.Object, bone_name: str):
    rest_bone = armature.data.bones.get(bone_name)
    if rest_bone is None:
        return None
    world_matrix = armature.matrix_world @ rest_bone.matrix_local
    return remove_bone_axis_adapter(world_matrix, armature)


def _validate_mesh_group_bone_limits(
    exporter: "DoW2ModelExporter",
    mesh_groups: Dict[str, List[List[ExportSubMesh]]],
):
    if exporter.options.apply_bone_limit:
        return

    offenders = []
    for group_name, lods in mesh_groups.items():
        for lod_idx, lod_meshes in enumerate(lods):
            for sub_mesh in lod_meshes:
                bone_count = count_sub_mesh_influencing_bones(sub_mesh)
                if bone_count > MAX_INFLUENCING_BONES_PER_MESH:
                    offenders.append(
                        f"{group_name}:lod{lod_idx} -> {sub_mesh.name} uses {bone_count} influencing bones"
                    )

    if offenders:
        details = "; ".join(offenders[:5])
        if len(offenders) > 5:
            details = f"{details}; ... and {len(offenders) - 5} more"
        raise ExportValidationError(
            f"Export aborted: one or more meshes exceed the {MAX_INFLUENCING_BONES_PER_MESH}-bone skin limit. Enable 'Apply 54 Bone Limit' to split them automatically. {details}"
        )


def compute_tangent_space(exporter: "DoW2ModelExporter", sub_mesh: ExportSubMesh):
    """Compute tangent and binormal vectors for all vertices in a sub-mesh."""
    vertices = sub_mesh.vertices
    faces = sub_mesh.faces

    if not vertices or not faces:
        return

    tan1 = [Vector((0, 0, 0)) for _ in vertices]
    tan2 = [Vector((0, 0, 0)) for _ in vertices]

    for face in faces:
        i0, i1, i2 = face

        v0 = vertices[i0]
        v1 = vertices[i1]
        v2 = vertices[i2]

        p21 = v1.position - v0.position
        p31 = v2.position - v0.position

        uv0 = v0.uv[0] if v0.uv[0] else (0.0, 0.0)
        uv1 = v1.uv[0] if v1.uv[0] else (0.0, 0.0)
        uv2 = v2.uv[0] if v2.uv[0] else (0.0, 0.0)

        uv21 = (uv1[0] - uv0[0], uv1[1] - uv0[1])
        uv31 = (uv2[0] - uv0[0], uv2[1] - uv0[1])

        determinant = uv21[0] * uv31[1] - uv31[0] * uv21[1]
        if abs(determinant) < 1e-8:
            reciprocal = 1.0
        else:
            reciprocal = 1.0 / determinant

        sdir = Vector(
            (
                (uv31[1] * p21.x - uv21[1] * p31.x) * reciprocal,
                (uv31[1] * p21.y - uv21[1] * p31.y) * reciprocal,
                (uv31[1] * p21.z - uv21[1] * p31.z) * reciprocal,
            )
        )
        tdir = Vector(
            (
                (uv21[0] * p31.x - uv31[0] * p21.x) * reciprocal,
                (uv21[0] * p31.y - uv31[0] * p21.y) * reciprocal,
                (uv21[0] * p31.z - uv31[0] * p21.z) * reciprocal,
            )
        )

        tan1[i0] += sdir
        tan1[i1] += sdir
        tan1[i2] += sdir
        tan2[i0] += tdir
        tan2[i1] += tdir
        tan2[i2] += tdir

    for index, vert in enumerate(vertices):
        normal = vert.normal.normalized()
        tangent = tan1[index]

        tangent = tangent - normal * normal.dot(tangent)
        if tangent.length > 1e-8:
            tangent = tangent.normalized()
        else:
            if abs(normal.z) < 0.9:
                tangent = normal.cross(Vector((0, 0, 1))).normalized()
            else:
                tangent = normal.cross(Vector((1, 0, 0))).normalized()

        binormal = normal.cross(tangent)
        if normal.cross(tangent).dot(tan2[index]) < 0:
            binormal = -binormal

        if binormal.length > 1e-8:
            binormal = binormal.normalized()

        vert.tangent = tangent
        vert.binormal = binormal


def make_vertex_key(
    exporter: "DoW2ModelExporter",
    vert: ExportVertex,
    orig_vert_normal: Optional[Tuple[float, float, float]] = None,
) -> Tuple[Tuple[float, ...], Tuple[float, ...], Tuple[float, ...], Tuple[float, ...]]:
    """Create a hashable key for vertex welding."""

    def round_vec(value, decimals=4):
        return tuple(round(component, decimals) for component in value)

    return (
        round_vec(vert.position),
        orig_vert_normal if orig_vert_normal else round_vec(vert.normal),
        round_vec(vert.uv[0]) if vert.uv[0] else (0.0, 0.0),
        round_vec(vert.uv[1]) if vert.uv[1] else (0.0, 0.0),
    )


def find_or_add_vertex(
    exporter: "DoW2ModelExporter",
    sub_mesh: ExportSubMesh,
    vert: ExportVertex,
    orig_vert_normal: Optional[Tuple[float, float, float]] = None,
) -> int:
    """Find an existing export vertex or append a new one."""
    if not hasattr(sub_mesh, "_vertex_cache"):
        sub_mesh._vertex_cache = {}

    key = exporter._make_vertex_key(vert, orig_vert_normal)
    if key in sub_mesh._vertex_cache:
        return sub_mesh._vertex_cache[key]

    index = len(sub_mesh.vertices)
    sub_mesh.vertices.append(vert)
    sub_mesh._vertex_cache[key] = index
    return index


def update_bounds(exporter: "DoW2ModelExporter", sub_mesh: ExportSubMesh, pos: Vector):
    """Update a sub-mesh bounding box."""
    if sub_mesh.minimum is None:
        sub_mesh.minimum = pos.copy()
        sub_mesh.maximum = pos.copy()
    else:
        for index in range(3):
            sub_mesh.minimum[index] = min(sub_mesh.minimum[index], pos[index])
            sub_mesh.maximum[index] = max(sub_mesh.maximum[index], pos[index])


def update_bounds_obj(exporter: "DoW2ModelExporter", obj, pos: Vector):
    """Update min/max bounds on any object exposing minimum and maximum."""
    if obj.minimum is None:
        obj.minimum = pos.copy()
        obj.maximum = pos.copy()
    else:
        for index in range(3):
            obj.minimum[index] = min(obj.minimum[index], pos[index])
            obj.maximum[index] = max(obj.maximum[index], pos[index])


def export_mesh_group(exporter: "DoW2ModelExporter", group_name: str, lods: List[List[ExportSubMesh]]):
    """Export a mesh group matching MaxScript mesh group export."""
    print(f"Exporting mesh group '{group_name}'")

    mesh_header_pos = exporter.writer.file.tell()
    mesh_data_pos = exporter.writer.write_chunk_header("FOLD", "MESH", 3, 0, group_name, 0)

    imdg_header_pos = exporter.writer.file.tell()
    imdg_data_pos = exporter.writer.write_chunk_header("FOLD", "IMDG", 1, 0, group_name, 0)

    for lod_idx, lod_meshes in enumerate(lods):
        if not lod_meshes:
            continue

        print(f"Exporting lod{lod_idx}")
        lod_name = f"{group_name}:lod{lod_idx}"

        lod_mesh_header_pos = exporter.writer.file.tell()
        lod_mesh_data_pos = exporter.writer.write_chunk_header("FOLD", "MESH", 3, 0, lod_name, 0)

        imod_header_pos = exporter.writer.file.tell()
        imod_data_pos = exporter.writer.write_chunk_header("FOLD", "IMOD", 4, 0, lod_name, 0)

        exporter.writer.write_chunk_header("DATA", "DATA", 9, 4, None, 1)
        exporter.writer.write_long(lod_idx)

        for sub_mesh in lod_meshes:
            exporter._export_sub_mesh(sub_mesh)

        exporter.writer.update_chunk_size(imod_header_pos, imod_data_pos)
        exporter.writer.update_chunk_size(lod_mesh_header_pos, lod_mesh_data_pos)

    exporter.writer.update_chunk_size(imdg_header_pos, imdg_data_pos)
    exporter.writer.update_chunk_size(mesh_header_pos, mesh_data_pos)


def export_sub_mesh(exporter: "DoW2ModelExporter", sub_mesh: ExportSubMesh):
    """Export a sub-mesh matching MaxScript ExportSubMesh."""
    print(f"Exporting '{sub_mesh.name}' sub mesh ({len(sub_mesh.vertices)} verts, {len(sub_mesh.faces)} faces)")

    mesh_header_pos = exporter.writer.file.tell()
    mesh_data_pos = exporter.writer.write_chunk_header("FOLD", "MESH", 3, 0, sub_mesh.name, 0)

    trim_header_pos = exporter.writer.file.tell()
    trim_data_pos = exporter.writer.write_chunk_header("FOLD", "TRIM", 7, 0, sub_mesh.name, 0)

    data_header_pos = exporter.writer.file.tell()
    data_data_pos = exporter.writer.write_chunk_header("DATA", "DATA", 7, 0, None, -1)

    vertex_size = exporter._write_vertex_elements(sub_mesh)

    exporter.writer.write_long(len(sub_mesh.vertices))
    exporter.writer.write_long(vertex_size)

    for vert in sub_mesh.vertices:
        exporter._write_vertex(vert, sub_mesh)

    num_indices = len(sub_mesh.faces) * 3
    exporter.writer.write_long(1)
    exporter.writer.write_long(num_indices)
    exporter.writer.write_long(3)
    exporter.writer.write_long(num_indices)

    for face in sub_mesh.faces:
        exporter.writer.write_short(face[0])
        exporter.writer.write_short(face[2])
        exporter.writer.write_short(face[1])

    if sub_mesh.material_name:
        exporter.writer.write_long(len(sub_mesh.material_name))
        exporter.writer.write_str(sub_mesh.material_name)
    else:
        exporter.writer.write_long(0)

    if sub_mesh.has_skin and sub_mesh.skin_bones:
        exporter.writer.write_long(len(sub_mesh.skin_bones))
        for bone in sub_mesh.skin_bones:
            exporter.writer.write_matrix(bone.matrix)
            exporter.writer.write_matrix(bone.imatrix)
            exporter.writer.write_long(len(bone.name))
            exporter.writer.write_str(bone.name)
    else:
        exporter.writer.write_long(0)

    exporter.writer.write_long(0)
    exporter.writer.write_long(0)

    exporter.writer.update_chunk_size(data_header_pos, data_data_pos)

    exporter._export_bounding_volumes(sub_mesh)

    exporter.writer.update_chunk_size(trim_header_pos, trim_data_pos)
    exporter.writer.update_chunk_size(mesh_header_pos, mesh_data_pos)


def write_vertex_elements(exporter: "DoW2ModelExporter", sub_mesh: ExportSubMesh) -> int:
    """Write vertex element declarations matching MaxScript WriteVertexElements."""
    num_elements = 0
    vertex_size = 0

    num_elem_pos = exporter.writer.file.tell()
    exporter.writer.write_long(0)

    exporter.writer.write_long(0)
    exporter.writer.write_long(4)
    exporter.writer.write_long(4)
    num_elements += 1
    vertex_size += 12

    if sub_mesh.has_skin:
        exporter.writer.write_long(1)
        exporter.writer.write_long(4)
        exporter.writer.write_long(14)
        num_elements += 1
        vertex_size += 4

        exporter.writer.write_long(2)
        exporter.writer.write_long(4)
        exporter.writer.write_long(2)
        num_elements += 1
        vertex_size += 4

    exporter.writer.write_long(3)
    exporter.writer.write_long(4)
    exporter.writer.write_long(2)
    num_elements += 1
    vertex_size += 4

    exporter.writer.write_long(4)
    exporter.writer.write_long(4)
    exporter.writer.write_long(2)
    num_elements += 1
    vertex_size += 4

    exporter.writer.write_long(5)
    exporter.writer.write_long(4)
    exporter.writer.write_long(2)
    num_elements += 1
    vertex_size += 4

    if sub_mesh.has_map[0]:
        exporter.writer.write_long(8)
        exporter.writer.write_long(4)
        exporter.writer.write_long(3)
        num_elements += 1
        vertex_size += 8

    if sub_mesh.has_map[1]:
        exporter.writer.write_long(9)
        exporter.writer.write_long(4)
        exporter.writer.write_long(3)
        num_elements += 1
        vertex_size += 8

    current_pos = exporter.writer.file.tell()
    exporter.writer.file.seek(num_elem_pos)
    exporter.writer.write_long(num_elements)
    exporter.writer.file.seek(current_pos)

    return vertex_size


def write_vertex(exporter: "DoW2ModelExporter", vert: ExportVertex, sub_mesh: ExportSubMesh):
    """Write a single vertex matching MaxScript vertex writing."""
    dx_pos = blender_to_dx_position(vert.position)
    exporter.writer.write_float(dx_pos[0])
    exporter.writer.write_float(dx_pos[1])
    exporter.writer.write_float(dx_pos[2])

    if sub_mesh.has_skin:
        for index in vert.blend_indices:
            exporter.writer.write_byte(index)

        weight_bytes = weights_to_bytes(vert.blend_weights)
        exporter.writer.file.write(weight_bytes)

    dx_normal = blender_to_dx_normal(vert.normal)
    exporter.writer.file.write(pack_vector(dx_normal))

    dx_binormal = blender_to_dx_normal(vert.binormal)
    exporter.writer.file.write(pack_vector(dx_binormal))

    dx_tangent = blender_to_dx_normal(vert.tangent)
    exporter.writer.file.write(pack_vector(dx_tangent))

    for index in range(2):
        if sub_mesh.has_map[index]:
            uv = vert.uv[index] if vert.uv[index] else (0.0, 0.0)
            exporter.writer.write_float(uv[0])
            exporter.writer.write_float(-uv[1])


def export_bounding_volumes(exporter: "DoW2ModelExporter", sub_mesh: ExportSubMesh):
    """Export bounding volumes matching MaxScript ExportBoundingVolumes.

    When export_existing_bvols is enabled, reads position/scale from
    BVOL_ wire-cube objects instead of recomputing from mesh vertices.
    """
    if exporter.options.export_existing_bvols:
        mesh_min, mesh_max, bone_bounds = _collect_existing_bvols(exporter, sub_mesh)
        if mesh_min is not None:
            exporter._write_bounding_volume(mesh_min, mesh_max)
            for bone in sub_mesh.skin_bones:
                bmin, bmax = bone_bounds.get(bone.name, (None, None))
                if bmin is None:
                    bmin, bmax = bone.minimum, bone.maximum
                exporter._write_bounding_volume(bmin, bmax)
            return

    exporter._write_bounding_volume(sub_mesh.minimum, sub_mesh.maximum)

    for bone in sub_mesh.skin_bones:
        exporter._write_bounding_volume(bone.minimum, bone.maximum)


def _collect_existing_bvols(
    exporter: "DoW2ModelExporter",
    sub_mesh: ExportSubMesh,
) -> tuple:
    """Look up BVOL_ objects for the given sub-mesh.

    Returns (mesh_min, mesh_max, {bone_name: (min, max), ...}).
    Returns (None, None, {}) if no mesh-level BVOL found.
    """
    material_key = getattr(sub_mesh, "material_name", "")

    bvol_objects = [
        o for o in bpy.data.objects
        if o.name.startswith("BVOL_")
        and (o.get("dow2_bvol_material") == material_key
             or o.get("dow2_bvol_submesh") == sub_mesh.name)
    ]

    mesh_min = None
    mesh_max = None
    bone_bounds: dict = {}

    for obj in bvol_objects:
        center = obj.location
        half = obj.scale
        vmin = center - half
        vmax = center + half

        bvol_type = obj.get("dow2_bvol_type")
        if bvol_type == "mesh":
            mesh_min = vmin
            mesh_max = vmax
        elif bvol_type == "bone":
            bone_name = obj.get("dow2_bvol_bone_name", "")
            if bone_name:
                bone_bounds[bone_name] = (vmin, vmax)

    return mesh_min, mesh_max, bone_bounds


def write_bounding_volume(
    exporter: "DoW2ModelExporter",
    vmin: Optional[Vector],
    vmax: Optional[Vector],
):
    """Write a single bounding volume matching MaxScript ExportBoundingVolume."""
    if vmin is None:
        vmin = Vector((0, 0, 0))
    if vmax is None:
        vmax = Vector((0, 0, 0))

    exporter.writer.write_chunk_header("DATA", "BVOL", 2, 61, None, -1)
    exporter.writer.write_byte(1)

    center = (vmax + vmin) / 2
    dx_center = blender_to_dx_position(center)
    exporter.writer.write_float(dx_center[0])
    exporter.writer.write_float(dx_center[1])
    exporter.writer.write_float(dx_center[2])

    scale = (vmax - vmin) * 0.5
    exporter.writer.write_float(scale.x)
    exporter.writer.write_float(scale.z)
    exporter.writer.write_float(scale.y)

    identity = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    for value in identity:
        exporter.writer.write_float(value)


__all__ = [
    "collect_mesh_groups",
    "compute_tangent_space",
    "export_bounding_volumes",
    "export_mesh_group",
    "export_mesh_groups",
    "export_meshes",
    "export_sub_mesh",
    "find_or_add_vertex",
    "make_vertex_key",
    "process_mesh_object",
    "update_bounds",
    "update_bounds_obj",
    "write_bounding_volume",
    "write_vertex",
    "write_vertex_elements",
]