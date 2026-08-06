import bpy
from collections import defaultdict
from typing import Dict, List


DAMAGE_STATES = ["healthy", "light_damage", "heavy_damage", "wreck"]
PHYSICS_ROOT_COLLECTION_NAME = "DoW2 Physics"


def _is_damage_state_collection(name: str) -> bool:
    base_name = name.split(".")[0]
    return base_name in DAMAGE_STATES


def _is_lod_collection(name: str) -> bool:
    return name.lower().startswith("lod")


def _lod_sort_key(name: str):
    suffix = name[3:].split(".")[0]
    try:
        return int(suffix)
    except Exception:
        return 999


def _find_child_collection(parent: bpy.types.Collection, name: str):
    for child in parent.children:
        if child.name == name or child.name.split(".")[0] == name:
            return child
    return None


def _iter_collection_descendants(collection: bpy.types.Collection):
    yield collection
    for child in collection.children:
        yield from _iter_collection_descendants(child)


def find_active_armature(scene: bpy.types.Scene):
    named = bpy.data.objects.get("DoW2_Armature")
    if named and named.type == 'ARMATURE':
        return named

    for obj in scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def collect_meshes_by_damage_state(scene: bpy.types.Scene) -> Dict[str, Dict[str, List[bpy.types.Object]]]:
    grouped = {state: defaultdict(list) for state in DAMAGE_STATES}

    for state_collection in scene.collection.children:
        if not _is_damage_state_collection(state_collection.name):
            continue

        state_name = state_collection.name.split(".")[0]

        for child in state_collection.children:
            if not _is_lod_collection(child.name):
                continue
            lod_name = child.name
            for obj in child.objects:
                if obj.type == 'MESH':
                    grouped[state_name][lod_name].append(obj)

        for obj in state_collection.objects:
            if obj.type == 'MESH':
                grouped[state_name]["lod0"].append(obj)

    normalized = {}
    for state, lod_map in grouped.items():
        sorted_lods = dict(sorted(lod_map.items(), key=lambda item: _lod_sort_key(item[0])))
        normalized[state] = sorted_lods
    return normalized


def collect_collision_meshes(scene: bpy.types.Scene) -> Dict[str, List[bpy.types.Object]]:
    collisions = {}
    for collection in bpy.data.collections:
        base_name = collection.name.split(".")[0]
        if not (base_name.endswith("_collision") or base_name.startswith("Collision::")):
            continue
        meshes = [obj for obj in collection.objects if obj.type == 'MESH']
        if meshes:
            collisions[collection.name] = meshes
    return collisions


def collect_physics_hulls(scene: bpy.types.Scene) -> Dict[str, Dict[str, List[bpy.types.Object]]]:
    grouped = {state: defaultdict(list) for state in DAMAGE_STATES}

    root = _find_child_collection(scene.collection, PHYSICS_ROOT_COLLECTION_NAME)
    if root is not None:
        for state_name in DAMAGE_STATES:
            state_collection = _find_child_collection(root, state_name)
            if state_collection is None:
                continue
            for collection in _iter_collection_descendants(state_collection):
                lod_name = collection.name.split(".")[0]
                if not _is_lod_collection(lod_name):
                    lod_name = f"lod{int(collection.get('dow2_physics_lod', 0))}"
                for obj in collection.objects:
                    if obj.type != 'MESH' or not bool(obj.get("dow2_physics_hull", False)):
                        continue
                    grouped[state_name][lod_name].append(obj)

        normalized = {}
        for state, lod_map in grouped.items():
            sorted_lods = dict(sorted(lod_map.items(), key=lambda item: _lod_sort_key(item[0])))
            normalized[state] = sorted_lods
        return normalized

    for obj in scene.objects:
        if obj.type != 'MESH' or not bool(obj.get("dow2_physics_hull", False)):
            continue
        state_name = str(obj.get("dow2_physics_state", ""))
        if state_name not in grouped:
            continue
        lod_level = int(obj.get("dow2_physics_lod", 0))
        grouped[state_name][f"lod{lod_level}"].append(obj)

    normalized = {}
    for state, lod_map in grouped.items():
        sorted_lods = dict(sorted(lod_map.items(), key=lambda item: _lod_sort_key(item[0])))
        normalized[state] = sorted_lods
    return normalized


def collect_markers_and_cover(scene: bpy.types.Scene) -> List[bpy.types.Object]:
    results = []
    for obj in scene.objects:
        if obj.type != 'EMPTY':
            continue
        if bool(obj.get("dow2_is_marker", False)):
            results.append(obj)
            continue
        upper = obj.name.upper()
        if "MARKER" in upper or "MRKR" in upper or "COVER" in upper or upper in {"SIMBOX", "COVERBOX"}:
            results.append(obj)
    return sorted(results, key=lambda item: item.name.lower())


def is_relic_material(mat: bpy.types.Material) -> bool:
    if mat is None:
        return False
    return bool(mat.get("dow2_is_relic_material", False) or "dow2_shader" in mat)


def get_material_shader(mat: bpy.types.Material) -> str:
    return str(mat.get("dow2_shader", "")) if mat else ""
