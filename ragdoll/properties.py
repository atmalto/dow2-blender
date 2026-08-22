from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import PropertyGroup

from .authoring import BODY_SHAPE_ITEMS
from .field_specs import EXPOSED_FIELD_SPECS, TEMPLATE_DRIVEN_FIELDS
from .templates import list_template_bones, list_template_folders, list_template_models, load_template_library
from ..utils import load_persisted_settings, store_persisted_settings


_RAGDOLL_IMPORT_SETTINGS_ATTR = "ragdoll_import_settings_json"
_RAGDOLL_IMPORT_PATH_STORAGE_KEY = "_ragdoll_import_path"
_RAGDOLL_MODEL_PATH_STORAGE_KEY = "_ragdoll_model_path"


def _get_persisted_ragdoll_import_value(settings, persisted_key: str, storage_key: str) -> str:
    current_value = str(settings.get(storage_key, "") or "")
    if current_value:
        return current_value
    payload = load_persisted_settings(bpy.context, _RAGDOLL_IMPORT_SETTINGS_ATTR)
    return str(payload.get(persisted_key, "") or "")


def _set_persisted_ragdoll_import_value(settings, value: str, persisted_key: str, storage_key: str) -> None:
    text = str(value or "")
    settings[storage_key] = text
    payload = load_persisted_settings(bpy.context, _RAGDOLL_IMPORT_SETTINGS_ATTR)
    payload[persisted_key] = text
    store_persisted_settings(bpy.context, _RAGDOLL_IMPORT_SETTINGS_ATTR, payload)


def _get_ragdoll_import_path(settings) -> str:
    return _get_persisted_ragdoll_import_value(settings, "ragdoll_import_path", _RAGDOLL_IMPORT_PATH_STORAGE_KEY)


def _set_ragdoll_import_path(settings, value: str) -> None:
    _set_persisted_ragdoll_import_value(settings, value, "ragdoll_import_path", _RAGDOLL_IMPORT_PATH_STORAGE_KEY)


def _get_ragdoll_model_path(settings) -> str:
    return _get_persisted_ragdoll_import_value(settings, "ragdoll_model_path", _RAGDOLL_MODEL_PATH_STORAGE_KEY)


def _set_ragdoll_model_path(settings, value: str) -> None:
    _set_persisted_ragdoll_import_value(settings, value, "ragdoll_model_path", _RAGDOLL_MODEL_PATH_STORAGE_KEY)


def _update_constraint_preview_settings(self, context):
    from .authoring.preview import sync_constraint_preview_objects

    sync_constraint_preview_objects()


def _template_model_items(self, context):
    try:
        models = list_template_models()
    except Exception:
        return [("__ERROR__", "Template Load Failed", "The frozen ragdoll template library could not be loaded")]
    return [(model, model, model) for model in models] or [("__NONE__", "No Models Found", "The frozen ragdoll template library is empty")]


def _template_folder_items(self, context):
    model = (self.template_model or "").strip()
    if not model or model.startswith("__"):
        return [("__NONE__", "Choose Model First", "Select a template model before choosing a folder")]
    try:
        folders = list_template_folders(model)
    except Exception:
        return [("__ERROR__", "Template Load Failed", "The frozen ragdoll template library could not be loaded")]
    return [(folder, folder, folder) for folder in folders] or [("__NONE__", "No Folders Found", "No template folders were found for the selected model")]


def _template_bone_items(self, context):
    model = (self.template_model or "").strip()
    folder = (self.template_folder or "").strip()
    if not model or model.startswith("__") or not folder or folder.startswith("__"):
        return [("__NONE__", "Choose Model And Folder First", "Select a template model and folder before choosing a bone")]
    try:
        bones = list_template_bones(model, folder)
    except Exception:
        return [("__ERROR__", "Template Load Failed", "The frozen ragdoll template library could not be loaded")]
    return [(bone, bone, bone) for bone in bones] or [("__NONE__", "No Bones Found", "No template bone names were found for the selected model and folder")]


class DOW2_RagdollSettings(PropertyGroup):
    preview_constraints: BoolProperty(
        name="Preview Constraints While Editing",
        description="Draw live constraint previews while editing, including parent-to-child arrows and angular limit overlays",
        default=True,
        update=_update_constraint_preview_settings,
    )

    preview_plane_min: BoolProperty(
        name="Preview Plane Min",
        description="Show the Plane Min clipping cone in the viewport preview and let it clip the main twist cone without changing the authored limit",
        default=True,
        update=_update_constraint_preview_settings,
    )

    preview_plane_max: BoolProperty(
        name="Preview Plane Max",
        description="Show the Plane Max clipping cone in the viewport preview and let it clip the main twist cone without changing the authored limit",
        default=True,
        update=_update_constraint_preview_settings,
    )

    ragdoll_name: StringProperty(
        name="Ragdoll Name",
        description="Name used for the generated ragdoll skeleton collection",
        default="ragdoll",
    )

    ragdoll_import_path: StringProperty(
        name="Ragdoll HKX",
        description="Path to the ragdoll HKX file to import",
        default="",
        get=_get_ragdoll_import_path,
        set=_set_ragdoll_import_path,
    )

    ragdoll_model_path: StringProperty(
        name="Companion Model",
        description="Path to the companion DoW2 .model used to build the imported authored ragdoll state",
        default="",
        get=_get_ragdoll_model_path,
        set=_set_ragdoll_model_path,
    )

    ragdoll_last_import_name: StringProperty(
        name="Last Imported Ragdoll",
        default="",
    )

    ragdoll_last_import_collection: StringProperty(
        name="Last Imported Collection",
        default="",
    )

    ragdoll_last_import_source_format: StringProperty(
        name="Last Import Source Format",
        default="",
    )

    ragdoll_last_import_body_count: IntProperty(
        name="Last Import Body Count",
        default=0,
        min=0,
    )

    ragdoll_last_import_constraint_count: IntProperty(
        name="Last Import Constraint Count",
        default=0,
        min=0,
    )

    template_model: EnumProperty(
        name="Model",
        description="Template model source used by the category preset loaders",
        items=_template_model_items,
    )

    template_folder: EnumProperty(
        name="Folder",
        description="Template folder source used by the category preset loaders",
        items=_template_folder_items,
    )

    template_bone: EnumProperty(
        name="Bone",
        description="Template bone source used by the category preset loaders",
        items=_template_bone_items,
    )

    json_export_path: StringProperty(
        name="JSON Path",
        description="Path for explicit ragdoll JSON export used for inspection and backend input",
        subtype="FILE_PATH",
        default="//dow2_ragdoll.json",
    )

    hkx_export_path: StringProperty(
        name="HKX Path",
        description="Path for native Havok 4.5.1 ragdoll HKX export",
        subtype="FILE_PATH",
        default="//dow2_ragdoll.hkx",
    )

    export_json_sidecar: BoolProperty(
        name="Write JSON Sidecar",
        description="Also write the explicit ragdoll JSON alongside HKX export",
        default=False,
    )

    auto_generate_missing_bodies: BoolProperty(
        name="Auto-generate Missing Bodies",
        description="The backend expects ragdoll bones to resolve to rigid bodies. When enabled, missing authored body objects fall back to generated export bodies. When disabled, export fails instead",
        default=True,
    )

    body_shape: EnumProperty(
        name="Body Shape",
        description="Preview body shape used when creating or updating ragdoll bodies",
        items=BODY_SHAPE_ITEMS,
        default="CAPSULE",
    )

    body_radius: FloatProperty(
        name="Radius",
        description="Default radius used when creating or updating selected ragdoll bodies",
        default=0.1,
        min=0.001,
        soft_max=2.0,
    )

    body_length: FloatProperty(
        name="Length",
        description="Default length used when creating or updating selected ragdoll bodies",
        default=0.4,
        min=0.001,
        soft_max=4.0,
    )


classes = [
    DOW2_RagdollSettings,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.dow2_ragdoll_settings = PointerProperty(type=DOW2_RagdollSettings)
    bpy.types.Scene.dow2_ragdoll_exposed_field_count = len(EXPOSED_FIELD_SPECS)
    bpy.types.Scene.dow2_ragdoll_template_field_count = len(TEMPLATE_DRIVEN_FIELDS)


def unregister():
    if hasattr(bpy.types.Scene, "dow2_ragdoll_settings"):
        del bpy.types.Scene.dow2_ragdoll_settings
    if hasattr(bpy.types.Scene, "dow2_ragdoll_exposed_field_count"):
        del bpy.types.Scene.dow2_ragdoll_exposed_field_count
    if hasattr(bpy.types.Scene, "dow2_ragdoll_template_field_count"):
        del bpy.types.Scene.dow2_ragdoll_template_field_count

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)