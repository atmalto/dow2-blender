from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import bmesh
import bpy
from mathutils import Vector

from ..utils import blender_to_dx_position, link_object_to_collection


STATE_NAMES = ("healthy", "light_damage", "heavy_damage", "wreck")
ROOT_BONE_NAME = "skeleton_root"
PHYSICS_ROOT_COLLECTION_NAME = "DoW2 Physics"
PHYSICS_ARMATURE_NAME = "DoW2_Armature"
LEGACY_PHYSICS_ARMATURE_NAME = "DoW2_Physics_Armature"
PHYSICS_HULL_PREFIX = "hull::"
HULL_PROP = "dow2_physics_hull"
BODY_NAME_PROP = "dow2_physics_body_name"
STATE_PROP = "dow2_physics_state"
LOD_PROP = "dow2_physics_lod"
WORKFLOW_PROP = "dow2_physics_workflow"
ARMATURE_PROP = "dow2_is_physics_armature"
GENERATED_BONE_PROP = "dow2_is_generated_physics_bone"
VERTEX_WEIGHT_EPSILON = 1e-6


def find_child_collection(parent: bpy.types.Collection, name: str) -> Optional[bpy.types.Collection]:
    for child in parent.children:
        if child.name == name or child.name.split(".")[0] == name:
            return child
    return None


def ensure_child_collection(parent: bpy.types.Collection, name: str) -> bpy.types.Collection:
    existing = find_child_collection(parent, name)
    if existing is not None:
        return existing

    collection = bpy.data.collections.new(name)
    parent.children.link(collection)
    return collection


def ensure_physics_root_collection(scene: bpy.types.Scene) -> bpy.types.Collection:
    return ensure_child_collection(scene.collection, PHYSICS_ROOT_COLLECTION_NAME)


def ensure_physics_lod_collection(scene: bpy.types.Scene, state_name: str, lod_level: int) -> bpy.types.Collection:
    root = ensure_physics_root_collection(scene)
    state_collection = ensure_child_collection(root, state_name)
    return ensure_child_collection(state_collection, f"lod{lod_level}")


def iter_collection_descendants(collection: bpy.types.Collection) -> Iterable[bpy.types.Collection]:
    yield collection
    for child in collection.children:
        yield from iter_collection_descendants(child)


def is_physics_hull_object(obj: bpy.types.Object) -> bool:
    return bool(obj.get(HULL_PROP, False))


def is_physics_armature_object(obj: bpy.types.Object) -> bool:
    return bool(obj and obj.type == "ARMATURE" and obj.get(ARMATURE_PROP, False))


def find_physics_armature() -> Optional[bpy.types.Object]:
    for armature_name in (PHYSICS_ARMATURE_NAME, LEGACY_PHYSICS_ARMATURE_NAME):
        obj = bpy.data.objects.get(armature_name)
        if obj and obj.type == "ARMATURE":
            return obj
    return None


def get_hull_body_name(obj: bpy.types.Object) -> str:
    return obj.get(BODY_NAME_PROP, obj.name)


def make_hull_object_name(state_name: str, lod_level: int, body_name: str) -> str:
    return f"{PHYSICS_HULL_PREFIX}{state_name}::lod{lod_level}::{body_name}"


def _find_parent_collection(child: bpy.types.Collection) -> Optional[bpy.types.Collection]:
    for parent in bpy.data.collections:
        if child.name in parent.children:
            return parent
    for scene in bpy.data.scenes:
        if child.name in scene.collection.children:
            return scene.collection
    return None


def infer_object_state_and_lod(obj: bpy.types.Object) -> Tuple[Optional[str], int]:
    if is_physics_hull_object(obj):
        return None, 0

    state_name = obj.get("dow2_group")
    lod_level = int(obj.get("dow2_lod", 0))

    if state_name in STATE_NAMES:
        return state_name, lod_level

    for collection in obj.users_collection:
        collection_name = collection.name.split(".")[0]
        if collection_name in STATE_NAMES:
            return collection_name, 0

        if collection_name.startswith("lod"):
            try:
                lod_level = int(collection_name[3:])
            except ValueError:
                lod_level = 0
            parent = _find_parent_collection(collection)
            if parent is not None:
                parent_name = parent.name.split(".")[0]
                if parent_name in STATE_NAMES:
                    return parent_name, lod_level

    return None, 0


def collect_source_meshes(scene: bpy.types.Scene, selected_only: bool) -> Dict[str, Dict[int, List[bpy.types.Object]]]:
    selected_mesh_names = {
        obj.name for obj in bpy.context.selected_objects if obj.type == "MESH"
    } if selected_only else None

    state_map: Dict[str, Dict[int, List[bpy.types.Object]]] = defaultdict(lambda: defaultdict(list))
    for obj in scene.objects:
        if obj.type != "MESH":
            continue
        if is_physics_hull_object(obj):
            continue
        if selected_mesh_names is not None and obj.name not in selected_mesh_names:
            continue

        state_name, lod_level = infer_object_state_and_lod(obj)
        if state_name not in STATE_NAMES:
            continue
        state_map[state_name][lod_level].append(obj)

    return {state: dict(lods) for state, lods in state_map.items()}


def collect_physics_hulls(scene: bpy.types.Scene) -> Dict[str, Dict[int, List[bpy.types.Object]]]:
    hull_map: Dict[str, Dict[int, List[bpy.types.Object]]] = {state: {} for state in STATE_NAMES}
    root = find_child_collection(scene.collection, PHYSICS_ROOT_COLLECTION_NAME)
    if root is None:
        return hull_map

    for state_name in STATE_NAMES:
        state_collection = find_child_collection(root, state_name)
        if state_collection is None:
            continue
        lod_map: Dict[int, List[bpy.types.Object]] = defaultdict(list)
        for collection in iter_collection_descendants(state_collection):
            for obj in collection.objects:
                if obj.type != "MESH" or not is_physics_hull_object(obj):
                    continue
                lod_level = int(obj.get(LOD_PROP, 0))
                lod_map[lod_level].append(obj)
        hull_map[state_name] = dict(lod_map)

    return hull_map


def get_selected_source_bone_names(context: bpy.types.Context) -> Set[str]:
    selected_bones: Set[str] = set()
    candidate_armatures = [
        obj for obj in context.selected_objects if obj.type == "ARMATURE" and not is_physics_armature_object(obj)
    ]
    if context.active_object and context.active_object.type == "ARMATURE" and not is_physics_armature_object(context.active_object):
        if context.active_object not in candidate_armatures:
            candidate_armatures.append(context.active_object)

    for armature_obj in candidate_armatures:
        if context.mode == "POSE" and context.active_object == armature_obj:
            selected_bones.update(pose_bone.name for pose_bone in armature_obj.pose.bones if pose_bone.bone.select)
            continue
        if context.mode == "EDIT_ARMATURE" and context.active_object == armature_obj:
            selected_bones.update(edit_bone.name for edit_bone in armature_obj.data.edit_bones if edit_bone.select)
            continue
        selected_bones.update(bone.name for bone in armature_obj.data.bones if bone.select)

    return selected_bones


def _choose_owner_bone(weight_entries: Sequence[Tuple[str, float]]) -> Optional[str]:
    valid_entries = [(name, weight) for name, weight in weight_entries if name and weight > VERTEX_WEIGHT_EPSILON]
    if not valid_entries:
        return None

    non_root_entries = [(name, weight) for name, weight in valid_entries if name.lower() != ROOT_BONE_NAME]
    candidates = non_root_entries or valid_entries
    candidates.sort(key=lambda item: (-item[1], item[0].lower()))
    return candidates[0][0]


def group_world_vertices_by_owner_bone(mesh_obj: bpy.types.Object) -> Dict[str, List[List[float]]]:
    group_names = {group.index: group.name for group in mesh_obj.vertex_groups}
    owned_vertices: Dict[str, List[List[float]]] = defaultdict(list)
    world_matrix = mesh_obj.matrix_world

    for vertex in mesh_obj.data.vertices:
        weight_entries = []
        for group in vertex.groups:
            bone_name = group_names.get(group.group)
            if bone_name is None:
                continue
            weight_entries.append((bone_name, float(group.weight)))

        owner_bone = _choose_owner_bone(weight_entries)
        if owner_bone is None:
            continue

        world_position = world_matrix @ vertex.co
        owned_vertices[owner_bone].append([world_position.x, world_position.y, world_position.z])

    return dict(owned_vertices)


def collect_vertices_for_bones(
    meshes: Sequence[bpy.types.Object],
    selected_bones: Optional[Set[str]] = None,
) -> Dict[str, List[List[float]]]:
    selected_lower = {name.lower() for name in selected_bones} if selected_bones else None
    merged: Dict[str, List[List[float]]] = defaultdict(list)

    for mesh_obj in meshes:
        owned_vertices = group_world_vertices_by_owner_bone(mesh_obj)
        for bone_name, vertices in owned_vertices.items():
            if bone_name.lower() == ROOT_BONE_NAME and selected_lower is None:
                continue
            if selected_lower is not None and bone_name.lower() not in selected_lower:
                continue
            merged[bone_name].extend(vertices)

    return {bone_name: vertices for bone_name, vertices in merged.items()}


def gather_mesh_world_vertices(mesh_obj: bpy.types.Object) -> List[List[float]]:
    world_matrix = mesh_obj.matrix_world
    return [
        [*(world_matrix @ vertex.co)]
        for vertex in mesh_obj.data.vertices
    ]


def compute_centroid(world_vertices: Sequence[Sequence[float]]) -> Vector:
    if not world_vertices:
        return Vector((0.0, 0.0, 0.0))
    accum = Vector((0.0, 0.0, 0.0))
    for vertex in world_vertices:
        accum += Vector(vertex)
    return accum / len(world_vertices)


def _build_hull_bmesh(world_vertices: Sequence[Sequence[float]]) -> Optional[bmesh.types.BMesh]:
    if len(world_vertices) < 4:
        return None

    bm = bmesh.new()
    for vertex in world_vertices:
        bm.verts.new(vertex)
    bm.verts.ensure_lookup_table()
    result = bmesh.ops.convex_hull(bm, input=bm.verts)

    delete_map = {}
    for key in ("geom_interior", "geom_unused"):
        for element in result.get(key, []):
            if not isinstance(element, (bmesh.types.BMVert, bmesh.types.BMEdge, bmesh.types.BMFace)):
                continue
            if not element.is_valid:
                continue
            delete_map[id(element)] = element

    if delete_map:
        bmesh.ops.delete(bm, geom=list(delete_map.values()), context="VERTS")

    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    if len(bm.verts) < 4 or len(bm.faces) == 0:
        bm.free()
        return None
    return bm


def ensure_physics_armature(scene: bpy.types.Scene) -> bpy.types.Object:
    existing = bpy.data.objects.get(PHYSICS_ARMATURE_NAME)
    if existing and existing.type == "ARMATURE":
        _ensure_armature_root_bone(existing)
        return existing

    legacy = bpy.data.objects.get(LEGACY_PHYSICS_ARMATURE_NAME)
    if legacy and legacy.type == "ARMATURE":
        legacy.name = PHYSICS_ARMATURE_NAME
        if legacy.data is not None:
            legacy.data.name = PHYSICS_ARMATURE_NAME
        _ensure_armature_root_bone(legacy)
        return legacy

    armature_data = bpy.data.armatures.new(PHYSICS_ARMATURE_NAME)
    armature_obj = bpy.data.objects.new(PHYSICS_ARMATURE_NAME, armature_data)
    armature_obj[ARMATURE_PROP] = True
    link_object_to_collection(armature_obj, scene.collection)
    _ensure_armature_root_bone(armature_obj)
    return armature_obj


def _ensure_armature_root_bone(armature_obj: bpy.types.Object) -> None:
    previous_active = bpy.context.view_layer.objects.active
    previous_mode = bpy.context.mode

    if previous_active is not None and previous_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = armature_obj
    armature_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = armature_obj.data.edit_bones
    root_bone = edit_bones.get(ROOT_BONE_NAME)
    if root_bone is None:
        root_bone = edit_bones.new(ROOT_BONE_NAME)
        root_bone.head = Vector((0.0, 0.0, 0.0))
        root_bone.tail = Vector((0.0, 0.05, 0.0))

    bpy.ops.object.mode_set(mode="OBJECT")
    if previous_active is not None:
        bpy.context.view_layer.objects.active = previous_active
    if previous_mode.startswith("EDIT_") or previous_mode == "POSE":
        try:
            bpy.ops.object.mode_set(mode=previous_mode)
        except RuntimeError:
            pass


def ensure_physics_bone(armature_obj: bpy.types.Object, bone_name: str, world_center: Vector) -> None:
    previous_active = bpy.context.view_layer.objects.active
    previous_mode = bpy.context.mode

    if previous_active is not None and previous_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = armature_obj
    armature_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = armature_obj.data.edit_bones
    root_bone = edit_bones.get(ROOT_BONE_NAME)
    if root_bone is None:
        root_bone = edit_bones.new(ROOT_BONE_NAME)
        root_bone.head = Vector((0.0, 0.0, 0.0))
        root_bone.tail = Vector((0.0, 0.05, 0.0))

    edit_bone = edit_bones.get(bone_name)
    if edit_bone is None:
        edit_bone = edit_bones.new(bone_name)
    edit_bone.parent = root_bone
    edit_bone.use_connect = False
    edit_bone.head = world_center
    edit_bone.tail = world_center + Vector((0.0, 0.05, 0.0))
    edit_bone[GENERATED_BONE_PROP] = True

    bpy.ops.object.mode_set(mode="OBJECT")
    bone = armature_obj.data.bones.get(bone_name)
    if bone is not None:
        bone[GENERATED_BONE_PROP] = True
    if previous_active is not None:
        bpy.context.view_layer.objects.active = previous_active
    if previous_mode.startswith("EDIT_") or previous_mode == "POSE":
        try:
            bpy.ops.object.mode_set(mode=previous_mode)
        except RuntimeError:
            pass


def _delete_object(obj: bpy.types.Object) -> None:
    mesh_data = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh_data is not None and mesh_data.users == 0:
        bpy.data.meshes.remove(mesh_data)


def remove_existing_hull(state_name: str, lod_level: int, body_name: str) -> None:
    expected_name = make_hull_object_name(state_name, lod_level, body_name)
    existing = bpy.data.objects.get(expected_name)
    if existing and is_physics_hull_object(existing):
        _delete_object(existing)
        return

    for obj in list(bpy.data.objects):
        if not is_physics_hull_object(obj):
            continue
        if obj.get(BODY_NAME_PROP) != body_name:
            continue
        if int(obj.get(LOD_PROP, -1)) != lod_level:
            continue
        if obj.get(STATE_PROP) != state_name:
            continue
        _delete_object(obj)


def find_existing_hull(state_name: str, lod_level: int, body_name: str) -> Optional[bpy.types.Object]:
    expected_name = make_hull_object_name(state_name, lod_level, body_name)
    existing = bpy.data.objects.get(expected_name)
    if existing and is_physics_hull_object(existing):
        return existing

    for obj in bpy.data.objects:
        if not is_physics_hull_object(obj):
            continue
        if obj.get(BODY_NAME_PROP) != body_name:
            continue
        if int(obj.get(LOD_PROP, -1)) != lod_level:
            continue
        if obj.get(STATE_PROP) != state_name:
            continue
        return obj
    return None


def create_or_replace_hull_object(
    scene: bpy.types.Scene,
    state_name: str,
    lod_level: int,
    body_name: str,
    world_vertices: Sequence[Sequence[float]],
    workflow_name: str,
    armature_obj: Optional[bpy.types.Object],
    generation_preset: str,
    imported_config: Optional[dict] = None,
) -> Optional[bpy.types.Object]:
    from . import hull_properties

    bm = _build_hull_bmesh(world_vertices)
    if bm is None:
        return None
    hull_volume = float(bm.calc_volume(signed=False)) if len(bm.faces) else 0.0

    existing = find_existing_hull(state_name, lod_level, body_name)
    previous_settings = hull_properties.snapshot_hull_settings(existing)
    remove_existing_hull(state_name, lod_level, body_name)
    object_name = make_hull_object_name(state_name, lod_level, body_name)
    mesh = bpy.data.meshes.new(object_name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    hull_obj = bpy.data.objects.new(object_name, mesh)
    hull_obj.display_type = "WIRE"
    hull_obj.hide_render = True
    hull_obj[HULL_PROP] = True
    hull_obj[BODY_NAME_PROP] = body_name
    hull_obj[STATE_PROP] = state_name
    hull_obj[LOD_PROP] = lod_level
    hull_obj[WORKFLOW_PROP] = workflow_name
    hull_obj["dow2_group"] = state_name
    hull_obj["dow2_lod"] = lod_level

    target_collection = ensure_physics_lod_collection(scene, state_name, lod_level)
    link_object_to_collection(hull_obj, target_collection)

    if armature_obj is not None:
        vertex_group = hull_obj.vertex_groups.new(name=body_name)
        vertex_group.add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
        modifier = hull_obj.modifiers.new(name="PhysicsArmature", type="ARMATURE")
        modifier.object = armature_obj

    hull_properties.initialize_hull_settings(
        hull_obj,
        default_preset=generation_preset,
        snapshot=previous_settings,
        imported_config=imported_config,
    )
    if previous_settings is None and imported_config is None:
        hull_properties.apply_generated_rubble_mass_fit(
            hull_obj.dow2_physics_hull_settings,
            generation_preset,
            hull_volume,
        )

    return hull_obj


def _remove_generated_bones(armature_obj: bpy.types.Object) -> int:
    generated_bone_names = [
        bone.name for bone in armature_obj.data.bones
        if bool(bone.get(GENERATED_BONE_PROP, False))
    ]
    if not generated_bone_names:
        return 0

    previous_active = bpy.context.view_layer.objects.active
    previous_mode = bpy.context.mode
    removed_count = 0

    if previous_active is not None and previous_mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = armature_obj
    armature_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = armature_obj.data.edit_bones
    for bone_name in generated_bone_names:
        edit_bone = edit_bones.get(bone_name)
        if edit_bone is None:
            continue
        edit_bones.remove(edit_bone)
        removed_count += 1

    bpy.ops.object.mode_set(mode="OBJECT")
    if previous_active is not None:
        bpy.context.view_layer.objects.active = previous_active
    if previous_mode.startswith("EDIT_") or previous_mode == "POSE":
        try:
            bpy.ops.object.mode_set(mode=previous_mode)
        except RuntimeError:
            pass

    return removed_count


def delete_physics_hulls(scene: bpy.types.Scene) -> int:
    deleted_count = 0
    for obj in list(scene.objects):
        if is_physics_hull_object(obj):
            _delete_object(obj)
            deleted_count += 1

    for armature_name in (PHYSICS_ARMATURE_NAME, LEGACY_PHYSICS_ARMATURE_NAME):
        armature_obj = bpy.data.objects.get(armature_name)
        if armature_obj is None or armature_obj.type != "ARMATURE":
            continue
        _remove_generated_bones(armature_obj)
        if is_physics_armature_object(armature_obj):
            bpy.data.objects.remove(armature_obj, do_unlink=True)

    root_collection = find_child_collection(scene.collection, PHYSICS_ROOT_COLLECTION_NAME)
    if root_collection is not None:
        _remove_collection_recursive(root_collection)

    return deleted_count


def _remove_collection_recursive(collection: bpy.types.Collection) -> None:
    for child in list(collection.children):
        _remove_collection_recursive(child)
    parent = _find_parent_collection(collection)
    if parent is not None and collection.name in parent.children:
        parent.children.unlink(collection)
    if collection.users == 0:
        bpy.data.collections.remove(collection)


def set_hull_visibility(scene: bpy.types.Scene, isolate_hulls: bool) -> int:
    changed = 0
    for obj in scene.objects:
        if isolate_hulls:
            should_hide = not is_physics_hull_object(obj)
        else:
            should_hide = is_physics_hull_object(obj)
        if obj.hide_get() != should_hide:
            obj.hide_set(should_hide)
            changed += 1
    return changed


def hull_object_to_dx_vertices(obj: bpy.types.Object) -> List[List[float]]:
    vertices = []
    world_matrix = obj.matrix_world
    for vertex in obj.data.vertices:
        world_position = world_matrix @ vertex.co
        dx_x, dx_y, dx_z = blender_to_dx_position(world_position)
        vertices.append([dx_x, dx_y, dx_z])
    return vertices


def count_nonempty_state_bins(scene: bpy.types.Scene) -> int:
    hulls = collect_physics_hulls(scene)
    return sum(1 for state_name in STATE_NAMES if sum(len(items) for items in hulls.get(state_name, {}).values()) > 0)