"""Animation export operators and registration for DoW2."""

import os

import bpy

from ..utils import load_persisted_settings, store_persisted_settings
from .batch_export_utils import ensure_batch_export_configs, run_parallel_batch_export_jobs
from .batch_utils import get_default_parallel_worker_count, get_parallel_worker_limit
from .export_core import (
    ensure_log_dir,
    export_animation,
    export_current_animation,
    find_selected_armature,
    gather_animation_data,
    gather_skeleton_data,
    get_addon_path,
    get_anim_blender2hkx_path,
    get_log_path,
    load_export_set_from_bone_file,
    load_export_sets_from_csv,
    log_error,
    log_info,
    log_message,
    log_warning,
    to_title_case,
)
from .rig_track_utils import get_scene_export_name_sets, get_scene_csv_path, parse_bone_name_file


_ANIMATION_EXPORT_SETTINGS_ATTR = "animation_export_settings_json"

_QUANTIZATION_ITEMS = [
    (str(bits), f"{bits}-bit", f"Use {bits}-bit quantization for animation compression")
    for bits in range(1, 17)
]

_BLOCK_SIZE_ITEMS = [
    ('4', '4', 'Compress animation in blocks of 4 poses'),
    ('8', '8', 'Compress animation in blocks of 8 poses (recommended)'),
    ('16', '16', 'Compress animation in blocks of 16 poses'),
    ('FULL', 'Full Clip', 'Compress the entire clip as one block'),
]


def _load_animation_export_settings(context) -> dict:
    return load_persisted_settings(context, _ANIMATION_EXPORT_SETTINGS_ATTR)


def _store_animation_export_settings(context, *, single_export=None, batch_export=None):
    settings = _load_animation_export_settings(context)
    if single_export is not None:
        settings["single_export"] = single_export
    if batch_export is not None:
        settings["batch_export"] = batch_export
    store_persisted_settings(context, _ANIMATION_EXPORT_SETTINGS_ATTR, settings)


def _apply_operator_settings(operator, payload: dict):
    for key, value in payload.items():
        if hasattr(operator, key):
            setattr(operator, key, value)


def _apply_operator_settings_with_guard(operator, payload: dict, guard_attr: str):
    setattr(operator, guard_attr, True)
    try:
        _apply_operator_settings(operator, payload)
    finally:
        setattr(operator, guard_attr, False)


def _single_export_settings_payload(operator) -> dict:
    return {
        "quantization_bits": operator.quantization_bits,
        "tolerance": operator.tolerance,
        "use_block_compression": operator.use_block_compression,
        "block_size": operator.block_size,
        "use_three_component_quaternions": operator.use_three_component_quaternions,
    }


def _batch_export_settings_payload(operator) -> dict:
    return {
        "use_global_rig_reference": operator.use_global_rig_reference,
        "use_global_track_reference": operator.use_global_track_reference,
        "parallel_workers": operator.parallel_workers,
        "quantization_bits": operator.quantization_bits,
        "tolerance": operator.tolerance,
        "use_block_compression": operator.use_block_compression,
        "block_size": operator.block_size,
        "use_three_component_quaternions": operator.use_three_component_quaternions,
    }


def _persist_single_animation_export_settings_update(operator, context):
    if getattr(operator, "_is_loading_single_animation_export_settings", False):
        return
    _store_animation_export_settings(context, single_export=_single_export_settings_payload(operator))


def _persist_batch_animation_export_settings_update(operator, context):
    if getattr(operator, "_is_loading_batch_animation_export_settings", False):
        return
    _store_animation_export_settings(context, batch_export=_batch_export_settings_payload(operator))


class EXPORT_OT_dow2_animation(bpy.types.Operator):
    """Export animation to DoW2 HKX format."""

    bl_idname = "export_anim.dow2_hkx"
    bl_label = "Export DoW2 Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to export HKX file",
        subtype='FILE_PATH',
    )

    filter_glob: bpy.props.StringProperty(
        default="*.hkx",
        options={'HIDDEN'},
    )

    quantization_bits: bpy.props.EnumProperty(
        name="Quantization",
        description="Bit depth for Havok animation quantization",
        items=_QUANTIZATION_ITEMS,
        default='8',
        update=_persist_single_animation_export_settings_update,
    )

    tolerance: bpy.props.FloatProperty(
        name="Tolerance",
        description="Compression tolerance. 0.0 = lossless, higher = smaller files with artifacts",
        default=0.0,
        min=0.0,
        max=0.1,
        precision=4,
        step=0.1,
        update=_persist_single_animation_export_settings_update,
    )

    use_block_compression: bpy.props.BoolProperty(
        name="Use Block Compression",
        description="Compress the animation in smaller pose blocks instead of one full-clip block",
        default=True,
        update=_persist_single_animation_export_settings_update,
    )

    block_size: bpy.props.EnumProperty(
        name="Block Size",
        description="Number of poses per Havok compression block",
        items=_BLOCK_SIZE_ITEMS,
        default='8',
        update=_persist_single_animation_export_settings_update,
    )

    use_three_component_quaternions: bpy.props.BoolProperty(
        name="Use 3-Component Quaternion Compression",
        description="Allow Havok to drop and reconstruct one quaternion component on safe rotation tracks",
        default=True,
        update=_persist_single_animation_export_settings_update,
    )

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text="Compression Settings:")
        box.prop(self, "quantization_bits")
        box.prop(self, "tolerance")
        box.prop(self, "use_block_compression")
        compression_row = box.row()
        compression_row.enabled = self.use_block_compression
        compression_row.prop(self, "block_size")
        box.prop(self, "use_three_component_quaternions")

        csv_path = get_scene_csv_path()
        box = layout.box()
        box.label(text="Rig/Track Source:")
        if os.path.exists(csv_path):
            box.label(text=os.path.basename(csv_path), icon='FILE')
        else:
            box.label(text="No CSV found. Export will derive settings from the current scene", icon='INFO')

    def invoke(self, context, event):
        settings = _load_animation_export_settings(context)
        _apply_operator_settings_with_guard(self, settings.get("single_export", {}), "_is_loading_single_animation_export_settings")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        _store_animation_export_settings(context, single_export=_single_export_settings_payload(self))

        if not self.filepath:
            self.report({'ERROR'}, "No file path specified")
            return {'CANCELLED'}

        if not self.filepath.lower().endswith('.hkx'):
            self.filepath += '.hkx'

        armature_obj = find_selected_armature(context)
        if armature_obj is None:
            self.report({'ERROR'}, "Select or activate an armature before exporting")
            return {'CANCELLED'}

        csv_path = get_scene_csv_path()
        export_bones = None
        export_tracks = None
        missing_names = []
        if csv_path and os.path.exists(csv_path):
            export_bones, export_tracks, missing_names = load_export_sets_from_csv(armature_obj, csv_path)
            if export_bones is None or export_tracks is None:
                self.report({'ERROR'}, f"Missing CSV config for export: {csv_path}")
                return {'CANCELLED'}
        else:
            export_bones, export_tracks, error_message = get_scene_export_name_sets(
                context.scene,
                context=context,
                armature_obj=armature_obj,
            )
            if export_bones is None or export_tracks is None:
                self.report({'ERROR'}, error_message)
                return {'CANCELLED'}
            log_info("Single export: no CSV found, deriving rig/track settings from the current scene")

        if missing_names:
            preview = ", ".join(sorted(set(missing_names))[:10])
            if len(set(missing_names)) > 10:
                preview += ", ..."
            log_warning(f"Single export: some configured bones were not found in the armature: {preview}")

        quantization_bits = int(self.quantization_bits)
        tolerance = self.tolerance
        use_block_compression = self.use_block_compression
        block_size = 0 if self.block_size == 'FULL' else int(self.block_size)
        use_three_component_quaternions = self.use_three_component_quaternions

        if export_current_animation(
            self.filepath,
            export_bones,
            export_tracks,
            quantization_bits=quantization_bits,
            tolerance=tolerance,
            use_block_compression=use_block_compression,
            block_size=block_size,
            use_three_component_quaternions=use_three_component_quaternions,
        ):
            self.report({'INFO'}, f"Exported animation to {self.filepath}")
            return {'FINISHED'}

        self.report({'ERROR'}, "Failed to export animation")
        return {'CANCELLED'}


class DOW2_OT_batch_import_anims(bpy.types.Operator):
    """Batch import .anim files to .blend files."""

    bl_idname = "dow2.batch_import_anims"
    bl_label = "Batch Import Animations"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(
        name="Directory",
        description="Directory containing .anim files",
        subtype='DIR_PATH',
    )

    def invoke(self, context, event):
        settings = _load_animation_export_settings(context)
        _apply_operator_settings(self, settings.get("batch_export", {}))
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        _store_animation_export_settings(context, batch_export=_batch_export_settings_payload(self))

        if not self.directory:
            self.report({'ERROR'}, "No directory selected")
            return {'CANCELLED'}

        anim_files = []
        for file_name in os.listdir(self.directory):
            if file_name.lower().endswith('.anim'):
                anim_files.append(os.path.join(self.directory, file_name))

        if not anim_files:
            self.report({'WARNING'}, f"No .anim files found in {self.directory}")
            return {'CANCELLED'}

        log_info(f"Batch importing {len(anim_files)} animation files...")

        armature_obj = None
        for obj in context.scene.objects:
            if obj.type == 'ARMATURE':
                armature_obj = obj
                break

        if armature_obj:
            armature_bones = set(bone.name.lower() for bone in armature_obj.data.bones)
            log_info(f"Scene armature '{armature_obj.name}' has {len(armature_bones)} bones")
            all_missing_bones = set()
            bones_validated = False
        else:
            log_warning("No armature in scene - bone validation skipped")
            armature_bones = set()
            all_missing_bones = set()
            bones_validated = True

        success_count = 0
        for anim_path in anim_files:
            anim_name = os.path.splitext(os.path.basename(anim_path))[0]
            blend_path = os.path.join(self.directory, anim_name + ".blend")

            log_info(f"Importing: {anim_name}")

            try:
                bpy.ops.import_anim.dow2_anim(filepath=anim_path)

                if armature_obj and not bones_validated:
                    bones_validated = True
                    if armature_obj.animation_data and armature_obj.animation_data.action:
                        action = armature_obj.animation_data.action
                        anim_bones = set()
                        for fcurve in action.fcurves:
                            if fcurve.data_path.startswith('pose.bones["'):
                                bone_name = fcurve.data_path.split('"')[1]
                                anim_bones.add(bone_name)

                        for bone_name in sorted(anim_bones):
                            if bone_name.lower() in armature_bones:
                                log_info(f"  Bone '{bone_name}' found")
                            else:
                                log_warning(f"  Bone '{bone_name}' MISSING")
                                all_missing_bones.add(bone_name)

                bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)
                success_count += 1
                log_info(f"  Saved: {blend_path}")

            except Exception as exc:
                log_error(f"Failed to import {anim_name}: {exc}")

        log_info(f"Batch import complete: {success_count}/{len(anim_files)} successful")
        if all_missing_bones:
            log_warning(f"Missing bones summary: {', '.join(sorted(all_missing_bones))}")
            log_warning("Import additional models to add these bones to the scene.")

        self.report({'INFO'}, f"Imported {success_count}/{len(anim_files)} animations")
        return {'FINISHED'}


class DOW2_OT_batch_export_anims(bpy.types.Operator):
    """Batch export .blend files to .hkx files."""

    bl_idname = "dow2.batch_export_anims"
    bl_label = "Batch Export Animations"
    bl_options = {'REGISTER'}

    directory: bpy.props.StringProperty(
        name="Directory",
        description="Directory containing .blend files to export",
        subtype='DIR_PATH',
    )

    use_global_rig_reference: bpy.props.BoolProperty(
        name="Use Global Rig Reference",
        description="Ignores per-animation rig flags and uses canonical all bones reference: .rig",
        default=False,
        update=_persist_batch_animation_export_settings_update,
    )

    use_global_track_reference: bpy.props.BoolProperty(
        name="Use Global Track Reference",
        description="Ignores per-animation tracks flags and uses canonical all bones reference: .tracks",
        default=False,
        update=_persist_batch_animation_export_settings_update,
    )

    parallel_workers: bpy.props.IntProperty(
        name="Worker Processes",
        description="Number of background Blender processes to use for batch export",
        min=1,
        max=get_parallel_worker_limit(),
        default=get_default_parallel_worker_count(),
        update=_persist_batch_animation_export_settings_update,
    )

    quantization_bits: bpy.props.EnumProperty(
        name="Quantization",
        description="Bit depth for Havok animation quantization",
        items=_QUANTIZATION_ITEMS,
        default='8',
        update=_persist_batch_animation_export_settings_update,
    )

    tolerance: bpy.props.FloatProperty(
        name="Tolerance",
        description="Compression tolerance. 0.0 = lossless, higher = smaller files with artifacts",
        default=0.0,
        min=0.0,
        max=0.1,
        precision=4,
        step=0.1,
        update=_persist_batch_animation_export_settings_update,
    )

    use_block_compression: bpy.props.BoolProperty(
        name="Use Block Compression",
        description="Compress animations in smaller pose blocks instead of one full-clip block",
        default=True,
        update=_persist_batch_animation_export_settings_update,
    )

    block_size: bpy.props.EnumProperty(
        name="Block Size",
        description="Number of poses per Havok compression block",
        items=_BLOCK_SIZE_ITEMS,
        default='8',
        update=_persist_batch_animation_export_settings_update,
    )

    use_three_component_quaternions: bpy.props.BoolProperty(
        name="Use 3-Component Quaternion Compression",
        description="Allow Havok to drop and reconstruct one quaternion component on safe rotation tracks",
        default=True,
        update=_persist_batch_animation_export_settings_update,
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Compression Settings:")
        box.prop(self, "quantization_bits")
        box.prop(self, "tolerance")
        box.prop(self, "use_block_compression")
        compression_row = box.row()
        compression_row.enabled = self.use_block_compression
        compression_row.prop(self, "block_size")
        box.prop(self, "use_three_component_quaternions")

        layout.prop(self, "use_global_rig_reference")
        layout.prop(self, "use_global_track_reference")
        layout.prop(self, "parallel_workers", slider=True)

    def invoke(self, context, event):
        settings = _load_animation_export_settings(context)
        _apply_operator_settings_with_guard(self, settings.get("batch_export", {}), "_is_loading_batch_animation_export_settings")
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        _store_animation_export_settings(context, batch_export=_batch_export_settings_payload(self))

        if not self.directory:
            self.report({'ERROR'}, "No directory selected")
            return {'CANCELLED'}

        blend_files = []
        for file_name in os.listdir(self.directory):
            if file_name.lower().endswith('.blend'):
                blend_files.append(os.path.join(self.directory, file_name))

        if not blend_files:
            self.report({'WARNING'}, f"No .blend files found in {self.directory}")
            return {'CANCELLED'}

        worker_count = max(1, min(self.parallel_workers, len(blend_files), get_parallel_worker_limit()))
        quantization_bits = int(self.quantization_bits)
        tolerance = self.tolerance
        use_block_compression = self.use_block_compression
        block_size = 0 if self.block_size == 'FULL' else int(self.block_size)
        use_three_component_quaternions = self.use_three_component_quaternions
        log_info(
            f"Batch exporting {len(blend_files)} blend files to HKX using {worker_count} worker process(es) "
            f"({quantization_bits}-bit, tolerance={tolerance}, "
            f"block_compression={use_block_compression}, block_size={self.block_size}, "
            f"three_component_quats={use_three_component_quaternions})..."
        )

        config_result = ensure_batch_export_configs(blend_files, self.directory)
        if config_result.get("fatal_error"):
            self.report({'ERROR'}, config_result["fatal_error"])
            return {'CANCELLED'}

        global_rig_path = os.path.join(self.directory, ".rig")
        global_track_path = os.path.join(self.directory, ".tracks")

        if self.use_global_rig_reference:
            global_rig_names = parse_bone_name_file(global_rig_path)
            if not global_rig_names:
                self.report({'ERROR'}, f"Global rig file not found or empty: {global_rig_path}")
                return {'CANCELLED'}

        if self.use_global_track_reference:
            global_track_names = parse_bone_name_file(global_track_path)
            if not global_track_names:
                self.report({'ERROR'}, f"Global tracks file not found or empty: {global_track_path}")
                return {'CANCELLED'}

        result = run_parallel_batch_export_jobs(
            blend_files,
            self.directory,
            use_global_rig_reference=self.use_global_rig_reference,
            use_global_track_reference=self.use_global_track_reference,
            quantization_bits=quantization_bits,
            tolerance=tolerance,
            use_block_compression=use_block_compression,
            block_size=block_size,
            use_three_component_quaternions=use_three_component_quaternions,
            worker_count=worker_count,
        )

        success_count = result["success_count"]
        failure_count = len(result["failed_blends"])
        log_info(f"Batch export complete: {success_count}/{len(blend_files)} successful")
        if result.get("fatal_error"):
            self.report({'ERROR'}, result["fatal_error"])
            return {'CANCELLED'}

        if failure_count:
            self.report({'WARNING'}, f"Exported {success_count}/{len(blend_files)} animations using {worker_count} worker process(es)")
        else:
            self.report({'INFO'}, f"Exported {success_count}/{len(blend_files)} animations using {worker_count} worker process(es)")
        return {'FINISHED'}


def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_dow2_animation.bl_idname, text="DoW2 Animation (.hkx)")
    self.layout.operator(DOW2_OT_batch_export_anims.bl_idname, text="DoW2 Batch Animations (.hkx)")


classes = [
    EXPORT_OT_dow2_animation,
    DOW2_OT_batch_import_anims,
    DOW2_OT_batch_export_anims,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


__all__ = [
    "EXPORT_OT_dow2_animation",
    "DOW2_OT_batch_export_anims",
    "DOW2_OT_batch_import_anims",
    "ensure_log_dir",
    "export_animation",
    "export_current_animation",
    "find_selected_armature",
    "gather_animation_data",
    "gather_skeleton_data",
    "get_addon_path",
    "get_anim_blender2hkx_path",
    "get_log_path",
    "load_export_set_from_bone_file",
    "load_export_sets_from_csv",
    "log_error",
    "log_info",
    "log_message",
    "log_warning",
    "register",
    "to_title_case",
    "unregister",
]