import json
from pathlib import Path

from .bodies import create_rigid_bodies_from_skeleton
from .constraints import create_constraints
from .hkx import export_ragdoll_data_to_hkx
from .skeleton import create_ragdoll_skeleton_from_armature

try:
    from .authoring import build_authored_ragdoll_data, find_ragdoll_skeleton_for_source
except Exception:
    build_authored_ragdoll_data = None
    find_ragdoll_skeleton_for_source = None


def build_ragdoll_data(armature, ragdoll_bone_order=None, auto_generate_missing_bodies=True):
    if build_authored_ragdoll_data is not None and find_ragdoll_skeleton_for_source is not None:
        authored_skeleton = find_ragdoll_skeleton_for_source(armature)
        if authored_skeleton is not None:
            return build_authored_ragdoll_data(
                armature,
                authored_skeleton,
                auto_generate_missing_bodies=auto_generate_missing_bodies,
            )

    animation_skeleton, ragdoll_skeleton, bone_mappings, ragdoll_bone_map = create_ragdoll_skeleton_from_armature(
        armature, ragdoll_bone_order=ragdoll_bone_order
    )

    rigid_bodies = create_rigid_bodies_from_skeleton(
        ragdoll_skeleton, armature, ragdoll_bone_map
    )
    constraints = create_constraints(ragdoll_skeleton)

    ragdoll_data = {
        "animation_skeleton": animation_skeleton,
        "ragdoll_skeleton": ragdoll_skeleton,
        "bone_mappings": bone_mappings,
        "rigid_bodies": rigid_bodies,
        "constraints": constraints,
    }

    return ragdoll_data


def export_ragdoll_json(armature, output_path, ragdoll_bone_order=None, auto_generate_missing_bodies=True):
    ragdoll_data = build_ragdoll_data(
        armature,
        ragdoll_bone_order=ragdoll_bone_order,
        auto_generate_missing_bodies=auto_generate_missing_bodies,
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(ragdoll_data, indent=2), encoding="utf-8")
    return ragdoll_data


def export_ragdoll_hkx(
    armature,
    output_path,
    ragdoll_bone_order=None,
    json_path=None,
    auto_generate_missing_bodies=True,
):
    ragdoll_data = build_ragdoll_data(
        armature,
        ragdoll_bone_order=ragdoll_bone_order,
        auto_generate_missing_bodies=auto_generate_missing_bodies,
    )
    success, output, _ = export_ragdoll_data_to_hkx(ragdoll_data, output_path, json_path=json_path)
    if not success:
        raise RuntimeError(output)
    return ragdoll_data