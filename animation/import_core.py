import os
import struct
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import bpy
from mathutils import Matrix

from ..model.skeleton_space import BONE_AXIS_ADAPTER, BONE_AXIS_ADAPTER_INV, armature_uses_bone_axis_adapter
from .import_utils import (
    build_import_bone_mapping,
    clear_action_curves_for_bones,
    compute_import_local_matrix,
    ensure_import_action,
    get_current_world_matrices_by_anim_idx,
)
from ..utils import dx_to_blender_matrix


ANIM_SIGNATURE = b"STA"
ANIM_VERSION = 4


@dataclass
class AnimationData:
    """Holds parsed animation data from .anim file."""

    name: str = ""
    duration_seconds: float = 0.0
    bones: List[str] = field(default_factory=list)
    parent_indices: List[int] = field(default_factory=list)
    pose: List[Matrix] = field(default_factory=list)
    tracks: List[int] = field(default_factory=list)
    frames: List[List[Matrix]] = field(default_factory=list)


@dataclass
class AnimationImportResult:
    """Result details for a single animation import."""

    success: bool
    failure_reason: str = ""
    missing_bones: List[str] = field(default_factory=list)
    referenced_bones: List[str] = field(default_factory=list)
    tracked_bones: List[str] = field(default_factory=list)
    mapped_bone_count: int = 0
    total_bone_count: int = 0
    frame_count: int = 0


class AnimationReader:
    """Reads DoW2 .anim files."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file = None

    def read_byte(self) -> int:
        return struct.unpack('<B', self.file.read(1))[0]

    def read_long(self) -> int:
        return struct.unpack('<I', self.file.read(4))[0]

    def read_float(self) -> float:
        return struct.unpack('<f', self.file.read(4))[0]

    def read_str(self, length: int) -> str:
        return self.file.read(length).decode('utf-8', errors='replace')

    def read_matrix(self) -> Matrix:
        """Read 4x3 matrix (12 floats) from file."""
        row1 = (self.read_float(), self.read_float(), self.read_float())
        row2 = (self.read_float(), self.read_float(), self.read_float())
        row3 = (self.read_float(), self.read_float(), self.read_float())
        row4 = (self.read_float(), self.read_float(), self.read_float())

        return Matrix((
            (row1[0], row2[0], row3[0], row4[0]),
            (row1[1], row2[1], row3[1], row4[1]),
            (row1[2], row2[2], row3[2], row4[2]),
            (0.0, 0.0, 0.0, 1.0),
        ))

    def load(self) -> Optional[AnimationData]:
        """Load animation from file."""
        try:
            self.file = open(self.filepath, 'rb')

            signature = self.file.read(3)
            if signature != ANIM_SIGNATURE:
                print(f"Wrong file signature: {signature}")
                return None

            version = self.read_byte()
            if version != ANIM_VERSION:
                print(f"Wrong file version: {version} (expected {ANIM_VERSION})")
                return None

            anim = AnimationData()

            name_len = self.read_long()
            anim.name = self.read_str(name_len)

            num_bones = self.read_long()
            for _ in range(num_bones):
                bone_name_len = self.read_long()
                bone_name = self.read_str(bone_name_len)
                anim.bones.append(bone_name)

                pose_matrix = self.read_matrix()
                anim.pose.append(pose_matrix)

            num_tracks = self.read_long()
            for _ in range(num_tracks):
                anim.tracks.append(self.read_long())

            num_frames = self.read_long()
            for _ in range(num_frames):
                frame_data = []
                for _ in range(num_bones):
                    matrix = self.read_matrix()
                    matrix = dx_to_blender_matrix(matrix)
                    frame_data.append(matrix)
                anim.frames.append(frame_data)

            if num_frames > 1:
                anim.duration_seconds = (num_frames - 1) / 30.0

            self.file.close()
            return anim

        except Exception as exc:
            print(f"Error loading animation: {exc}")
            if self.file:
                self.file.close()
            return None


class DoW2AnimationImporter:
    """Imports DoW2 animations into Blender."""

    def __init__(self, context):
        self.context = context

    def find_armature(self) -> Optional[bpy.types.Object]:
        """Find the armature in the scene (from imported .model)."""
        if self.context.active_object and self.context.active_object.type == 'ARMATURE':
            return self.context.active_object

        for obj in self.context.scene.objects:
            if obj.type == 'ARMATURE':
                return obj

        return None

    def log_missing_bones(self, anim_name: str, armature_name: str, missing_bones: List[str]):
        """Log bones referenced by the animation that do not exist on the armature."""
        if not missing_bones:
            return

        print(
            f"Animation '{anim_name}' references {len(missing_bones)} bone(s) that are not in armature '{armature_name}'. Skipping them:"
        )
        for bone_name in missing_bones:
            print(f"  - {bone_name}")

    def import_animation(
        self,
        anim: AnimationData,
        armature: bpy.types.Object,
        selected_bone_names: Optional[set[str]] = None,
    ) -> AnimationImportResult:
        """Import animation data onto armature."""
        if not anim.frames:
            print("No frames in animation")
            return AnimationImportResult(success=False, failure_reason="Animation contains no frames")

        scene = self.context.scene
        num_frames = len(anim.frames)
        num_bones = len(anim.bones)
        target_fps = 30.0
        keyframe_times = [float(frame_index) for frame_index in range(num_frames)]

        if num_frames > 1 and anim.duration_seconds > 0.0:
            seconds_per_sample = anim.duration_seconds / float(num_frames - 1)
            keyframe_times = [frame_index * seconds_per_sample * target_fps for frame_index in range(num_frames)]

        scene.render.fps = int(target_fps)
        scene.frame_start = 0
        scene.frame_end = max(0, int(math.ceil(keyframe_times[-1])))
        scene.frame_current = 0

        action_name = anim.name if anim.name else "DoW2_Animation"
        mapping = build_import_bone_mapping(
            anim.bones,
            armature,
            parent_indices=anim.parent_indices,
            selected_bone_names=selected_bone_names,
        )
        bone_mapping = mapping.bone_mapping
        missing_bones = mapping.missing_bones
        tracked_indices = set(anim.tracks) if anim.tracks else set(range(num_bones))
        tracked_bones = [anim.bones[index] for index in anim.tracks if 0 <= index < len(anim.bones)]
        mapped_tracked_indices = tracked_indices.intersection(bone_mapping.keys())

        self.log_missing_bones(anim.name or action_name, armature.name, missing_bones)

        if not bone_mapping:
            if selected_bone_names:
                failure_reason = "None of the selected bones are referenced by this animation"
            else:
                failure_reason = "Animation bones do not match the armature"
            print(f"Failed to import animation '{anim.name or action_name}': {failure_reason}")
            return AnimationImportResult(
                success=False,
                failure_reason=failure_reason,
                missing_bones=missing_bones,
                referenced_bones=list(anim.bones),
                tracked_bones=tracked_bones,
                mapped_bone_count=0,
                total_bone_count=num_bones,
                frame_count=num_frames,
            )

        if not mapped_tracked_indices:
            if selected_bone_names:
                failure_reason = "None of the selected bones are tracked by this animation"
            else:
                failure_reason = "Animation tracked bones do not match the armature"
            print(f"Failed to import animation '{anim.name or action_name}': {failure_reason}")
            return AnimationImportResult(
                success=False,
                failure_reason=failure_reason,
                missing_bones=missing_bones,
                referenced_bones=list(anim.bones),
                tracked_bones=tracked_bones,
                mapped_bone_count=0,
                total_bone_count=num_bones,
                frame_count=num_frames,
            )

        action = ensure_import_action(armature, action_name, selected_bone_names=selected_bone_names)
        if selected_bone_names:
            clear_action_curves_for_bones(action, selected_bone_names)

        original_mode = armature.mode if armature == self.context.active_object else 'OBJECT'
        bpy.context.view_layer.objects.active = armature
        if armature.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        for frame_idx, frame_data in enumerate(anim.frames):
            keyframe_time = keyframe_times[frame_idx]
            frame_whole = int(math.floor(keyframe_time))
            frame_sub = float(keyframe_time - frame_whole)
            scene.frame_set(frame_whole, subframe=frame_sub)

            runtime_world_cache: Dict[int, Matrix] = {}
            current_world_by_anim_idx = None
            if selected_bone_names:
                current_world_by_anim_idx = get_current_world_matrices_by_anim_idx(armature, mapping)

            for bone_idx, world_matrix in enumerate(frame_data):
                if bone_idx not in bone_mapping:
                    continue
                if bone_idx not in tracked_indices:
                    continue

                pose_bone = bone_mapping[bone_idx]

                local_matrix = compute_import_local_matrix(
                    bone_idx,
                    frame_data,
                    mapping,
                    runtime_world_cache,
                    current_world_by_anim_idx=current_world_by_anim_idx,
                )
                if local_matrix is None:
                    continue

                rest_local = mapping.rest_local_by_anim_idx[bone_idx]

                pose_transform = rest_local.inverted() @ local_matrix
                if armature_uses_bone_axis_adapter(armature):
                    pose_transform = BONE_AXIS_ADAPTER_INV @ pose_transform @ BONE_AXIS_ADAPTER

                loc = pose_transform.to_translation()
                rot = pose_transform.to_quaternion()
                scale = pose_transform.to_scale()

                pose_bone.rotation_mode = 'QUATERNION'
                pose_bone.location = loc
                pose_bone.rotation_quaternion = rot
                pose_bone.scale = scale

                pose_bone.keyframe_insert(data_path="location", frame=keyframe_time)
                pose_bone.keyframe_insert(data_path="rotation_quaternion", frame=keyframe_time)
                pose_bone.keyframe_insert(data_path="scale", frame=keyframe_time)

        if original_mode != 'POSE':
            bpy.ops.object.mode_set(mode=original_mode)

        print(
            f"Imported animation '{anim.name}': {num_frames} frames, {len(mapped_tracked_indices)}/{len(tracked_indices)} tracked bones mapped, {len(missing_bones)} bone(s) skipped"
        )
        return AnimationImportResult(
            success=True,
            missing_bones=missing_bones,
            referenced_bones=list(anim.bones),
            tracked_bones=tracked_bones,
            mapped_bone_count=len(mapped_tracked_indices),
            total_bone_count=num_bones,
            frame_count=num_frames,
        )

    def clear_animation(self, armature: bpy.types.Object):
        """Clear all animation data from armature."""
        if armature.animation_data:
            armature.animation_data.action = None

        for pose_bone in armature.pose.bones:
            pose_bone.location = (0, 0, 0)
            pose_bone.rotation_quaternion = (1, 0, 0, 0)
            pose_bone.rotation_euler = (0, 0, 0)
            pose_bone.scale = (1, 1, 1)

# a
__all__ = [
    "ANIM_SIGNATURE",
    "ANIM_VERSION",
    "AnimationData",
    "AnimationImportResult",
    "AnimationReader",
    "DoW2AnimationImporter",
] 