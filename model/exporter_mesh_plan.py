from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bpy

from .export_utils import ExportSkinBone, ExportSubMesh, ExportVertex


MAX_INFLUENCING_BONES_PER_MESH = 54


@dataclass(frozen=True)
class PlannedTriangle:
    loop_indices: Tuple[int, int, int]
    influencing_bones: frozenset[str]


def collect_vertex_influence_bone_names(obj: bpy.types.Object, mesh: bpy.types.Mesh) -> List[Set[str]]:
    """Collect positive-weight bone names for each mesh vertex."""
    group_names = [group.name for group in obj.vertex_groups]
    vertex_influences: List[Set[str]] = []

    for vertex in mesh.vertices:
        bone_names: Set[str] = set()
        for group in vertex.groups:
            if group.weight > 0 and group.group < len(group_names):
                bone_names.add(group_names[group.group])
        vertex_influences.append(bone_names)

    return vertex_influences


def count_influencing_bones(bone_name_sets: Iterable[Iterable[str]]) -> int:
    """Count unique influencing bones across an iterable of bone-name sets."""
    unique_bones: Set[str] = set()
    for bone_names in bone_name_sets:
        unique_bones.update(bone_names)
    return len(unique_bones)


def get_sub_mesh_influencing_bone_names(sub_mesh: ExportSubMesh) -> Set[str]:
    """Return the effective influencing bone names for a sub-mesh."""
    if sub_mesh.influencing_bone_names:
        return set(sub_mesh.influencing_bone_names)

    if not sub_mesh.has_skin or not sub_mesh.skin_bones:
        return set()

    skin_bone_names = [bone.name for bone in sub_mesh.skin_bones]
    influencing_bones: Set[str] = set()

    for vertex in sub_mesh.vertices:
        for bone_idx, weight in zip(vertex.blend_indices, vertex.blend_weights):
            if weight <= 0 or bone_idx >= len(skin_bone_names):
                continue
            bone_name = skin_bone_names[bone_idx]
            if bone_name != "skeleton_root":
                influencing_bones.add(bone_name)

    return influencing_bones


def count_sub_mesh_influencing_bones(sub_mesh: ExportSubMesh) -> int:
    """Count unique influencing bones for a sub-mesh."""
    return len(get_sub_mesh_influencing_bone_names(sub_mesh))


def partition_triangles_by_bone_limit(
    triangles: Sequence[PlannedTriangle],
    max_bones: int = MAX_INFLUENCING_BONES_PER_MESH,
) -> List[List[PlannedTriangle]]:
    """Partition triangles into buckets that each stay within the bone limit."""
    if not triangles:
        return []

    buckets: List[Dict[str, object]] = []

    for triangle in triangles:
        best_bucket: Optional[Dict[str, object]] = None
        best_overlap = -1

        for bucket in buckets:
            bucket_bones = bucket["bones"]
            merged_bones = bucket_bones | triangle.influencing_bones
            if len(merged_bones) > max_bones:
                continue

            overlap = len(bucket_bones & triangle.influencing_bones)
            if overlap > best_overlap:
                best_overlap = overlap
                best_bucket = bucket

        if best_bucket is None:
            best_bucket = {
                "bones": set(triangle.influencing_bones),
                "triangles": [],
            }
            buckets.append(best_bucket)
        else:
            best_bucket["bones"].update(triangle.influencing_bones)

        best_bucket["triangles"].append(triangle)

    return [bucket["triangles"] for bucket in buckets]


def material_export_signature(material: Optional[bpy.types.Material]):
    """Build a stable signature for exported material-equivalence checks."""
    if material is None:
        return None

    if material.get("dow2_force_unique_export_material", False):
        return ("unique", material.name)

    signature = []
    for key in sorted(material.keys()):
        if key in {"_RNA_UI", "dow2_force_unique_export_material"}:
            continue
        signature.append((key, _normalize_material_value(material[key])))

    return tuple(signature)


def combine_compatible_sub_meshes(
    sub_meshes: Sequence[ExportSubMesh],
    material_lookup: Dict[str, bpy.types.Material],
    max_bones: int = MAX_INFLUENCING_BONES_PER_MESH,
) -> List[ExportSubMesh]:
    """Combine sub-meshes with equivalent materials when layout and bone limits allow it."""
    combined: List[ExportSubMesh] = []

    for sub_mesh in sub_meshes:
        signature = material_export_signature(material_lookup.get(sub_mesh.material_name))
        target: Optional[ExportSubMesh] = None
        best_overlap = -1

        if signature is not None:
            source_bones = get_sub_mesh_influencing_bone_names(sub_mesh)
            for candidate in combined:
                candidate_signature = getattr(candidate, "_material_signature", None)
                if candidate_signature != signature:
                    continue
                if candidate.has_skin != sub_mesh.has_skin:
                    continue
                if tuple(candidate.has_map) != tuple(sub_mesh.has_map):
                    continue

                candidate_bones = get_sub_mesh_influencing_bone_names(candidate)
                if len(candidate_bones | source_bones) > max_bones:
                    continue

                overlap = len(candidate_bones & source_bones)
                if overlap > best_overlap:
                    best_overlap = overlap
                    target = candidate

        if target is None:
            clone = clone_sub_mesh(sub_mesh)
            clone._material_signature = signature
            combined.append(clone)
            continue

        merge_sub_mesh_into(target, sub_mesh)

    for sub_mesh in combined:
        if hasattr(sub_mesh, "_material_signature"):
            delattr(sub_mesh, "_material_signature")

    return combined


def clone_vertex(vertex: ExportVertex) -> ExportVertex:
    """Create a detached export-vertex copy."""
    clone = ExportVertex()
    clone.position = vertex.position.copy()
    clone.blend_indices = list(vertex.blend_indices)
    clone.blend_weights = list(vertex.blend_weights)
    clone.normal = vertex.normal.copy()
    clone.binormal = vertex.binormal.copy()
    clone.tangent = vertex.tangent.copy()
    clone.uv = [tuple(value) if value else None for value in vertex.uv]
    return clone


def clone_skin_bone(bone: ExportSkinBone) -> ExportSkinBone:
    """Create a detached skin-bone copy."""
    return ExportSkinBone(
        name=bone.name,
        matrix=bone.matrix.copy(),
        imatrix=bone.imatrix.copy(),
        minimum=bone.minimum.copy() if bone.minimum else None,
        maximum=bone.maximum.copy() if bone.maximum else None,
    )


def clone_sub_mesh(sub_mesh: ExportSubMesh) -> ExportSubMesh:
    """Create a detached sub-mesh copy."""
    return ExportSubMesh(
        name=sub_mesh.name,
        material_name=sub_mesh.material_name,
        vertices=[clone_vertex(vertex) for vertex in sub_mesh.vertices],
        faces=list(sub_mesh.faces),
        skin_bones=[clone_skin_bone(bone) for bone in sub_mesh.skin_bones],
        has_skin=sub_mesh.has_skin,
        has_map=list(sub_mesh.has_map),
        minimum=sub_mesh.minimum.copy() if sub_mesh.minimum else None,
        maximum=sub_mesh.maximum.copy() if sub_mesh.maximum else None,
        influencing_bone_names=tuple(sub_mesh.influencing_bone_names),
    )


def merge_sub_mesh_into(target: ExportSubMesh, source: ExportSubMesh):
    """Append one sub-mesh into another, remapping skin indices as needed."""
    vertex_offset = len(target.vertices)
    target.has_skin = target.has_skin or source.has_skin

    source_skin_names = [bone.name for bone in source.skin_bones]
    target_skin_indices = {bone.name: index for index, bone in enumerate(target.skin_bones)}

    for source_bone in source.skin_bones:
        target_bone = next((bone for bone in target.skin_bones if bone.name == source_bone.name), None)
        if target_bone is None:
            target_skin_indices[source_bone.name] = len(target.skin_bones)
            target.skin_bones.append(clone_skin_bone(source_bone))
            continue
        _merge_bounds(target_bone, source_bone.minimum, source_bone.maximum)

    for vertex in source.vertices:
        clone = clone_vertex(vertex)
        if target.has_skin and source_skin_names:
            clone.blend_indices = [0, 0, 0, 0]
            for slot, (bone_idx, weight) in enumerate(zip(vertex.blend_indices, vertex.blend_weights)):
                if weight <= 0 or bone_idx >= len(source_skin_names):
                    continue
                bone_name = source_skin_names[bone_idx]
                clone.blend_indices[slot] = target_skin_indices[bone_name]
        target.vertices.append(clone)

    for face in source.faces:
        target.faces.append((face[0] + vertex_offset, face[1] + vertex_offset, face[2] + vertex_offset))

    _merge_bounds(target, source.minimum, source.maximum)

    merged_bones = set(get_sub_mesh_influencing_bone_names(target))
    merged_bones.update(get_sub_mesh_influencing_bone_names(source))
    target.influencing_bone_names = tuple(sorted(merged_bones))


def _merge_bounds(target, source_minimum, source_maximum):
    if source_minimum is None or source_maximum is None:
        return

    if target.minimum is None:
        target.minimum = source_minimum.copy()
        target.maximum = source_maximum.copy()
        return

    for index in range(3):
        target.minimum[index] = min(target.minimum[index], source_minimum[index])
        target.maximum[index] = max(target.maximum[index], source_maximum[index])


def _normalize_material_value(value):
    if hasattr(value, "items"):
        return tuple((str(key), _normalize_material_value(item)) for key, item in sorted(value.items()))
    if isinstance(value, str):
        return value
    if hasattr(value, "__iter__") and not isinstance(value, (bytes, bytearray)):
        try:
            return tuple(_normalize_material_value(item) for item in value)
        except TypeError:
            return value
    return value


__all__ = [
    "MAX_INFLUENCING_BONES_PER_MESH",
    "PlannedTriangle",
    "clone_skin_bone",
    "clone_sub_mesh",
    "collect_vertex_influence_bone_names",
    "combine_compatible_sub_meshes",
    "count_influencing_bones",
    "count_sub_mesh_influencing_bones",
    "get_sub_mesh_influencing_bone_names",
    "material_export_signature",
    "merge_sub_mesh_into",
    "partition_triangles_by_bone_limit",
]