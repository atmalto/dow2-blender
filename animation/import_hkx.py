import json
import os
import subprocess
import tempfile

from mathutils import Matrix, Quaternion, Vector

from ..model.skeleton_space import remove_bone_axis_adapter
from ..utils import dx_to_blender_matrix
from .export_core import get_anim_blender2hkx_path
from .import_core import AnimationData


class HkxAnimationImportError(RuntimeError):
    """Raised when the native HKX animation import path fails."""


class HkxNonAnimationAssetError(HkxAnimationImportError):
    """Raised when an HKX file is valid but does not contain animation data."""


def _transform_dict_to_dx_matrix(transform_dict: dict) -> Matrix:
    position = Vector(transform_dict.get("pos", [0.0, 0.0, 0.0]))
    rotation_values = transform_dict.get("rot", [0.0, 0.0, 0.0, 1.0])
    rotation = Quaternion((rotation_values[3], rotation_values[0], rotation_values[1], rotation_values[2]))
    scale = Vector(transform_dict.get("scale", [1.0, 1.0, 1.0]))
    return Matrix.LocRotScale(position, rotation, scale)


def _transform_dict_to_blender_local_matrix(transform_dict: dict) -> Matrix:
    return dx_to_blender_matrix(_transform_dict_to_dx_matrix(transform_dict))


def _build_world_matrices(local_matrices: list[Matrix], parent_indices: list[int]) -> list[Matrix]:
    world_matrices = [None] * len(local_matrices)

    def resolve(index: int) -> Matrix:
        cached = world_matrices[index]
        if cached is not None:
            return cached

        parent_index = parent_indices[index] if index < len(parent_indices) else -1
        local_matrix = local_matrices[index]
        if parent_index >= 0:
            world_matrix = resolve(parent_index) @ local_matrix
        else:
            world_matrix = local_matrix.copy()

        world_matrices[index] = world_matrix
        return world_matrix

    for index in range(len(local_matrices)):
        resolve(index)

    return world_matrices


def _extract_armature_reference_data(armature) -> tuple[list[str], list[int], list[Matrix], list[Matrix]]:
    bones = list(armature.data.bones)
    bone_names = [bone.name for bone in bones]
    bone_indices = {bone.name: index for index, bone in enumerate(bones)}
    parent_indices = [bone_indices.get(bone.parent.name, -1) if bone.parent else -1 for bone in bones]

    reference_world_matrices = [remove_bone_axis_adapter(bone.matrix_local, armature) for bone in bones]
    reference_local_matrices = []
    for bone, world_matrix in zip(bones, reference_world_matrices):
        if bone.parent:
            parent_world = remove_bone_axis_adapter(bone.parent.matrix_local, armature)
            local_matrix = parent_world.inverted() @ world_matrix
        else:
            local_matrix = world_matrix.copy()
        reference_local_matrices.append(local_matrix)

    return bone_names, parent_indices, reference_local_matrices, reference_world_matrices


def _parse_hkx_animation_json(filepath: str, payload: dict, armature=None) -> AnimationData:
    bone_names = list(payload.get("bones", []))
    if bone_names:
        parent_indices = list(payload.get("parent_indices", []))
        if len(parent_indices) < len(bone_names):
            parent_indices.extend([-1] * (len(bone_names) - len(parent_indices)))

        reference_pose_payload = list(payload.get("reference_pose", []))
        if len(reference_pose_payload) < len(bone_names):
            identity_transform = {"pos": [0.0, 0.0, 0.0], "rot": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]}
            reference_pose_payload.extend(identity_transform.copy() for _ in range(len(bone_names) - len(reference_pose_payload)))

        reference_local_matrices = [
            _transform_dict_to_blender_local_matrix(transform_dict)
            for transform_dict in reference_pose_payload[: len(bone_names)]
        ]
        reference_world_matrices = _build_world_matrices([matrix.copy() for matrix in reference_local_matrices], parent_indices)
    else:
        if armature is None:
            raise HkxAnimationImportError("HKX animation does not contain skeleton data and requires a loaded model armature")
        bone_names, parent_indices, reference_local_matrices, reference_world_matrices = _extract_armature_reference_data(armature)

    track_bone_indices = list(payload.get("track_bone_indices", []))
    if not track_bone_indices:
        track_bone_indices = list(range(len(bone_names)))

    for index in track_bone_indices:
        if index < 0 or index >= len(bone_names):
            raise HkxAnimationImportError(f"Native HKX reader returned invalid track index {index}")

    frame_payloads = list(payload.get("transforms", []))
    expected_frame_count = int(payload.get("num_frames", len(frame_payloads)))
    if expected_frame_count != len(frame_payloads):
        raise HkxAnimationImportError(
            f"Native HKX reader returned {len(frame_payloads)} frame payloads but declared {expected_frame_count}"
        )

    animation = AnimationData()
    animation.name = payload.get("animation_name") or os.path.splitext(os.path.basename(filepath))[0]
    animation.duration_seconds = float(payload.get("duration", 0.0) or 0.0)
    animation.bones = bone_names
    animation.pose = reference_world_matrices
    animation.tracks = track_bone_indices

    for frame_index, frame_payload in enumerate(frame_payloads):
        if len(frame_payload) != len(track_bone_indices):
            raise HkxAnimationImportError(
                f"Frame {frame_index} returned {len(frame_payload)} tracks, expected {len(track_bone_indices)}"
            )

        local_matrices = [matrix.copy() for matrix in reference_local_matrices]
        for track_index, transform_dict in enumerate(frame_payload):
            bone_index = track_bone_indices[track_index]
            local_matrices[bone_index] = _transform_dict_to_blender_local_matrix(transform_dict)

        animation.frames.append(_build_world_matrices(local_matrices, parent_indices))

    return animation


def load_hkx_animation(filepath: str, armature=None) -> AnimationData:
    """Load a DoW2 animation HKX via the native Havok reader executable."""
    anim_blender2hkx = get_anim_blender2hkx_path()
    if not os.path.exists(anim_blender2hkx):
        raise HkxAnimationImportError(f"Havok CLI not found: {anim_blender2hkx}")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as handle:
        json_path = handle.name

    try:
        result = subprocess.run(
            [anim_blender2hkx, "animation", "read", filepath, json_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            details = (result.stderr or result.stdout or "Unknown error").strip()
            lowered_details = details.lower()
            if "no animation tracks found" in lowered_details or "animation container not found" in lowered_details:
                raise HkxNonAnimationAssetError(f"HKX file is not an animation clip: {filepath}")
            raise HkxAnimationImportError(f"Native HKX animation read failed: {details}")

        with open(json_path, 'r', encoding='utf-8') as handle:
            payload = json.load(handle)
        return _parse_hkx_animation_json(filepath, payload, armature=armature)
    finally:
        if os.path.exists(json_path):
            os.remove(json_path)


__all__ = [
    "HkxAnimationImportError",
    "HkxNonAnimationAssetError",
    "load_hkx_animation",
]