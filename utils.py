import json
import os

import bpy
from mathutils import Matrix, Vector
from typing import List, Tuple, Optional


_ADDON_PREFERENCE_IDS = tuple(dict.fromkeys((
    (__package__ or "dow2_tools").split(".", 1)[0],
    "dow2_tools",
)))
_USER_PREFERENCES_SAVE_PENDING = False
DEFAULT_DOW2_RETRIBUTION_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Dawn of War II - Retribution"


def _save_user_preferences_timer():
    global _USER_PREFERENCES_SAVE_PENDING
    _USER_PREFERENCES_SAVE_PENDING = False

    try:
        if bpy.ops.wm.save_userpref.poll():
            bpy.ops.wm.save_userpref()
    except RuntimeError:
        pass

    return None


def save_user_preferences() -> None:
    global _USER_PREFERENCES_SAVE_PENDING

    try:
        if bpy.ops.wm.save_userpref.poll():
            bpy.ops.wm.save_userpref()
            return
    except RuntimeError:
        pass

    if _USER_PREFERENCES_SAVE_PENDING:
        return

    _USER_PREFERENCES_SAVE_PENDING = True
    bpy.app.timers.register(_save_user_preferences_timer, first_interval=0.0)


def get_addon_preferences(context=None):
    context = context or bpy.context
    preferences = getattr(context, "preferences", None)
    if preferences is None:
        return None

    for addon_id in _ADDON_PREFERENCE_IDS:
        addon = preferences.addons.get(addon_id)
        if addon is not None:
            return addon.preferences
    return None


def _existing_directory(path: str) -> str:
    value = bpy.path.abspath(str(path or "").strip())
    return os.path.normpath(value) if value and os.path.isdir(value) else ""


def get_active_mod_root(context=None) -> str:
    prefs = get_addon_preferences(context)
    if prefs is not None:
        for attr_name in ("module_path", "dow2_path"):
            path = _existing_directory(getattr(prefs, attr_name, ""))
            if path:
                return path
    return _existing_directory(DEFAULT_DOW2_RETRIBUTION_PATH)


def get_active_data_root(context=None) -> str:
    root = get_active_mod_root(context)
    if not root:
        return ""
    data_root = os.path.join(root, "data")
    return os.path.normpath(data_root) if os.path.isdir(data_root) else root


def get_file_browser_start_path(context=None, *subdirs: str) -> str:
    root = get_active_mod_root(context)
    if not root:
        return ""
    if subdirs:
        candidate = os.path.join(root, *subdirs)
        if os.path.isdir(candidate):
            return os.path.normpath(candidate)
    return root


def get_shader_browser_start_path(context=None) -> str:
    root = get_active_mod_root(context)
    if not root:
        return ""
    shader_root = os.path.join(root, "data", "shaders")
    if os.path.isdir(shader_root):
        return os.path.normpath(shader_root)
    return root


def set_file_browser_start(operator, context=None, *subdirs: str, attr_name: str = "filepath") -> None:
    if str(getattr(operator, attr_name, "") or "").strip():
        return
    start_path = get_file_browser_start_path(context, *subdirs)
    if start_path:
        setattr(operator, attr_name, start_path + os.sep)


def load_persisted_settings(context, attr_name: str) -> dict:
    prefs = get_addon_preferences(context)
    if prefs is None:
        return {}

    raw_value = str(getattr(prefs, attr_name, "") or "").strip()
    if not raw_value:
        return {}

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}

    return payload if isinstance(payload, dict) else {}


def store_persisted_settings(context, attr_name: str, payload: dict) -> None:
    prefs = get_addon_preferences(context)
    if prefs is None:
        return

    setattr(prefs, attr_name, json.dumps(payload, separators=(",", ":"), sort_keys=True))
    save_user_preferences()

# Shared coordinate conversion matrix (Blender/Max to DirectX)
BLENDER_TO_DX = Matrix((
    (-1, 0, 0, 0),
    (0, 0, 1, 0),
    (0, -1, 0, 0),
    (0, 0, 0, 1),
))


def blender_to_dx_matrix(matrix: Matrix) -> Matrix:
    """Convert Blender matrix to DirectX coordinates."""
    return BLENDER_TO_DX @ matrix @ BLENDER_TO_DX.inverted()


def dx_to_blender_matrix(matrix: Matrix) -> Matrix:
    """Convert DirectX matrix to Blender coordinates."""
    return BLENDER_TO_DX.inverted() @ matrix @ BLENDER_TO_DX


def blender_to_dx_position(pos: Vector) -> Tuple[float, float, float]:
    """Convert Blender position to DirectX."""
    return (-pos.x, pos.z, -pos.y)


def dx_to_blender_position(pos: Vector) -> Vector:
    """Convert DirectX position to Blender."""
    return Vector((-pos.x, -pos.z, pos.y))


def pack_vector(vector: Tuple[float, float, float]) -> bytes:
    """Pack vector to 4 bytes (MaxScript PackVector equivalent)."""
    result = [0, 0, 0, 0]

    for i in range(3):
        value = int(vector[i] * 127)
        if value <= 0:
            value = -value
            value = (~value) & 0xFF
        value ^= 0x80
        result[i] = value & 0xFF

    return bytes(result)


def unpack_vector(b: List[int]) -> Vector:
    """Unpack byte-encoded normal/tangent/binormal (MaxScript UnpackVector)."""
    vector = [0.0, 0.0, 0.0]

    for i in range(3):
        val = b[i]
        sign = (val & 0x80) != 0
        value = val & 0x7F

        if not sign:
            value = (~value) & 0x7F
            value = -value

        vector[i] = value / 127.0

    return Vector(vector)


def clear_scene(include_collections: bool = True) -> None:
    """Remove objects and orphaned data; optionally clear unused collections."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for arm in list(bpy.data.armatures):
        if arm.users == 0:
            bpy.data.armatures.remove(arm)

    if include_collections:
        _clear_non_root_collections(bpy.context.scene)


def _clear_non_root_collections(scene: bpy.types.Scene) -> None:
    """Remove every collection except the active scene root collection."""
    root_collection = scene.collection

    changed = True
    while changed:
        changed = False
        for collection in list(bpy.data.collections):
            if collection == root_collection:
                continue

            for parent in list(bpy.data.collections):
                child = parent.children.get(collection.name)
                if child is not None:
                    parent.children.unlink(child)

            for any_scene in bpy.data.scenes:
                scene_root = any_scene.collection
                child = scene_root.children.get(collection.name)
                if child is not None:
                    scene_root.children.unlink(child)

            root_child = root_collection.children.get(collection.name)
            if root_child is not None:
                root_collection.children.unlink(root_child)

            if collection.users == 0:
                bpy.data.collections.remove(collection)
                changed = True


def find_object_by_name(name: str, obj_type: Optional[str] = None):
    """Return object by name, optionally filtering by type."""
    obj = bpy.data.objects.get(name)
    if obj and (obj_type is None or obj.type == obj_type):
        return obj
    return None


def link_object_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    """Ensure object is linked to the given collection."""
    if collection and obj.name not in collection.objects:
        collection.objects.link(obj)


__all__ = [
    "blender_to_dx_matrix",
    "blender_to_dx_position",
    "clear_scene",
    "dx_to_blender_matrix",
    "dx_to_blender_position",
    "find_object_by_name",
    "get_active_data_root",
    "get_active_mod_root",
    "get_addon_preferences",
    "get_file_browser_start_path",
    "get_shader_browser_start_path",
    "link_object_to_collection",
    "load_persisted_settings",
    "pack_vector",
    "save_user_preferences",
    "set_file_browser_start",
    "store_persisted_settings",
    "unpack_vector",
]
