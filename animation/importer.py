"""Animation import operators and registration for DoW2."""

import os
from typing import List

import bpy

from ..utils import get_addon_preferences
from .batch_all_animations import (
    cache_saved_batch_blend,
    discard_cached_action,
    launch_all_animations_worker,
)
from .batch_utils import BatchImportRecord, reserve_output_path, write_batch_import_sidecars
from .hkanim import HkAnimToolError, collect_batch_animation_files
from .import_hkx import HkxAnimationImportError, HkxNonAnimationAssetError, load_hkx_animation
from .import_core import (
    ANIM_SIGNATURE,
    ANIM_VERSION,
    AnimationData,
    AnimationImportResult,
    AnimationReader,
    DoW2AnimationImporter,
)
from .import_utils import get_selected_armature_bone_names, resolve_batch_relative_animation_path
from .import_sidecars import (
    _dow2_single_import_save_post,
    build_import_record,
    clear_pending_single_import_sidecars,
    get_pending_single_import_record,
    queue_pending_single_import_sidecars,
    write_pending_single_import_sidecars,
    write_single_import_sidecars,
)


SUPPORTED_ANIMATION_EXTENSIONS = ('.anim', '.hkx')
_BATCH_IMPORT_INPUT_ATTR = "batch_import_input_directory"
_BATCH_IMPORT_OUTPUT_ATTR = "batch_import_output_directory"
_BATCH_IMPORT_ALL_ANIMATIONS_ATTR = "batch_import_write_all_animations_blend"


def _get_batch_import_directory_pref(context, attr_name: str) -> str:
    prefs = get_addon_preferences(context)
    if prefs is None:
        return ""
    return str(getattr(prefs, attr_name, "") or "")


def _set_batch_import_directories(context, *, input_directory=None, output_directory=None):
    prefs = get_addon_preferences(context)
    if prefs is None:
        return
    if input_directory is not None:
        prefs.batch_import_input_directory = input_directory
    if output_directory is not None:
        prefs.batch_import_output_directory = output_directory


def load_animation_file(filepath: str, armature=None):
    extension = os.path.splitext(filepath)[1].lower()
    if extension == '.anim':
        return AnimationReader(filepath).load()
    if extension == '.hkx':
        return load_hkx_animation(filepath, armature=armature)
    raise HkxAnimationImportError(f"Unsupported animation file type: {extension}")


class DOW2_OT_import_animation(bpy.types.Operator):
    """Import a single DoW2 animation file."""

    bl_idname = "import_scene.dow2_animation"
    bl_label = "Import DoW2 Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to .anim or .hkx file",
        subtype='FILE_PATH',
    )

    filter_glob: bpy.props.StringProperty(
        default="*.anim;*.hkx",
        options={'HIDDEN'},
    )

    import_selected_bones_only: bpy.props.BoolProperty(
        name="Selected Bones Only",
        description="Import animation only into currently selected bones on the target armature",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "import_selected_bones_only")

    def execute(self, context):
        print(f"Importing animation: {self.filepath}")

        importer = DoW2AnimationImporter(context)
        armature = importer.find_armature()
        if not armature:
            self.report({'ERROR'}, "No armature found. Import a .model file first.")
            return {'CANCELLED'}

        try:
            anim = load_animation_file(self.filepath, armature=armature)
        except HkxAnimationImportError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        if not anim:
            self.report({'ERROR'}, f"Failed to load animation: {self.filepath}")
            return {'CANCELLED'}

        selected_bone_names = None
        if self.import_selected_bones_only:
            selected_bone_names = get_selected_armature_bone_names(context, armature)
            if not selected_bone_names:
                self.report({'ERROR'}, "No bones selected on the target armature")
                return {'CANCELLED'}

        result = importer.import_animation(anim, armature, selected_bone_names=selected_bone_names)
        if not result.success:
            failure_reason = result.failure_reason or "Failed to import animation"
            self.report({'ERROR'}, failure_reason)
            return {'CANCELLED'}

        output_name = anim.name or os.path.splitext(os.path.basename(self.filepath))[0]
        record = build_import_record(output_name, result)

        if bpy.data.filepath:
            sidecar_paths = write_single_import_sidecars(os.path.dirname(bpy.data.filepath), record)
            print(f"Wrote single import report: {sidecar_paths['report']}")
            print(f"Wrote single import rig list: {sidecar_paths['rig']}")
            print(f"Wrote single import tracks list: {sidecar_paths['tracks']}")
        else:
            queue_pending_single_import_sidecars(context.scene, record)
            suggested_blend_path = os.path.join(os.path.dirname(self.filepath), f"{output_name}.blend")
            bpy.ops.wm.save_as_mainfile('INVOKE_DEFAULT', filepath=suggested_blend_path)

        if result.missing_bones:
            preview = ", ".join(result.missing_bones[:5])
            if len(result.missing_bones) > 5:
                preview = f"{preview}, ..."
            message = (
                f"Imported animation: {anim.name} ({result.frame_count} frames). Skipped {len(result.missing_bones)} missing bone(s): {preview}"
            )
            if self.import_selected_bones_only:
                message += f"; imported into {result.mapped_bone_count} selected bone(s)"
            if not bpy.data.filepath:
                message += "; save the scene to write sidecar files"
            self.report({'WARNING'}, message)
        else:
            message = f"Imported animation: {anim.name} ({result.frame_count} frames)"
            if self.import_selected_bones_only:
                message += f" into {result.mapped_bone_count} selected bone(s)"
            if not bpy.data.filepath:
                message += "; save the scene to write sidecar files"
            self.report({'INFO'}, message)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class DOW2_OT_batch_import_animations(bpy.types.Operator):
    """Batch import DoW2 animations from a directory."""

    bl_idname = "import_scene.dow2_animations_batch"
    bl_label = "Batch Import DoW2 Animations"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(
        name="Directory",
        description="Directory containing .anim or .hkx files",
        subtype='DIR_PATH',
    )

    filter_glob: bpy.props.StringProperty(
        default="*.anim;*.hkx",
        options={'HIDDEN'},
    )

    def resolve_directory(self, directory: str) -> str:
        if not directory:
            return ""
        return os.path.normpath(bpy.path.abspath(directory))

    def execute(self, context):
        input_directory = self.resolve_directory(self.directory or _get_batch_import_directory_pref(context, _BATCH_IMPORT_INPUT_ATTR))
        output_directory = self.resolve_directory(_get_batch_import_directory_pref(context, _BATCH_IMPORT_OUTPUT_ATTR))
        prefs = get_addon_preferences(context)
        write_all_animations_blend = bool(
            getattr(prefs, _BATCH_IMPORT_ALL_ANIMATIONS_ATTR, False)
            if prefs is not None
            else getattr(context.scene, "dow2_batch_import_write_all_animations_blend", False)
        )

        if not input_directory:
            self.report({'ERROR'}, "No input folder selected for batch import")
            return {'CANCELLED'}

        if not os.path.isdir(input_directory):
            self.report({'ERROR'}, f"Batch import input folder does not exist: {input_directory}")
            return {'CANCELLED'}

        if not output_directory:
            self.report({'ERROR'}, "No output folder selected for batch import")
            return {'CANCELLED'}

        context.scene.dow2_batch_import_input_directory = input_directory
        context.scene.dow2_batch_import_output_directory = output_directory
        context.scene.dow2_batch_import_write_all_animations_blend = write_all_animations_blend
        _set_batch_import_directories(
            context,
            input_directory=input_directory,
            output_directory=output_directory,
        )
        os.makedirs(output_directory, exist_ok=True)

        print(f"Batch importing from: {input_directory}")

        importer = DoW2AnimationImporter(context)
        armature = importer.find_armature()
        if not armature:
            self.report({'ERROR'}, "No armature found. Import a .model file first.")
            return {'CANCELLED'}

        try:
            batch_animation_files = collect_batch_animation_files(input_directory)
        except HkAnimToolError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        anim_files = batch_animation_files.files
        if not anim_files:
            batch_animation_files.cleanup()
            self.report({'WARNING'}, "No .hkanim, .anim, or .hkx files found in directory")
            return {'CANCELLED'}

        print(f"Found {len(anim_files)} animation files after applying per-folder format priority")
        if batch_animation_files.unpacked_hkanim_paths:
            print(f"Unpacked {len(batch_animation_files.unpacked_hkanim_paths)} .hkanim container(s) for batch import")

        imported_count = 0
        failed_count = 0
        skipped_non_animation_count = 0
        animations_with_missing_bones = 0
        batch_records: List[BatchImportRecord] = []
        used_output_paths: set[str] = set()
        cached_grouped_animations = {} if write_all_animations_blend else None

        try:
            for anim_path in anim_files:
                rel_path = resolve_batch_relative_animation_path(
                    anim_path,
                    input_directory,
                    batch_animation_files.unpack_root,
                )
                anim_name = os.path.splitext(os.path.basename(anim_path))[0]

                print(f"Importing: {rel_path}")

                try:
                    anim = load_animation_file(anim_path, armature=armature)
                except HkxNonAnimationAssetError as exc:
                    print(f"  Skipping non-animation HKX: {anim_path}: {exc}")
                    skipped_non_animation_count += 1
                    continue
                except HkxAnimationImportError as exc:
                    print(f"  Failed to load: {anim_path}: {exc}")
                    failed_count += 1
                    continue

                if not anim:
                    print(f"  Failed to load: {anim_path}")
                    failed_count += 1
                    continue

                importer.clear_animation(armature)
                result = importer.import_animation(anim, armature)
                if result.success:
                    imported_count += 1
                    desired_output_path = os.path.splitext(rel_path)[0]
                    output_path = reserve_output_path(used_output_paths, desired_output_path)
                    output_name = os.path.basename(output_path)
                    if output_path != desired_output_path:
                        print(f"  Duplicate animation path '{desired_output_path}' resolved to '{output_path}'")
                    if result.missing_bones:
                        animations_with_missing_bones += 1
                        print(f"  Skipped {len(result.missing_bones)} missing bone(s) while importing '{output_name}'")

                    batch_records.append(
                        BatchImportRecord(
                            animation_name=output_name,
                            relative_output_path=output_path,
                            bone_names=result.referenced_bones,
                            tracked_bone_names=result.tracked_bones,
                            missing_bones=result.missing_bones,
                        )
                    )

                    blend_path = os.path.join(output_directory, f"{output_path}.blend")
                    os.makedirs(os.path.dirname(blend_path) or output_directory, exist_ok=True)
                    source_action = armature.animation_data.action if armature.animation_data else None
                    if cached_grouped_animations is not None:
                        action_name = source_action.name if source_action is not None else output_name
                        cache_saved_batch_blend(cached_grouped_animations, output_path, blend_path, action_name)
                    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)
                    print(f"  Saved: {blend_path}")
                    if cached_grouped_animations is not None:
                        importer.clear_animation(armature)
                        discard_cached_action(source_action)
                else:
                    failure_reason = result.failure_reason or "unknown import failure"
                    print(f"  Failed to import: {anim_path}: {failure_reason}")
                    failed_count += 1
        finally:
            importer.clear_animation(armature)
            batch_animation_files.cleanup()

        if batch_records:
            sidecar_paths = write_batch_import_sidecars(output_directory, batch_records)
            for group_path, group_sidecars in sorted(sidecar_paths.items(), key=lambda item: item[0].lower()):
                group_output_directory = os.path.join(output_directory, group_path) if group_path else output_directory
                print(f"Wrote batch sidecars for: {group_output_directory}")
                print(f"  Report: {group_sidecars['report']}")
                print(f"  Rig: {group_sidecars['rig']}")
                print(f"  Tracks: {group_sidecars['tracks']}")

        all_animation_set_count = 0
        if cached_grouped_animations:
            worker_launch = launch_all_animations_worker(cached_grouped_animations, output_directory)
            if worker_launch.get("launched"):
                all_animation_set_count = sum(1 for refs in cached_grouped_animations.values() if refs)
                print(f"Scheduled all_animations worker: {worker_launch['manifest_path']}")
                print(f"  Result manifest: {worker_launch['result_path']}")
                print(f"  Worker log: {worker_launch['log_path']}")
            else:
                print("Failed to launch all_animations worker")

        unpacked_hkanim_count = len(batch_animation_files.unpacked_hkanim_paths)
        all_animations_suffix = f", {all_animation_set_count} all_animations blend(s) scheduled" if write_all_animations_blend else ""
        if animations_with_missing_bones:
            self.report(
                {'WARNING'},
                f"Imported {imported_count} animations, {failed_count} failed, {skipped_non_animation_count} non-animation HKX skipped, {unpacked_hkanim_count} .hkanim unpacked, {animations_with_missing_bones} import(s) skipped missing bones{all_animations_suffix}",
            )
        else:
            self.report(
                {'INFO'},
                f"Imported {imported_count} animations, {failed_count} failed, {skipped_non_animation_count} non-animation HKX skipped, {unpacked_hkanim_count} .hkanim unpacked{all_animations_suffix}",
            )
        return {'FINISHED'}

    def invoke(self, context, event):
        stored_input_directory = _get_batch_import_directory_pref(context, _BATCH_IMPORT_INPUT_ATTR)
        if stored_input_directory:
            self.directory = stored_input_directory
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class DOW2_OT_clear_animation(bpy.types.Operator):
    """Clear all animation from the armature."""

    bl_idname = "dow2.clear_animation"
    bl_label = "Clear Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        importer = DoW2AnimationImporter(context)
        armature = importer.find_armature()
        if not armature:
            self.report({'ERROR'}, "No armature found")
            return {'CANCELLED'}

        importer.clear_animation(armature)
        self.report({'INFO'}, "Animation cleared")
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(DOW2_OT_import_animation.bl_idname, text="DoW2 Animation (.anim)")


def menu_func_import_batch(self, context):
    self.layout.operator(DOW2_OT_batch_import_animations.bl_idname, text="DoW2 Animations (Batch)")


classes = [
    DOW2_OT_import_animation,
    DOW2_OT_batch_import_animations,
    DOW2_OT_clear_animation,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dow2_batch_import_input_directory = bpy.props.StringProperty(
        name="Batch Import Input Folder",
        description="Folder containing .hkanim, .anim, or .hkx files to batch import",
        subtype='DIR_PATH',
        default="",
    )
    bpy.types.Scene.dow2_batch_import_output_directory = bpy.props.StringProperty(
        name="Batch Import Output Folder",
        description="Folder where .blend files, CSV configs, import_report.txt, .rig, and .tracks will be saved during batch import",
        subtype='DIR_PATH',
        default="",
    )
    bpy.types.Scene.dow2_batch_import_write_all_animations_blend = bpy.props.BoolProperty(
        name="Write all_animations.blend",
        description="After batch import finishes, build one combined all_animations.blend per output group in a background Blender process",
        default=False,
    )
    bpy.types.Scene.dow2_pending_single_import_sidecars = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.dow2_pending_single_import_animation_name = bpy.props.StringProperty(default="")
    bpy.types.Scene.dow2_pending_single_import_bone_names = bpy.props.StringProperty(default="")
    bpy.types.Scene.dow2_pending_single_import_tracked_bone_names = bpy.props.StringProperty(default="")
    bpy.types.Scene.dow2_pending_single_import_missing_bones = bpy.props.StringProperty(default="")
    if _dow2_single_import_save_post not in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.append(_dow2_single_import_save_post)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import_batch)


def unregister():
    if _dow2_single_import_save_post in bpy.app.handlers.save_post:
        bpy.app.handlers.save_post.remove(_dow2_single_import_save_post)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import_batch)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    del bpy.types.Scene.dow2_pending_single_import_missing_bones
    del bpy.types.Scene.dow2_pending_single_import_tracked_bone_names
    del bpy.types.Scene.dow2_pending_single_import_bone_names
    del bpy.types.Scene.dow2_pending_single_import_animation_name
    del bpy.types.Scene.dow2_pending_single_import_sidecars
    del bpy.types.Scene.dow2_batch_import_write_all_animations_blend
    del bpy.types.Scene.dow2_batch_import_output_directory
    del bpy.types.Scene.dow2_batch_import_input_directory
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


__all__ = [
    "ANIM_SIGNATURE",
    "ANIM_VERSION",
    "AnimationData",
    "AnimationImportResult",
    "AnimationReader",
    "DoW2AnimationImporter",
    "DOW2_OT_batch_import_animations",
    "DOW2_OT_clear_animation",
    "DOW2_OT_import_animation",
    "_dow2_single_import_save_post",
    "build_import_record",
    "clear_pending_single_import_sidecars",
    "get_pending_single_import_record",
    "queue_pending_single_import_sidecars",
    "register",
    "unregister",
    "write_pending_single_import_sidecars",
    "write_single_import_sidecars",
]