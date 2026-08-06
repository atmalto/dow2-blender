import datetime
import json
import os
import subprocess
import tempfile

import bpy
from mathutils import Matrix

from ..model.skeleton_space import get_export_local_matrix, get_export_node_world_matrix
from .rig_track_utils import (
    get_armature_bones_in_export_order,
    parse_bone_name_file,
    parse_rig_track_csv,
    resolve_bone_names_for_armature,
)
from ..utils import blender_to_dx_matrix


def get_addon_path():
    """Get the path to the addon directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_log_path():
    """Get path to logs folder."""
    return os.path.join(get_addon_path(), "logs")


def ensure_log_dir():
    """Ensure logs directory exists."""
    log_path = get_log_path()
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    return log_path


def log_message(message, level="INFO"):
    """Log a message to the log file."""
    log_dir = ensure_log_dir()
    log_file = os.path.join(log_dir, "dow2_tools.log")

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}\n"

    with open(log_file, 'a', encoding='utf-8') as handle:
        handle.write(log_line)

    print(f"[{level}] {message}")


def log_info(message):
    log_message(message, "INFO")


def log_warning(message):
    log_message(message, "WARNING")


def log_error(message):
    log_message(message, "ERROR")


def get_anim_blender2hkx_path():
    """Get path to the centralized Havok CLI."""
    addon_path = get_addon_path()
    return os.path.join(addon_path, "blender_hkx", "havok_io_cli.exe")


def to_title_case(name):
    """Convert bone name to Title Case for DoW2 compatibility."""
    parts = name.split(' ')
    titled_parts = []
    for part in parts:
        if part:
            titled_parts.append(part[0].upper() + part[1:] if len(part) > 1 else part.upper())
    return ' '.join(titled_parts)


def gather_skeleton_data(armature_obj, export_bones=None, title_case_names=True):
    """Gather skeleton bone data from armature."""
    bones = []
    bone_name_to_index = {}

    if export_bones is None:
        source_bones = get_armature_bones_in_export_order(armature_obj)
    else:
        source_bones = []
        seen = set()
        for bone_name in export_bones:
            if bone_name in seen:
                continue
            seen.add(bone_name)
            bone = armature_obj.data.bones.get(bone_name)
            if bone is not None:
                source_bones.append(bone)

    for bone in source_bones:
        if export_bones is None or bone.name in export_bones:
            bone_name_to_index[bone.name] = len(bones)
            bones.append(bone)

    bone_names = []
    original_names = []
    parent_indices = []
    reference_pose = []

    for bone in bones:
        original_names.append(bone.name)

        name = to_title_case(bone.name) if title_case_names else bone.name
        bone_names.append(name)

        if bone.parent and bone.parent.name in bone_name_to_index:
            parent_idx = bone_name_to_index[bone.parent.name]
        else:
            parent_idx = -1
        parent_indices.append(parent_idx)

        if bone.parent and bone.parent.name in bone_name_to_index:
            local_matrix = get_export_local_matrix(bone, bone.parent, armature_obj)
        else:
            local_matrix = get_export_local_matrix(bone, None, armature_obj)

        local_matrix = blender_to_dx_matrix(local_matrix)

        pos = local_matrix.to_translation()
        rot = local_matrix.to_quaternion()
        scale = local_matrix.to_scale()

        reference_pose.append({
            "pos": [pos.x, pos.y, pos.z],
            "rot": [rot.x, rot.y, rot.z, rot.w],
            "scale": [scale.x, scale.y, scale.z],
        })

    return bone_names, parent_indices, reference_pose, original_names


def _ensure_quaternion_continuity(transforms):
    if not transforms or not transforms[0]:
        return 0

    flip_count = 0
    track_count = len(transforms[0])
    for track_index in range(track_count):
        previous_rot = transforms[0][track_index]["rot"]
        for frame_index in range(1, len(transforms)):
            current_rot = transforms[frame_index][track_index]["rot"]
            dot = sum(left * right for left, right in zip(previous_rot, current_rot))
            if dot < 0.0:
                transforms[frame_index][track_index]["rot"] = [-component for component in current_rot]
                current_rot = transforms[frame_index][track_index]["rot"]
                flip_count += 1
            previous_rot = current_rot

    return flip_count


def gather_animation_data(armature_obj, action, original_bone_names, export_tracks=None):
    """Gather animation keyframe data from an action."""
    scene = bpy.context.scene
    fps = scene.render.fps

    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1])
    num_frames = frame_end - frame_start + 1
    duration = (num_frames - 1) / fps

    bone_name_to_index = {name: i for i, name in enumerate(original_bone_names)}
    tracked_bone_names = original_bone_names if export_tracks is None else [
        bone_name for bone_name in original_bone_names if bone_name in export_tracks
    ]
    tracked_bone_set = set(tracked_bone_names)

    skeleton_parent_names = {}
    reference_local_dx = {}
    for bone_name in original_bone_names:
        bone = armature_obj.data.bones.get(bone_name)
        parent_name = None
        if bone and bone.parent and bone.parent.name in bone_name_to_index:
            parent_name = bone.parent.name
        skeleton_parent_names[bone_name] = parent_name

        if bone and parent_name:
            local_matrix = get_export_local_matrix(bone, bone.parent, armature_obj)
        elif bone:
            local_matrix = get_export_local_matrix(bone, None, armature_obj)
        else:
            local_matrix = Matrix.Identity(4)
        reference_local_dx[bone_name] = blender_to_dx_matrix(local_matrix)

    transforms = []
    original_frame = scene.frame_current

    if armature_obj.animation_data is None:
        armature_obj.animation_data_create()
    old_action = armature_obj.animation_data.action
    armature_obj.animation_data.action = action

    try:
        for frame in range(frame_start, frame_end + 1):
            scene.frame_set(frame)

            world_matrices_dx = {}
            for bone_name in original_bone_names:
                pose_bone = armature_obj.pose.bones.get(bone_name)
                if pose_bone:
                    world_matrix = get_export_node_world_matrix(pose_bone, armature_obj)
                    world_matrices_dx[bone_name] = blender_to_dx_matrix(world_matrix)
                else:
                    world_matrices_dx[bone_name] = None

            frame_transforms = []
            runtime_world_cache = {}

            def get_runtime_world(bone_name):
                if bone_name in runtime_world_cache:
                    return runtime_world_cache[bone_name]

                parent_name = skeleton_parent_names[bone_name]
                parent_world = Matrix.Identity(4)
                if parent_name:
                    parent_world = get_runtime_world(parent_name)

                sampled_world = world_matrices_dx.get(bone_name)
                if bone_name in tracked_bone_set and sampled_world is not None:
                    world_matrix = sampled_world
                else:
                    world_matrix = parent_world @ reference_local_dx[bone_name]

                runtime_world_cache[bone_name] = world_matrix
                return world_matrix

            for bone_name in tracked_bone_names:
                parent_name = skeleton_parent_names[bone_name]
                parent_world = Matrix.Identity(4)
                if parent_name:
                    parent_world = get_runtime_world(parent_name)

                sampled_world = world_matrices_dx.get(bone_name)
                if sampled_world is not None:
                    local_matrix = parent_world.inverted() @ sampled_world
                else:
                    local_matrix = reference_local_dx[bone_name]

                pos = local_matrix.to_translation()
                rot = local_matrix.to_quaternion()
                scale = local_matrix.to_scale()

                frame_transforms.append({
                    "pos": [pos.x, pos.y, pos.z],
                    "rot": [rot.x, rot.y, rot.z, rot.w],
                    "scale": [scale.x, scale.y, scale.z],
                })

            transforms.append(frame_transforms)

        continuity_flip_count = _ensure_quaternion_continuity(transforms)
        if continuity_flip_count:
            log_info(f"Applied quaternion continuity pass to {continuity_flip_count} rotation keys")

    finally:
        scene.frame_set(original_frame)
        armature_obj.animation_data.action = old_action

    return duration, num_frames, transforms, [bone_name_to_index[bone_name] for bone_name in tracked_bone_names]


def find_selected_armature(context):
    """Find the armature to use for animation export."""
    for obj in context.selected_objects:
        if obj.type == 'ARMATURE':
            return obj

    if context.active_object and context.active_object.type == 'ARMATURE':
        return context.active_object

    return None


def load_export_sets_from_csv(armature_obj, csv_path):
    """Load rig and track selections from a per-animation CSV file."""
    rig_names, track_names = parse_rig_track_csv(csv_path)
    if rig_names is None or track_names is None:
        return None, None, [f"Missing CSV config: {csv_path}"]

    export_bones, missing_rig = resolve_bone_names_for_armature(armature_obj, rig_names)
    export_tracks, missing_tracks = resolve_bone_names_for_armature(armature_obj, track_names)
    return export_bones, export_tracks, missing_rig + missing_tracks


def load_export_set_from_bone_file(armature_obj, file_path):
    """Load a single rig/track selection set from a global text file."""
    names = parse_bone_name_file(file_path)
    if not names:
        return None, [f"Missing or empty bone list: {file_path}"]

    resolved, missing = resolve_bone_names_for_armature(armature_obj, names)
    return resolved, missing


def export_animation(
    armature_obj,
    action,
    output_path,
    export_bones=None,
    export_tracks=None,
    quantization_bits=8,
    tolerance=0.0,
    use_block_compression=True,
    block_size=8,
    use_three_component_quaternions=True,
):
    """Export an animation action to HKX format."""
    anim_blender2hkx = get_anim_blender2hkx_path()

    if not os.path.exists(anim_blender2hkx):
        log_error(f"havok_io_cli.exe not found at {anim_blender2hkx}")
        return False

    if export_bones is not None and len(export_bones) == 0:
        log_error("No rig bones selected for export")
        return False

    if export_bones is not None and export_tracks is not None:
        ignored_tracks = sorted(bone_name for bone_name in export_tracks if bone_name not in export_bones)
        if ignored_tracks:
            preview = ", ".join(ignored_tracks[:10])
            if len(ignored_tracks) > 10:
                preview += ", ..."
            log_warning(f"Ignoring track selections not present in rig: {preview}")
        export_tracks = {bone_name for bone_name in export_tracks if bone_name in export_bones}

    log_info(f"Gathering skeleton data from {armature_obj.name}...")
    bone_names, parent_indices, reference_pose, original_names = gather_skeleton_data(armature_obj, export_bones)

    log_info(f"Gathering animation data from action {action.name} ({len(bone_names)} rig bones)...")
    duration, num_frames, transforms, track_bone_indices = gather_animation_data(armature_obj, action, original_names, export_tracks)
    log_info(f"Writing {len(track_bone_indices)} animation tracks")

    anim_data = {
        "skeleton_name": armature_obj.name,
        "duration": duration,
        "bones": bone_names,
        "parent_indices": parent_indices,
        "reference_pose": reference_pose,
        "track_bone_indices": track_bone_indices,
        "num_frames": num_frames,
        "transforms": transforms,
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as handle:
        json.dump(anim_data, handle, indent=2)
        json_path = handle.name

    try:
        effective_block_size = block_size if use_block_compression else 0
        log_info(
            f"Running havok_io_cli.exe animation write ({quantization_bits}-bit, tolerance={tolerance}, "
            f"block_compression={use_block_compression}, block_size={effective_block_size or 'full'}, "
            f"three_component_quats={use_three_component_quaternions})..."
        )
        log_info(f"  Input: {json_path}")
        log_info(f"  Output: {output_path}")

        result = subprocess.run(
            [
                anim_blender2hkx,
                "animation",
                "write",
                json_path,
                output_path,
                str(quantization_bits),
                str(tolerance),
                "1" if use_block_compression else "0",
                str(effective_block_size),
                "1" if use_three_component_quaternions else "0",
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    log_info(f"  [hkx] {line}")

        if result.returncode != 0 and result.returncode != 139:
            if result.stderr:
                log_error(f"havok_io_cli animation write errors: {result.stderr}")

            if not os.path.exists(output_path):
                log_error(f"havok_io_cli animation write failed with code {result.returncode}")
                return False

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            log_info(f"Successfully exported: {output_path} ({file_size} bytes)")
            return True

        log_error("Output file was not created")
        return False

    finally:
        try:
            os.unlink(json_path)
        except OSError:
            pass


def export_current_animation(
    output_path,
    export_bones=None,
    export_tracks=None,
    quantization_bits=8,
    tolerance=0.0,
    use_block_compression=True,
    block_size=8,
    use_three_component_quaternions=True,
):
    """Export the current armature's active action to HKX."""
    armature_obj = None

    for obj in bpy.context.selected_objects:
        if obj.type == 'ARMATURE':
            armature_obj = obj
            break

    if not armature_obj and bpy.context.active_object and bpy.context.active_object.type == 'ARMATURE':
        armature_obj = bpy.context.active_object

    if not armature_obj:
        log_error("No armature selected")
        return False

    if not armature_obj.animation_data or not armature_obj.animation_data.action:
        log_error("Armature has no active action")
        return False

    action = armature_obj.animation_data.action
    return export_animation(
        armature_obj,
        action,
        output_path,
        export_bones,
        export_tracks,
        quantization_bits=quantization_bits,
        tolerance=tolerance,
        use_block_compression=use_block_compression,
        block_size=block_size,
        use_three_component_quaternions=use_three_component_quaternions,
    )


__all__ = [
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
    "to_title_case",
]