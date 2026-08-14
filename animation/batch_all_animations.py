"""Optional all_animations blend generation from saved per-animation blend outputs."""

import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List

import bpy

from .action_compat import action_has_fcurves, ensure_action_fcurve, iter_action_fcurves


ALL_ANIMATIONS_BLEND_NAME = "all_animations.blend"


@dataclass
class SavedBlendActionRef:
    blend_path: str
    action_name: str


@dataclass
class CachedAllAnimationsBuildResult:
    saved_blend_paths: Dict[str, str] = field(default_factory=dict)
    failed_animation_names: Dict[str, List[str]] = field(default_factory=dict)


def _get_group_path(relative_output_path: str) -> str:
    normalized_path = os.path.normpath(relative_output_path or "animation")
    group_path = os.path.dirname(normalized_path)
    return "" if group_path in ("", ".") else group_path


def cache_saved_batch_blend(
    grouped_blends: Dict[str, List[SavedBlendActionRef]],
    relative_output_path: str,
    blend_path: str,
    action_name: str,
):
    """Cache saved per-animation blend refs for end-of-batch all_animations building."""
    group_path = _get_group_path(relative_output_path)
    grouped_blends.setdefault(group_path, []).append(
        SavedBlendActionRef(blend_path=blend_path, action_name=action_name)
    )


def _build_action_name(group_path: str) -> str:
    if not group_path:
        return "all_animations"
    return f"{os.path.basename(group_path)}_all_animations"


def _get_or_create_target_curve(
    target_action: bpy.types.Action,
    target_datablock,
    target_curves: Dict[tuple[str, int], bpy.types.FCurve],
    source_fcurve: bpy.types.FCurve,
) -> bpy.types.FCurve:
    curve_key = (source_fcurve.data_path, source_fcurve.array_index)
    target_curve = target_curves.get(curve_key)
    if target_curve is not None:
        return target_curve

    target_curve = ensure_action_fcurve(
        target_action,
        target_datablock,
        source_fcurve.data_path,
        index=source_fcurve.array_index,
        group_name=source_fcurve.group.name if source_fcurve.group else "",
    )
    target_curve.auto_smoothing = source_fcurve.auto_smoothing
    target_curve.extrapolation = source_fcurve.extrapolation
    target_curve.color_mode = source_fcurve.color_mode
    target_curve.lock = source_fcurve.lock
    target_curve.mute = source_fcurve.mute
    target_curves[curve_key] = target_curve
    return target_curve


def _append_action_timeline(
    target_action: bpy.types.Action,
    target_datablock,
    target_curves: Dict[tuple[str, int], bpy.types.FCurve],
    source_action: bpy.types.Action,
    timeline_end: float,
) -> float:
    source_start = float(source_action.frame_range[0])
    source_end = float(source_action.frame_range[1])
    timeline_start = 0.0 if timeline_end < 0.0 else timeline_end + 1.0
    frame_offset = timeline_start - source_start

    for source_fcurve in iter_action_fcurves(source_action):
        source_points = source_fcurve.keyframe_points
        point_count = len(source_points)
        if point_count == 0:
            continue

        target_curve = _get_or_create_target_curve(target_action, target_datablock, target_curves, source_fcurve)
        start_index = len(target_curve.keyframe_points)
        target_curve.keyframe_points.add(point_count)

        for point_index, source_keyframe in enumerate(source_points):
            target_keyframe = target_curve.keyframe_points[start_index + point_index]
            target_keyframe.co = (source_keyframe.co[0] + frame_offset, source_keyframe.co[1])
            target_keyframe.handle_left = (
                source_keyframe.handle_left[0] + frame_offset,
                source_keyframe.handle_left[1],
            )
            target_keyframe.handle_right = (
                source_keyframe.handle_right[0] + frame_offset,
                source_keyframe.handle_right[1],
            )
            target_keyframe.interpolation = source_keyframe.interpolation
            target_keyframe.easing = source_keyframe.easing
            target_keyframe.back = source_keyframe.back
            target_keyframe.amplitude = source_keyframe.amplitude
            target_keyframe.period = source_keyframe.period
            target_keyframe.type = source_keyframe.type
            target_keyframe.handle_left_type = source_keyframe.handle_left_type
            target_keyframe.handle_right_type = source_keyframe.handle_right_type

        target_curve.update()

    return source_end + frame_offset


def discard_cached_action(action: bpy.types.Action | None):
    if action is None:
        return
    try:
        action.use_fake_user = False
    except ReferenceError:
        return
    try:
        bpy.data.actions.remove(action)
    except (ReferenceError, RuntimeError):
        return


def _load_action_from_blend(blend_path: str, action_name: str) -> bpy.types.Action | None:
    loaded_actions = []
    with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
        if action_name in data_from.actions:
            data_to.actions = [action_name]
            loaded_actions = data_to.actions
    return loaded_actions[0] if loaded_actions else None


def _get_addon_core_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def _find_scene_armature() -> bpy.types.Object | None:
    context = bpy.context
    if context.active_object and context.active_object.type == 'ARMATURE':
        return context.active_object
    for obj in context.scene.objects:
        if obj.type == 'ARMATURE':
            return obj
    return None


def run_all_animations_worker(manifest_path: str) -> int:
    """Background Blender worker entry point for building all_animations blends."""
    result_path = ""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)

        result_path = manifest["result_path"]
        output_directory = manifest["output_directory"]
        grouped_refs_payload = manifest["grouped_blends"]

        result = CachedAllAnimationsBuildResult()
        for group_path, refs_payload in grouped_refs_payload.items():
            if not refs_payload:
                continue

            print(f"[all_animations] building group '{group_path or '<root>'}' with {len(refs_payload)} clip(s)")

            base_blend_path = refs_payload[0]["blend_path"]
            bpy.ops.wm.open_mainfile(
                filepath=base_blend_path,
                load_ui=False,
                use_scripts=False,
                display_file_selector=False,
            )
            armature = _find_scene_armature()
            if armature is None:
                result.failed_animation_names.setdefault(group_path, []).extend(
                    ref["action_name"] for ref in refs_payload
                )
                continue

            combined_action = bpy.data.actions.new(name=_build_action_name(group_path))
            target_curves: Dict[tuple[str, int], bpy.types.FCurve] = {}
            timeline_end = -1.0
            base_action = armature.animation_data.action if armature.animation_data else None
            try:
                if armature.animation_data is None:
                    armature.animation_data_create()
                armature.animation_data.action = combined_action

                if base_action is not None:
                    print(f"[all_animations] appending base action '{base_action.name}'")
                    timeline_end = _append_action_timeline(combined_action, armature, target_curves, base_action, timeline_end)
                else:
                    result.failed_animation_names.setdefault(group_path, []).append(refs_payload[0]["action_name"])

                for ref_payload in refs_payload[1:]:
                    print(f"[all_animations] appending '{ref_payload['action_name']}'")
                    source_action = _load_action_from_blend(ref_payload["blend_path"], ref_payload["action_name"])
                    if source_action is None:
                        result.failed_animation_names.setdefault(group_path, []).append(ref_payload["action_name"])
                        continue
                    timeline_end = _append_action_timeline(combined_action, armature, target_curves, source_action, timeline_end)
                    discard_cached_action(source_action)

                if not action_has_fcurves(combined_action):
                    continue

                armature.animation_data.action = combined_action
                bpy.context.scene.frame_start = 0
                bpy.context.scene.frame_end = max(0, int(math.ceil(timeline_end)))
                bpy.context.scene.frame_current = 0

                blend_path = (
                    os.path.join(output_directory, group_path, ALL_ANIMATIONS_BLEND_NAME)
                    if group_path else os.path.join(output_directory, ALL_ANIMATIONS_BLEND_NAME)
                )
                os.makedirs(os.path.dirname(blend_path) or output_directory, exist_ok=True)
                bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)
                result.saved_blend_paths[group_path] = blend_path
            finally:
                if armature.animation_data and armature.animation_data.action == combined_action:
                    armature.animation_data.action = None
                discard_cached_action(combined_action)

        with open(result_path, 'w', encoding='utf-8') as handle:
            json.dump(
                {
                    "status": "completed",
                    "saved_blend_paths": result.saved_blend_paths,
                    "failed_animation_names": result.failed_animation_names,
                },
                handle,
            )
        return 0
    except Exception as exc:
        if result_path:
            with open(result_path, 'w', encoding='utf-8') as handle:
                json.dump(
                    {
                        "status": "failed",
                        "saved_blend_paths": {},
                        "failed_animation_names": {"": [str(exc)]},
                    },
                    handle,
                )
        return 1


def launch_all_animations_worker(
    grouped_blends: Dict[str, List[SavedBlendActionRef]],
    output_directory: str,
):
    """Launch a detached Blender worker that builds all_animations blends from saved outputs."""
    if not grouped_blends:
        return {"launched": False, "result_path": "", "manifest_path": "", "log_path": ""}

    blender_binary = bpy.app.binary_path
    addon_core_path = _get_addon_core_path()
    temp_dir = tempfile.mkdtemp(prefix="dow2_all_animations_")
    result_path = os.path.join(output_directory, "all_animations_worker_result.json")
    manifest_path = os.path.join(temp_dir, "manifest.json")
    log_path = os.path.join(output_directory, "all_animations_worker.log")
    manifest = {
        "output_directory": output_directory,
        "result_path": result_path,
        "grouped_blends": {
            group_path: [
                {"blend_path": ref.blend_path, "action_name": ref.action_name}
                for ref in refs
            ]
            for group_path, refs in grouped_blends.items()
        },
    }
    with open(manifest_path, 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle)

    with open(result_path, 'w', encoding='utf-8') as handle:
        json.dump(
            {
                "status": "queued",
                "saved_blend_paths": {},
                "failed_animation_names": {},
            },
            handle,
        )

    python_expr = (
        f"import sys; sys.path.insert(0, {addon_core_path!r}); "
        f"from dow2_tools.animation.batch_all_animations import run_all_animations_worker; "
        f"raise SystemExit(run_all_animations_worker({manifest_path!r}))"
    )

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path, 'a', encoding='utf-8') as log_handle:
        process = subprocess.Popen(
            [
                blender_binary,
                "--background",
                "--factory-startup",
                "--python-exit-code",
                "1",
                "--python-expr",
                python_expr,
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            creationflags=creation_flags,
        )

    return {
        "launched": process.poll() is None,
        "manifest_path": manifest_path,
        "result_path": result_path,
        "log_path": log_path,
    }


__all__ = [
    "ALL_ANIMATIONS_BLEND_NAME",
    "SavedBlendActionRef",
    "cache_saved_batch_blend",
    "discard_cached_action",
    "launch_all_animations_worker",
    "run_all_animations_worker",
]