import os

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, CollectionProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup

from ..utils import get_addon_preferences
from ..animation.hkanim import (
    HkAnimToolError,
    build_default_pack_output_path,
    pack_hkanim_from_directory,
    unpack_hkanim_next_to_source,
)
from ..animation.rig_track_utils import (
    generate_scene_rig_track_settings,
    get_scene_csv_path,
    get_scene_name,
    load_scene_rig_track_settings,
    reset_scene_rig_track_settings,
    save_scene_rig_track_settings,
    set_scene_rig_track_flags,
)


class DOW2_RigTrackSettingItem(PropertyGroup):
    bone_name: StringProperty(name="Bone Name")
    rig_enabled: BoolProperty(name="Rig", default=True)
    track_enabled: BoolProperty(name="Track", default=True)


class DOW2_OT_refresh_rig_track_settings(Operator):
    """ Reload rig and track settings from last saved for this scene (saved .blend file required) """

    bl_idname = "dow2.refresh_rig_track_settings"
    bl_label = "Refresh Rig and Track Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        csv_path = get_scene_csv_path()
        if not bpy.data.filepath:
            self.report({'WARNING'}, "Save the .blend file first to load rig/track settings")
            return {'CANCELLED'}

        if load_scene_rig_track_settings(context.scene):
            self.report({'INFO'}, f"Loaded rig/track settings from {os.path.basename(csv_path)}")
        else:
            self.report({'WARNING'}, f"No matching config found: {os.path.basename(csv_path)}")
        return {'FINISHED'}


class DOW2_OT_save_rig_track_settings(Operator):
    """ Save current rig and track settings for this scene (saved .blend file required) """

    bl_idname = "dow2.save_rig_track_settings"
    bl_label = "Save Rig and Track Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'WARNING'}, "Save the .blend file first to save rig/track settings")
            return {'CANCELLED'}

        csv_path = save_scene_rig_track_settings(context.scene)
        if not csv_path:
            self.report({'ERROR'}, "Unable to resolve the scene CSV path")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Saved rig/track settings to {os.path.basename(csv_path)}")
        return {'FINISHED'}


class DOW2_OT_reset_rig_track_settings(Operator):
    """ Enabled rig/tracks for all bones (saved .blend file required) """

    bl_idname = "dow2.reset_rig_track_settings"
    bl_label = "Reset Rig and Track Settings"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        reset_scene_rig_track_settings(context.scene)
        self.report({'INFO'}, "Rig/track settings reset to enabled")
        return {'FINISHED'}


class DOW2_OT_generate_rig_track_settings(Operator):
    """Generate rig/track settings from the current scene and active action."""

    bl_idname = "dow2.generate_rig_track_settings"
    bl_label = "Generate Config Files From This Scene"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        csv_path, error_message = generate_scene_rig_track_settings(context.scene, context=context)
        if not csv_path:
            self.report({'WARNING'}, error_message)
            return {'CANCELLED'}

        self.report({'INFO'}, f"Generated rig/track settings in {os.path.basename(csv_path)}")
        return {'FINISHED'}


class DOW2_OT_create_rig_track_settings(Operator):
    """Create new animation config from your current skeleton, this will replace your current config."""

    bl_idname = "dow2.create_rig_track_settings"
    bl_label = "Create"
    bl_description = "Create new animation config from your current skeleton, this will replace your current config"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        csv_path, error_message = generate_scene_rig_track_settings(context.scene, context=context)
        if not csv_path:
            self.report({'WARNING'}, error_message)
            return {'CANCELLED'}

        self.report({'INFO'}, f"Created rig/track settings in {os.path.basename(csv_path)}")
        return {'FINISHED'}


class DOW2_OT_set_rig_track_flags(Operator):
    """Update rig or track flags in the current UI list without saving."""

    bl_idname = "dow2.set_rig_track_flags"
    bl_label = "Set Rig/Track Flags"
    bl_options = {'REGISTER', 'UNDO'}

    rig_enabled: bpy.props.BoolProperty(default=False)
    track_enabled: bpy.props.BoolProperty(default=False)
    apply_rig: bpy.props.BoolProperty(default=False)
    apply_track: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        if self.apply_rig:
            set_scene_rig_track_flags(context.scene, rig_enabled=self.rig_enabled)
        if self.apply_track:
            set_scene_rig_track_flags(context.scene, track_enabled=self.track_enabled)
        return {'FINISHED'}


class DOW2_OT_pack_hkanim(Operator):
    """Pack a folder of HKX animations into a .hkanim container."""

    bl_idname = "dow2.pack_hkanim"
    bl_label = "Pack .hkanim"
    bl_options = {'REGISTER'}

    directory: StringProperty(
        name="Directory",
        description="Folder containing root HKX files and optional one-level subset subfolders",
        subtype='DIR_PATH',
    )

    def execute(self, context):
        input_directory = os.path.normpath(bpy.path.abspath(self.directory))
        if not input_directory:
            self.report({'ERROR'}, "No folder selected for .hkanim packing")
            return {'CANCELLED'}

        if not os.path.isdir(input_directory):
            self.report({'ERROR'}, f"Selected folder does not exist: {input_directory}")
            return {'CANCELLED'}

        output_path = build_default_pack_output_path(input_directory, ensure_unique=True)
        try:
            packed_path = pack_hkanim_from_directory(input_directory, output_path)
        except HkAnimToolError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        print(f"Packed .hkanim: {packed_path}")
        self.report({'INFO'}, f"Packed .hkanim to {os.path.basename(packed_path)}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class DOW2_OT_unpack_hkanim(Operator):
    """Unpack a .hkanim file into a sibling folder of HKX files."""

    bl_idname = "dow2.unpack_hkanim"
    bl_label = "Unpack .hkanim"
    bl_options = {'REGISTER'}

    filepath: StringProperty(
        name="File Path",
        description="Path to a .hkanim file",
        subtype='FILE_PATH',
    )

    filter_glob: StringProperty(
        default="*.hkanim",
        options={'HIDDEN'},
    )

    def execute(self, context):
        input_path = os.path.normpath(bpy.path.abspath(self.filepath))
        if not input_path:
            self.report({'ERROR'}, "No .hkanim file selected")
            return {'CANCELLED'}

        if not os.path.isfile(input_path):
            self.report({'ERROR'}, f"Selected .hkanim does not exist: {input_path}")
            return {'CANCELLED'}

        try:
            output_directory = unpack_hkanim_next_to_source(input_path)
        except HkAnimToolError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        print(f"Unpacked .hkanim: {input_path} -> {output_directory}")
        self.report({'INFO'}, f"Unpacked .hkanim to {os.path.basename(output_directory)}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


@persistent
def _dow2_load_rig_track_settings(_dummy):
    scenes = getattr(bpy.data, "scenes", None)
    if scenes is None:
        return

    for scene in scenes:
        load_scene_rig_track_settings(scene)


@persistent
def _dow2_save_rig_track_settings(_dummy):
    scenes = getattr(bpy.data, "scenes", None)
    if scenes is None:
        return

    for scene in scenes:
        load_scene_rig_track_settings(scene)


def _deferred_load_rig_track_settings():
    scenes = getattr(bpy.data, "scenes", None)
    if scenes is None:
        return 0.1

    _dow2_load_rig_track_settings(None)
    return None


class DOW2_PT_animation_panel(Panel):
    """DoW2 Animation Panel"""

    bl_label = "Animation"
    bl_idname = "DOW2_PT_animation_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "DoW2"
    bl_order = 50
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = get_addon_preferences(context)
        batch_folder_target = prefs if prefs is not None else scene

        col = layout.column(align=True)
        col.label(text="Import:", icon="IMPORT")
        col.operator("import_scene.dow2_animation", text="Import Animation", icon="ACTION")
        col.operator("import_scene.dow2_animations_batch", text="Batch Import")

        batch_box = col.box()
        batch_col = batch_box.column(align=True)
        batch_col.label(text="Batch Import Folders:")
        batch_col.prop(batch_folder_target, "batch_import_input_directory" if prefs is not None else "dow2_batch_import_input_directory", text=".hkanim/.anim/.hkx input")
        batch_col.prop(batch_folder_target, "batch_import_output_directory" if prefs is not None else "dow2_batch_import_output_directory", text=".blend output")
        batch_col.prop(batch_folder_target, "batch_import_write_all_animations_blend" if prefs is not None else "dow2_batch_import_write_all_animations_blend", text="Write all_animations.blend")

        layout.separator()

        col = layout.column(align=True)
        col.label(text="Export:", icon="EXPORT")
        export_row = col.row(align=True)
        export_row.operator("export_anim.dow2_hkx", text="Export Current", icon="ACTION")
        export_row.operator("dow2.batch_export_anims", text="Batch Export")

        layout.separator()

        header, body = layout.panel("dow2_animation_hkanim_tools", default_closed=True)
        header.label(text=".hkanim")
        if body is not None:
            button_row = body.row(align=True)
            button_row.operator("dow2.pack_hkanim", text="Pack", icon="EXPORT")
            button_row.operator("dow2.unpack_hkanim", text="Unpack", icon="IMPORT")

        layout.separator()

        header, body = layout.panel("dow2_animation_rig_track_settings", default_closed=False)
        header.label(text="Rig and Track Settings")
        if body is not None:
            button_row = body.row(align=True)
            button_row.operator("dow2.refresh_rig_track_settings", text="Refresh", icon="FILE_REFRESH")
            button_row.operator("dow2.save_rig_track_settings", text="Save", icon="FILE_TICK")
            button_row.operator("dow2.reset_rig_track_settings", text="Reset", icon="LOOP_BACK")
            button_row.operator("dow2.create_rig_track_settings", text="Create", icon="FILE_NEW")

            toggle_row = body.row(align=True)
            op = toggle_row.operator("dow2.set_rig_track_flags", text="Track All")
            op.apply_track = True
            op.track_enabled = True

            op = toggle_row.operator("dow2.set_rig_track_flags", text="Track Off")
            op.apply_track = True
            op.track_enabled = False

            op = toggle_row.operator("dow2.set_rig_track_flags", text="Rig All")
            op.apply_rig = True
            op.rig_enabled = True

            op = toggle_row.operator("dow2.set_rig_track_flags", text="Rig Off")
            op.apply_rig = True
            op.rig_enabled = False

            settings_box = body.box()
            if not bpy.data.filepath:
                settings_box.label(text="Save the .blend to use rig/track settings", icon='INFO')
            else:
                if scene.dow2_rig_track_items:
                    table = settings_box.column(align=True)

                    header_row = table.row(align=True)
                    split = header_row.split(factor=0.7, align=True)
                    split.label(text="Bone")
                    flags = split.split(factor=0.45, align=True)

                    rig_col = flags.row(align=True)
                    rig_col.alignment = 'CENTER'
                    rig_col.label(text="Rig")

                    track_col = flags.row(align=True)
                    track_col.alignment = 'CENTER'
                    track_col.label(text="Track")

                    for item in scene.dow2_rig_track_items:
                        row = table.row(align=True)

                        split = row.split(factor=0.7, align=True)
                        split.label(text=item.bone_name)
                        flags = split.split(factor=0.45, align=True)

                        rig_col = flags.row(align=True)
                        rig_col.alignment = 'CENTER'
                        rig_col.prop(item, "rig_enabled", text="")

                        track_col = flags.row(align=True)
                        track_col.alignment = 'CENTER'
                        track_col.prop(item, "track_enabled", text="")
                else:
                    settings_box.operator(
                        "dow2.create_rig_track_settings",
                        text="Generate Config Files From This Scene",
                        icon='FILE_NEW',
                    )

            body.separator()

        armature = None
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                armature = obj
                break

        if armature and armature.animation_data:
            action = armature.animation_data.action
            if action:
                box = layout.box()
                box.label(text=f"Action: {action.name}")
                box.label(text=f"Range: {int(action.frame_range[0])} - {int(action.frame_range[1])}")
                box.label(text=f"FCurves: {len(action.fcurves)}")


ANIMATION_PANEL_CLASSES = [
    DOW2_RigTrackSettingItem,
    DOW2_OT_set_rig_track_flags,
    DOW2_OT_pack_hkanim,
    DOW2_OT_unpack_hkanim,
    DOW2_OT_refresh_rig_track_settings,
    DOW2_OT_save_rig_track_settings,
    DOW2_OT_reset_rig_track_settings,
    DOW2_OT_create_rig_track_settings,
    DOW2_OT_generate_rig_track_settings,
    DOW2_PT_animation_panel,
]


def register_animation_panel_state():
    bpy.types.Scene.dow2_rig_track_items = CollectionProperty(type=DOW2_RigTrackSettingItem)
    bpy.types.Scene.dow2_rig_track_loaded_csv_path = StringProperty(default="")
    if _dow2_load_rig_track_settings not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_dow2_load_rig_track_settings)
    if _dow2_save_rig_track_settings not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(_dow2_save_rig_track_settings)
    if not bpy.app.timers.is_registered(_deferred_load_rig_track_settings):
        bpy.app.timers.register(_deferred_load_rig_track_settings, first_interval=0.0)


def unregister_animation_panel_state():
    if _dow2_load_rig_track_settings in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_dow2_load_rig_track_settings)
    if _dow2_save_rig_track_settings in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_dow2_save_rig_track_settings)
    if bpy.app.timers.is_registered(_deferred_load_rig_track_settings):
        bpy.app.timers.unregister(_deferred_load_rig_track_settings)
    if hasattr(bpy.types.Scene, "dow2_rig_track_loaded_csv_path"):
        del bpy.types.Scene.dow2_rig_track_loaded_csv_path
    if hasattr(bpy.types.Scene, "dow2_rig_track_items"):
        del bpy.types.Scene.dow2_rig_track_items


__all__ = [
    "ANIMATION_PANEL_CLASSES",
    "DOW2_OT_create_rig_track_settings",
    "DOW2_OT_generate_rig_track_settings",
    "DOW2_OT_pack_hkanim",
    "DOW2_OT_refresh_rig_track_settings",
    "DOW2_OT_reset_rig_track_settings",
    "DOW2_OT_save_rig_track_settings",
    "DOW2_OT_set_rig_track_flags",
    "DOW2_OT_unpack_hkanim",
    "DOW2_PT_animation_panel",
    "DOW2_RigTrackSettingItem",
    "register_animation_panel_state",
    "unregister_animation_panel_state",
]