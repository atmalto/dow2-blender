import bpy
from bpy.types import AddonPreferences

from .utils import save_user_preferences


_ADDON_ID = (__package__ or "dow2_tools").split(".", 1)[0]


def _save_preferences_update(_self, _context):
    save_user_preferences()


class DoW2ToolsPreferences(AddonPreferences):
    bl_idname = _ADDON_ID

    dow2_path: bpy.props.StringProperty(
        name="DoW2 Path",
        description="Path to Dawn of War 2 installation",
        subtype="DIR_PATH",
        default=r"C:\Program Files (x86)\Steam\steamapps\common\Dawn of War II - Retribution",
        update=_save_preferences_update,
    )

    module_path: bpy.props.StringProperty(
        name="Mod Folder",
        description="Path to the active DoW2 mod folder or custom data directory (optional)",
        subtype="DIR_PATH",
        default="",
        update=_save_preferences_update,
    )

    model_export_settings_json: bpy.props.StringProperty(
        default="",
        options={'HIDDEN'},
        update=_save_preferences_update,
    )

    model_import_settings_json: bpy.props.StringProperty(
        default="",
        options={'HIDDEN'},
        update=_save_preferences_update,
    )

    ragdoll_import_settings_json: bpy.props.StringProperty(
        default="",
        options={'HIDDEN'},
        update=_save_preferences_update,
    )

    animation_export_settings_json: bpy.props.StringProperty(
        default="",
        options={'HIDDEN'},
        update=_save_preferences_update,
    )

    batch_import_input_directory: bpy.props.StringProperty(
        name="Batch Import Input Folder",
        description="Folder containing .hkanim, .anim, or .hkx files to batch import",
        subtype="DIR_PATH",
        default="",
        update=_save_preferences_update,
    )

    batch_import_output_directory: bpy.props.StringProperty(
        name="Batch Import Output Folder",
        description="Folder where .blend files and sidecars are written during batch import",
        subtype="DIR_PATH",
        default="",
        update=_save_preferences_update,
    )

    batch_import_write_all_animations_blend: bpy.props.BoolProperty(
        name="Write all_animations.blend",
        description="After batch import finishes, build one combined all_animations.blend per output group in a background Blender process",
        default=False,
        update=_save_preferences_update,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "dow2_path")
        layout.prop(self, "module_path", text="Mod Folder")

        layout.separator()
        layout.operator("dow2.reload_addon", icon='RECOVER_LAST')


def register():
    bpy.utils.register_class(DoW2ToolsPreferences)


def unregister():
    if hasattr(bpy.types, DoW2ToolsPreferences.__name__):
        bpy.utils.unregister_class(DoW2ToolsPreferences)


__all__ = [
    "DoW2ToolsPreferences",
    "register",
    "unregister",
]