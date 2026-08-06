import json
import os
from typing import Optional

import bpy
from bpy.app.handlers import persistent

from .batch_utils import BatchImportRecord, write_batch_import_sidecars


def build_import_record(animation_name: str, result) -> BatchImportRecord:
    """Build a sidecar record from a successful import result."""
    return BatchImportRecord(
        animation_name=animation_name,
        bone_names=result.referenced_bones,
        tracked_bone_names=result.tracked_bones,
        missing_bones=result.missing_bones,
    )


def write_single_import_sidecars(output_directory: str, record: BatchImportRecord):
    """Write single-import sidecar files into the target directory."""
    grouped_sidecar_paths = write_batch_import_sidecars(output_directory, [record])
    return grouped_sidecar_paths.get("", next(iter(grouped_sidecar_paths.values()), {}))


def queue_pending_single_import_sidecars(scene: bpy.types.Scene, record: BatchImportRecord):
    """Store pending single-import sidecar data until the scene is saved."""
    scene.dow2_pending_single_import_sidecars = True
    scene.dow2_pending_single_import_animation_name = record.animation_name
    scene.dow2_pending_single_import_bone_names = json.dumps(record.bone_names)
    scene.dow2_pending_single_import_tracked_bone_names = json.dumps(record.tracked_bone_names)
    scene.dow2_pending_single_import_missing_bones = json.dumps(record.missing_bones)


def clear_pending_single_import_sidecars(scene: bpy.types.Scene):
    """Clear pending single-import sidecar state from the scene."""
    scene.dow2_pending_single_import_sidecars = False
    scene.dow2_pending_single_import_animation_name = ""
    scene.dow2_pending_single_import_bone_names = ""
    scene.dow2_pending_single_import_tracked_bone_names = ""
    scene.dow2_pending_single_import_missing_bones = ""


def get_pending_single_import_record(scene: bpy.types.Scene) -> Optional[BatchImportRecord]:
    """Deserialize a pending single-import sidecar record from the scene."""
    if not scene.dow2_pending_single_import_sidecars:
        return None

    try:
        return BatchImportRecord(
            animation_name=scene.dow2_pending_single_import_animation_name,
            bone_names=json.loads(scene.dow2_pending_single_import_bone_names or "[]"),
            tracked_bone_names=json.loads(scene.dow2_pending_single_import_tracked_bone_names or "[]"),
            missing_bones=json.loads(scene.dow2_pending_single_import_missing_bones or "[]"),
        )
    except json.JSONDecodeError:
        clear_pending_single_import_sidecars(scene)
        return None


def write_pending_single_import_sidecars(scene: bpy.types.Scene):
    """Write any pending single-import sidecars after the scene is saved."""
    record = get_pending_single_import_record(scene)
    if record is None or not bpy.data.filepath:
        return None

    output_directory = os.path.dirname(bpy.data.filepath)
    sidecar_paths = write_single_import_sidecars(output_directory, record)
    clear_pending_single_import_sidecars(scene)
    return sidecar_paths


@persistent
def _dow2_single_import_save_post(_dummy):
    for scene in bpy.data.scenes:
        sidecar_paths = write_pending_single_import_sidecars(scene)
        if sidecar_paths:
            print(f"Wrote single import report: {sidecar_paths['report']}")
            print(f"Wrote single import rig list: {sidecar_paths['rig']}")
            print(f"Wrote single import tracks list: {sidecar_paths['tracks']}")


__all__ = [
    "_dow2_single_import_save_post",
    "build_import_record",
    "clear_pending_single_import_sidecars",
    "get_pending_single_import_record",
    "queue_pending_single_import_sidecars",
    "write_pending_single_import_sidecars",
    "write_single_import_sidecars",
]